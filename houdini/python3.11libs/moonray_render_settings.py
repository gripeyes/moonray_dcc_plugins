"""MoonRay Solaris Render Settings authoring and HDA generation."""

from pathlib import Path

import hou

from pxr import Gf, Sdf, UsdRender


OPERATOR_TYPE = "Lop::DW_MOONRAY::moonrayrendersettings::1"
OPERATOR_LABEL = "MoonRay Render Settings"
RENDER_SETTINGS_PRIM = "/Render/rendersettings"
RENDER_PRODUCTS_PARENT_PRIM = "/Render/Products"
RENDER_VARS_PARENT_PRIM = "/Render/Products/Vars"
RENDER_PRODUCT_NAME = "renderproduct"
BEAUTY_RENDER_VAR_NAME = "beauty"
PRODUCT_NAME = "$HIP/render/$HIPNAME.$OS.$F4.exr"
DEFAULT_RESOLUTION = (1920, 1080)


SCENE_VARIABLES = (
    ("sampling_mode", Sdf.ValueTypeNames.Token),
    ("pixel_samples", Sdf.ValueTypeNames.Int),
    ("light_samples", Sdf.ValueTypeNames.Int),
    ("bsdf_samples", Sdf.ValueTypeNames.Int),
    ("bssrdf_samples", Sdf.ValueTypeNames.Int),
    ("target_adaptive_error", Sdf.ValueTypeNames.Float),
    ("min_adaptive_samples", Sdf.ValueTypeNames.Int),
    ("max_adaptive_samples", Sdf.ValueTypeNames.Int),
    ("sample_clamping_value", Sdf.ValueTypeNames.Float),
    ("sample_clamping_depth", Sdf.ValueTypeNames.Int),
    ("roughness_clamping_factor", Sdf.ValueTypeNames.Float),
    ("max_depth", Sdf.ValueTypeNames.Int),
    ("max_diffuse_depth", Sdf.ValueTypeNames.Int),
    ("max_glossy_depth", Sdf.ValueTypeNames.Int),
    ("max_mirror_depth", Sdf.ValueTypeNames.Int),
    ("max_presence_depth", Sdf.ValueTypeNames.Int),
    ("max_hair_depth", Sdf.ValueTypeNames.Int),
    ("max_volume_depth", Sdf.ValueTypeNames.Int),
)


def _parm(node, name, default=None):
    parm = node.parm(name)
    if parm is None:
        return default
    return parm.eval()


def _string_parm(node, name, default=""):
    parm = node.parm(name)
    if parm is None:
        return default
    try:
        return parm.unexpandedString()
    except hou.OperationFailed:
        return str(parm.eval())


def _path(node, name, default):
    value = _string_parm(node, name, default).strip()
    return value or default


def _child_path(parent, child):
    parent_path = Sdf.Path(parent)
    return str(parent_path.AppendChild(child))


def _set_rel_targets(schema_obj, create_rel, paths):
    valid = [Sdf.Path(path) for path in paths if path]
    rel = create_rel()
    rel.SetTargets(valid)
    return rel


def author_from_node(node=None):
    """Author USD RenderSettings, RenderProduct, beauty RenderVar, and MoonRay settings."""

    node = node or hou.pwd()
    stage = node.editableStage()

    settings_path = _path(node, "render_settings_prim", RENDER_SETTINGS_PRIM)
    products_parent_path = _path(node, "render_products_parent_prim", RENDER_PRODUCTS_PARENT_PRIM)
    vars_parent_path = _path(node, "render_vars_parent_prim", RENDER_VARS_PARENT_PRIM)
    product_name = _string_parm(node, "render_product_name", RENDER_PRODUCT_NAME).strip() or RENDER_PRODUCT_NAME
    beauty_var_name = _string_parm(node, "beauty_render_var_name", BEAUTY_RENDER_VAR_NAME).strip() or BEAUTY_RENDER_VAR_NAME
    product_path = _child_path(products_parent_path, product_name)
    beauty_var_path = _child_path(vars_parent_path, beauty_var_name)
    camera_path = _path(node, "camera", "/cameras/camera1")

    settings = UsdRender.Settings.Define(stage, settings_path)
    product = UsdRender.Product.Define(stage, product_path)
    beauty_var = UsdRender.Var.Define(stage, beauty_var_path)

    _set_rel_targets(settings, settings.CreateProductsRel, [product_path])
    if camera_path:
        _set_rel_targets(settings, settings.CreateCameraRel, [camera_path])

    width = int(_parm(node, "resolutionx", DEFAULT_RESOLUTION[0]))
    height = int(_parm(node, "resolutiony", DEFAULT_RESOLUTION[1]))
    settings.CreateResolutionAttr().Set(Gf.Vec2i(width, height))

    product_name = _string_parm(node, "product_name", PRODUCT_NAME).strip() or PRODUCT_NAME
    product.CreateProductNameAttr().Set(product_name)
    product.CreateProductTypeAttr().Set("raster")
    _set_rel_targets(product, product.CreateOrderedVarsRel, [beauty_var_path])

    beauty_var.CreateDataTypeAttr().Set("color3f")
    beauty_var.CreateSourceNameAttr().Set("color")
    beauty_var.GetPrim().CreateAttribute(
        "driver:parameters:aov:name",
        Sdf.ValueTypeNames.String,
        custom=True,
    ).Set("color")

    settings_prim = settings.GetPrim()
    for name, value_type in SCENE_VARIABLES:
        parm = node.parm("sceneVariable_" + name)
        if parm is None:
            continue
        if value_type == Sdf.ValueTypeNames.Token:
            value = parm.evalAsString()
        elif value_type == Sdf.ValueTypeNames.Int:
            value = int(parm.eval())
        elif value_type == Sdf.ValueTypeNames.Float:
            value = float(parm.eval())
        settings_prim.CreateAttribute(
            "moonray:sceneVariable:" + name,
            value_type,
            custom=True,
        ).Set(value)

    rdl_output = _string_parm(node, "rdlOutput", "").strip()
    if rdl_output:
        settings_prim.CreateAttribute(
            "rdlOutput",
            Sdf.ValueTypeNames.String,
            custom=True,
        ).Set(rdl_output)


def _prim_path_tags(select_existing=False, input_index=None):
    tags = {
        "script_action": "import loputils\nloputils.selectPrimsInParm(kwargs, %s)" % (
            "True" if select_existing else "False"
        ),
        "script_action_icon": "BUTTONS_reselect",
        "sidefx::usdpathtype": "prim",
    }
    if input_index is not None:
        tags["sidefx::usdpathinput"] = str(input_index)
    return tags


def _parm_tags(**tags):
    return {key: value for key, value in tags.items() if value is not None}


def _string_prim_path(name, label, default, help_text, select_existing=False, input_index=None):
    parm = hou.StringParmTemplate(
        name,
        label,
        1,
        (default,),
        string_type=hou.stringParmType.Regular,
        help=help_text,
    )
    parm.setTags(_prim_path_tags(select_existing=select_existing, input_index=input_index))
    return parm


def _label(name, label, text):
    return hou.LabelParmTemplate(name, label, (text,))


def _build_parm_template_group():
    ptg = hou.ParmTemplateGroup()

    render_settings_prim = (
        _label(
            "render_prim_note",
            "",
            "The primitives MUST be located under the /Render/ primitive to match the USD spec.",
        ),
        _string_prim_path(
            "render_settings_prim",
            "RenderSettings Primitive Path",
            RENDER_SETTINGS_PRIM,
            "USD RenderSettings prim authored by this node. Point USD Render ROP or a future MoonRay ROP at this prim.",
            input_index=0,
        ),
        _string_prim_path(
            "render_products_parent_prim",
            "RenderProducts Parent Primitive Path",
            RENDER_PRODUCTS_PARENT_PRIM,
            "Parent prim under which the beauty RenderProduct is authored.",
            select_existing=True,
            input_index=0,
        ),
        _string_prim_path(
            "render_vars_parent_prim",
            "RenderVars Parent Primitive Path",
            RENDER_VARS_PARENT_PRIM,
            "Parent prim under which the first-pass beauty RenderVar is authored.",
            select_existing=True,
            input_index=0,
        ),
    )
    ptg.append(
        hou.FolderParmTemplate(
            "render_settings_prim_folder",
            "Render Settings Prim",
            render_settings_prim,
            folder_type=hou.folderType.Collapsible,
        )
    )

    output_picture = hou.StringParmTemplate(
        "product_name",
        "Output Picture",
        1,
        (PRODUCT_NAME,),
        string_type=hou.stringParmType.FileReference,
        help="Final raster output path authored as RenderProduct.productName. This is separate from debug RDL/RDLA scene export.",
    )
    output_picture.setTags({"filechooser_mode": "write"})
    ptg.append(output_picture)
    ptg.append(
        _string_prim_path(
            "camera",
            "Camera",
            "/cameras/camera1",
            "Render camera prim targeted by the RenderSettings camera relationship.",
            input_index=0,
        )
    )
    res_mode = hou.StringParmTemplate(
        "res_mode",
        "Resolution Mode",
        1,
        ("autoheight",),
        string_type=hou.stringParmType.Regular,
        help="Use the USD camera aperture aspect ratio to compute one resolution dimension, or set both dimensions manually.",
    )
    res_mode.setItemGeneratorScript("menu = __import__('loputils').resolutionModeMenuItems()\nreturn menu")
    res_mode.setItemGeneratorScriptLanguage(hou.scriptLanguage.Python)
    res_mode.setMenuType(hou.menuType.Normal)
    res_mode.setTags(
        {
            "export_disable": "1",
            "script_callback": "__import__('loputils').updateResolutionParameters(hou.pwd(), True)",
            "script_callback_language": "python",
        }
    )
    ptg.append(res_mode)
    ptg.append(
        resolution := hou.IntParmTemplate(
            "resolution",
            "Resolution",
            2,
            DEFAULT_RESOLUTION,
            naming_scheme=hou.parmNamingScheme.XYZW,
            min=1,
            max=8192,
            min_is_strict=True,
            help="Offline husk/USD renders use this resolution through RenderSettings. Viewport/IPR resolution is driven by the viewport.",
        )
    )
    resolution_menu = hou.MenuParmTemplate(
        "resolutionMenu",
        "Choose Resolution",
        (),
        (),
        help="Choose a common image resolution.",
    )
    resolution_menu.setItemGeneratorScript(
        'echo `pythonexprs("__import__(\'toolutils\').parseDialogScriptMenu(\'FBres\')")`'
    )
    resolution_menu.setItemGeneratorScriptLanguage(hou.scriptLanguage.Hscript)
    resolution_menu.setMenuType(hou.menuType.Mini)
    resolution_menu.hideLabel(True)
    resolution_menu.setTags(
        {
            "script_callback": 'opparm . resolution ( `arg("$script_value", 0)` `arg("$script_value", 1)` pixelAspectRatio ( `arg("$script_value", 2)` )'
        }
    )
    ptg.append(resolution_menu)
    pixel_aspect = hou.FloatParmTemplate(
        "pixelAspectRatio",
        "Pixel Aspect Ratio",
        1,
        (1.0,),
        help="Companion value used by Houdini's native resolution preset menu. Pixel aspect authoring is deferred.",
    )
    pixel_aspect.hide(True)
    ptg.append(pixel_aspect)
    ptg.append(
        _label(
            "resolution_note",
            "Resolution Note",
            "Offline husk/USD renders use this RenderSettings resolution. Viewport/IPR resolution is driven by the viewport.",
        )
    )

    render_product = (
        hou.StringParmTemplate(
            "render_product_name",
            "RenderProduct Name",
            1,
            (RENDER_PRODUCT_NAME,),
            help="Advanced name for the default beauty RenderProduct authored under the RenderProducts parent prim.",
        ),
        hou.StringParmTemplate(
            "beauty_render_var_name",
            "Beauty RenderVar Name",
            1,
            (BEAUTY_RENDER_VAR_NAME,),
            help="Advanced name for the default beauty RenderVar authored under the RenderVars parent prim.",
        ),
        _label(
            "beauty_note",
            "Beauty Output",
            "Derived paths: RenderProduct under the RenderProducts parent and beauty RenderVar under the RenderVars parent. AOV and Cryptomatte controls are deferred.",
        ),
    )

    sampling = [
        hou.MenuParmTemplate(
            "sceneVariable_sampling_mode",
            "Sampling Mode",
            ("uniform", "adaptive"),
            ("Uniform", "Adaptive"),
            default_value=0,
            help="MoonRay SceneVariables sampling_mode. Metadata values are uniform = 0 and adaptive = 2; this node authors the token form used by the generic Solaris Render Settings Moonray tab.",
        ),
        hou.IntParmTemplate(
            "sceneVariable_pixel_samples",
            "Pixel Samples",
            1,
            (8,),
            min=0,
            max=4096,
            help="MoonRay pixel_samples SceneVariable.",
        ),
        hou.IntParmTemplate(
            "sceneVariable_light_samples",
            "Light Samples",
            1,
            (2,),
            min=0,
            max=4096,
            help="MoonRay light_samples SceneVariable.",
        ),
        hou.IntParmTemplate(
            "sceneVariable_bsdf_samples",
            "BSDF Samples",
            1,
            (2,),
            min=0,
            max=4096,
            help="MoonRay bsdf_samples SceneVariable.",
        ),
        hou.IntParmTemplate(
            "sceneVariable_bssrdf_samples",
            "BSSRDF Samples",
            1,
            (2,),
            min=0,
            max=4096,
            help="MoonRay bssrdf_samples SceneVariable.",
        ),
    ]
    adaptive_cond = "{ sceneVariable_sampling_mode != adaptive }"
    for name, label, default, help_text in (
        (
            "sceneVariable_min_adaptive_samples",
            "Min Adaptive Samples",
            16,
            "MoonRay min_adaptive_samples SceneVariable. Used by adaptive sampling.",
        ),
        (
            "sceneVariable_max_adaptive_samples",
            "Max Adaptive Samples",
            4096,
            "MoonRay max_adaptive_samples SceneVariable. Used by adaptive sampling.",
        ),
    ):
        parm = hou.IntParmTemplate(name, label, 1, (default,), min=0, max=8192, help=help_text)
        parm.setConditional(hou.parmCondType.DisableWhen, adaptive_cond)
        sampling.append(parm)
    target_error = hou.FloatParmTemplate(
        "sceneVariable_target_adaptive_error",
        "Target Adaptive Error",
        1,
        (10.0,),
        min=0,
        max=100,
        help="MoonRay target_adaptive_error SceneVariable. Used by adaptive sampling.",
    )
    target_error.setConditional(hou.parmCondType.DisableWhen, adaptive_cond)
    sampling.append(target_error)

    ray_depth = []
    for name, label, default in (
        ("sceneVariable_max_depth", "Max Ray Depth", 5),
        ("sceneVariable_max_diffuse_depth", "Max Diffuse Depth", 2),
        ("sceneVariable_max_glossy_depth", "Max Glossy Depth", 2),
        ("sceneVariable_max_mirror_depth", "Max Mirror Depth", 3),
        ("sceneVariable_max_presence_depth", "Max Presence Depth", 16),
        ("sceneVariable_max_hair_depth", "Max Hair Depth", 5),
        ("sceneVariable_max_volume_depth", "Max Volume Depth", 1),
    ):
        ray_depth.append(
            hou.IntParmTemplate(
                name,
                label,
                1,
                (default,),
                min=0,
                max=128,
                help="MoonRay %s SceneVariable." % name.replace("sceneVariable_", ""),
            )
        )

    clamping = (
        hou.FloatParmTemplate(
            "sceneVariable_sample_clamping_value",
            "Sample Clamping Value",
            1,
            (10.0,),
            min=0,
            max=100,
            help="Clamp sample values before they are accumulated.",
        ),
        hou.IntParmTemplate(
            "sceneVariable_sample_clamping_depth",
            "Sample Clamping Depth",
            1,
            (1,),
            min=0,
            max=32,
            help="Ray depth after which sample clamping is applied.",
        ),
        hou.FloatParmTemplate(
            "sceneVariable_roughness_clamping_factor",
            "Roughness Clamping Factor",
            1,
            (0.0,),
            min=0,
            max=10,
            help="Clamp material roughness along paths. A value of 1 clamps values to the maximum roughness encountered, while lower values temper the clamping value. 0 disables the effect. Using this technique reduces fireflies from indirect caustics but is biased.",
        ),
    )

    debug = (
        hou.StringParmTemplate(
            "rdlOutput",
            "Debug RDL/RDLA Output",
            1,
            ("",),
            string_type=hou.stringParmType.FileReference,
            help="Optional debug scene export path consumed by hdMoonRay rdlOutput. This writes RDL/RDLA scene data, not the final raster image.",
        ),
    )
    debug[0].setTags({"filechooser_mode": "write"})

    ptg.append(
        hou.FolderParmTemplate(
            "moonray_settings",
            "MoonRay Render Settings",
            (
                hou.FolderParmTemplate("render_product", "Render Product", render_product),
                hou.FolderParmTemplate("sampling", "Sampling", sampling),
                hou.FolderParmTemplate("ray_depth", "Ray Depth", ray_depth),
                hou.FolderParmTemplate("clamping", "Clamping", clamping),
                hou.FolderParmTemplate("debug", "Debug", debug),
            ),
            folder_type=hou.folderType.Tabs,
        )
    )

    return ptg


def regenerate_hda(hda_path):
    """Regenerate the MoonRay Render Settings HDA from this source module."""

    hda_path = Path(hda_path)
    hda_path.parent.mkdir(parents=True, exist_ok=True)
    if hda_path.exists():
        hda_path.unlink()

    stage = hou.node("/stage") or hou.node("/").createNode("lopnet", "stage")
    source = stage.createNode("pythonscript", "moonrayrendersettings_src")
    source.parm("python").set(
        "import hou\n"
        "import moonray_render_settings\n\n"
        "moonray_render_settings.author_from_node(hou.pwd())\n"
    )

    hda_node = source.createDigitalAsset(
        name=OPERATOR_TYPE,
        hda_file_name=str(hda_path),
        description=OPERATOR_LABEL,
        min_num_inputs=0,
        max_num_inputs=1,
        ignore_external_references=True,
    )
    definition = hda_node.type().definition()
    definition.setComment(
        "Authors an artist-friendly USD RenderSettings/RenderProduct setup and curated hdMoonRay moonray:sceneVariable settings."
    )
    definition.setParmTemplateGroup(_build_parm_template_group())
    try:
        definition.setIcon("ROP_usdrender")
    except hou.OperationFailed:
        pass
    definition.updateFromNode(hda_node)
    hda_node.destroy()
    return str(hda_path)

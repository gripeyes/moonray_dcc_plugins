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
ROP_NODE_TYPE = "usdrender_rop"
ROP_RENDERER_TOKEN = "HdMoonrayRendererPlugin"
ROP_OWNER_LOP_KEY = "moonray_render_settings_lop"
ROP_OWNER_OPERATOR_KEY = "moonray_render_settings_operator"
ROP_OWNER_SESSION_KEY = "moonray_render_settings_lop_session_id"


SCENE_VARIABLES = (
    ("sampling_mode", Sdf.ValueTypeNames.Token),
    ("light_sampling_mode", Sdf.ValueTypeNames.Token),
    ("light_sampling_quality", Sdf.ValueTypeNames.Float),
    ("pixel_samples", Sdf.ValueTypeNames.Int),
    ("light_samples", Sdf.ValueTypeNames.Int),
    ("bsdf_samples", Sdf.ValueTypeNames.Int),
    ("bssrdf_samples", Sdf.ValueTypeNames.Int),
    ("target_adaptive_error", Sdf.ValueTypeNames.Float),
    ("min_adaptive_samples", Sdf.ValueTypeNames.Int),
    ("max_adaptive_samples", Sdf.ValueTypeNames.Int),
    ("batch_tile_order", Sdf.ValueTypeNames.Token),
    ("progressive_tile_order", Sdf.ValueTypeNames.Token),
    ("checkpoint_tile_order", Sdf.ValueTypeNames.Token),
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
    ("max_subsurface_per_path", Sdf.ValueTypeNames.Int),
    ("russian_roulette_threshold", Sdf.ValueTypeNames.Float),
    ("transparency_threshold", Sdf.ValueTypeNames.Float),
    ("presence_threshold", Sdf.ValueTypeNames.Float),
    ("presence_quality", Sdf.ValueTypeNames.Float),
    ("lock_frame_noise", Sdf.ValueTypeNames.Bool),
    ("disable_optimized_hair_sampling", Sdf.ValueTypeNames.Bool),
    ("volume_quality", Sdf.ValueTypeNames.Float),
    ("volume_shadow_quality", Sdf.ValueTypeNames.Float),
    ("volume_illumination_samples", Sdf.ValueTypeNames.Int),
    ("volume_opacity_threshold", Sdf.ValueTypeNames.Float),
    ("volume_overlap_mode", Sdf.ValueTypeNames.Token),
    ("volume_attenuation_factor", Sdf.ValueTypeNames.Float),
    ("volume_contribution_factor", Sdf.ValueTypeNames.Float),
    ("volume_phase_attenuation_factor", Sdf.ValueTypeNames.Float),
    ("volume_indirect_samples", Sdf.ValueTypeNames.Int),
    ("texture_blur", Sdf.ValueTypeNames.Float),
    ("pixel_filter_width", Sdf.ValueTypeNames.Float),
    ("pixel_filter", Sdf.ValueTypeNames.Token),
    ("enable_dof", Sdf.ValueTypeNames.Bool),
    ("enable_displacement", Sdf.ValueTypeNames.Bool),
    ("enable_subsurface_scattering", Sdf.ValueTypeNames.Bool),
    ("enable_shadowing", Sdf.ValueTypeNames.Bool),
    ("enable_presence_shadows", Sdf.ValueTypeNames.Bool),
    ("lights_visible_in_camera", Sdf.ValueTypeNames.Bool),
    ("propagate_visibility_bounce_type", Sdf.ValueTypeNames.Bool),
    ("shadow_terminator_fix", Sdf.ValueTypeNames.Token),
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


def _bool_parm(node, name, default=False):
    parm = node.parm(name)
    if parm is None:
        return default
    return bool(parm.eval())


def author_from_node(node=None):
    """Author USD RenderSettings, RenderProduct, optional beauty RenderVar, and MoonRay settings."""

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

    _set_rel_targets(settings, settings.CreateProductsRel, [product_path])
    if camera_path:
        _set_rel_targets(settings, settings.CreateCameraRel, [camera_path])

    width = int(_parm(node, "resolutionx", DEFAULT_RESOLUTION[0]))
    height = int(_parm(node, "resolutiony", DEFAULT_RESOLUTION[1]))
    settings.CreateResolutionAttr().Set(Gf.Vec2i(width, height))

    product_name = _string_parm(node, "product_name", PRODUCT_NAME).strip() or PRODUCT_NAME
    product.CreateProductNameAttr().Set(product_name)
    product.CreateProductTypeAttr().Set("raster")

    ordered_vars = []
    if _bool_parm(node, "aov_beauty", False):
        beauty_var = UsdRender.Var.Define(stage, beauty_var_path)
        beauty_var.CreateDataTypeAttr().Set("color3f")
        beauty_var.CreateSourceNameAttr().Set("color")
        beauty_var.CreateSourceTypeAttr().Set("raw")
        beauty_var.GetPrim().CreateAttribute(
            "driver:parameters:aov:name",
            Sdf.ValueTypeNames.String,
            custom=True,
        ).Set("color")
        beauty_var.GetPrim().CreateAttribute(
            "driver:parameters:aov:format",
            Sdf.ValueTypeNames.Token,
            custom=True,
        ).Set("color3f")
        beauty_var.GetPrim().CreateAttribute(
            "driver:parameters:aov:multiSampled",
            Sdf.ValueTypeNames.Bool,
            custom=True,
        ).Set(False)
        beauty_var.GetPrim().CreateAttribute(
            "driver:parameters:aov:clearValue",
            Sdf.ValueTypeNames.Int,
            custom=True,
        ).Set(0)
        ordered_vars.append(beauty_var_path)
    _set_rel_targets(product, product.CreateOrderedVarsRel, ordered_vars)

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
        elif value_type == Sdf.ValueTypeNames.Bool:
            value = bool(parm.eval())
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


def _safe_node_name(name):
    return "".join(ch if ch.isalnum() or ch == "_" else "_" for ch in name)


def _owned_rop_for_lop(lop_node):
    parent = lop_node.parent()
    if parent is None:
        return None

    lop_path = lop_node.path()
    lop_session_id = str(lop_node.sessionId())
    fallback_by_path = None
    fallback_by_session = None
    for rop in parent.children():
        if rop.type().name() != ROP_NODE_TYPE:
            continue
        if rop.userData(ROP_OWNER_OPERATOR_KEY) != OPERATOR_TYPE:
            continue
        if rop.userData(ROP_OWNER_LOP_KEY) == lop_path:
            return rop
        if rop.userData(ROP_OWNER_SESSION_KEY) == lop_session_id:
            fallback_by_session = rop
        elif rop.parm("loppath") is not None and rop.parm("loppath").eval() == lop_path:
            fallback_by_path = rop
    return fallback_by_session or fallback_by_path


def _create_owned_rop(lop_node):
    parent = lop_node.parent()
    if parent is None:
        raise hou.OperationFailed("MoonRay Render Settings LOP has no parent network.")
    base_name = _safe_node_name(lop_node.name() + "_usdrender")
    existing = parent.node(base_name)
    if existing is not None:
        if (
            existing.type().name() == ROP_NODE_TYPE
            and existing.userData(ROP_OWNER_OPERATOR_KEY) == OPERATOR_TYPE
            and existing.userData(ROP_OWNER_LOP_KEY) == lop_node.path()
        ):
            return existing
        rop = parent.createNode(ROP_NODE_TYPE)
        rop.setName(base_name, unique_name=True)
        return rop
    return parent.createNode(ROP_NODE_TYPE, base_name)


def create_or_update_usd_render_rop(lop_node=None):
    """Create or update the USD Render ROP owned by this MoonRay Render Settings LOP."""

    lop_node = lop_node or hou.pwd()
    rop = _owned_rop_for_lop(lop_node) or _create_owned_rop(lop_node)

    settings_prim = _path(lop_node, "render_settings_prim", RENDER_SETTINGS_PRIM)
    for parm_name, value in (
        ("renderer", ROP_RENDERER_TOKEN),
        ("loppath", lop_node.path()),
        ("rendersettings", settings_prim),
        ("outputimage", ""),
    ):
        parm = rop.parm(parm_name)
        if parm is not None:
            parm.set(value)

    try:
        rop.setInput(0, lop_node)
    except hou.OperationFailed:
        pass
    try:
        rop.setPosition(lop_node.position() + hou.Vector2(0, -1.0))
    except hou.OperationFailed:
        pass

    rop.setUserData(ROP_OWNER_LOP_KEY, lop_node.path())
    rop.setUserData(ROP_OWNER_OPERATOR_KEY, OPERATOR_TYPE)
    rop.setUserData(ROP_OWNER_SESSION_KEY, str(lop_node.sessionId()))
    rop.setComment("Owned by %s (%s)." % (lop_node.path(), OPERATOR_TYPE))
    try:
        rop.setGenericFlag(hou.nodeFlag.DisplayComment, True)
    except hou.OperationFailed:
        pass
    return rop


def _deferred_update_usd_render_rop(session_id):
    node = hou.nodeBySessionId(session_id)
    if node is not None and node.type().name() == OPERATOR_TYPE:
        create_or_update_usd_render_rop(node)


def on_created(kwargs):
    node = kwargs.get("node")
    if node is not None:
        try:
            import hdefereval

            hdefereval.executeDeferred(_deferred_update_usd_render_rop, node.sessionId())
        except Exception:
            create_or_update_usd_render_rop(node)


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


def _scene_int(name, label, default, min_value=0, max_value=128, help_text=None):
    return hou.IntParmTemplate(
        "sceneVariable_" + name,
        label,
        1,
        (default,),
        min=min_value,
        max=max_value,
        help=help_text or ("MoonRay %s SceneVariable." % name),
    )


def _scene_float(name, label, default, min_value=0.0, max_value=10.0, help_text=None):
    return hou.FloatParmTemplate(
        "sceneVariable_" + name,
        label,
        1,
        (default,),
        min=min_value,
        max=max_value,
        help=help_text or ("MoonRay %s SceneVariable." % name),
    )


def _scene_toggle(name, label, default, help_text=None):
    return hou.ToggleParmTemplate(
        "sceneVariable_" + name,
        label,
        default_value=default,
        help=help_text or ("MoonRay %s SceneVariable." % name),
    )


def _scene_menu(name, label, tokens, labels, default_token, help_text=None):
    parm = hou.MenuParmTemplate(
        "sceneVariable_" + name,
        label,
        tokens,
        labels,
        default_value=tokens.index(default_token),
        help=help_text or ("MoonRay %s SceneVariable." % name),
    )
    parm.setMenuType(hou.menuType.Normal)
    return parm


TILE_ORDER_TOKENS = (
    "top",
    "bottom",
    "left",
    "right",
    "morton",
    "random",
    "spiral square",
    "spiral rect",
    "morton shiftflip",
)
TILE_ORDER_LABELS = (
    "Top",
    "Bottom",
    "Left",
    "Right",
    "Morton",
    "Random",
    "Spiral Square",
    "Spiral Rect",
    "Morton Shift Flip",
)


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
    ptg.append(
        _label(
            "resolution_mode_note",
            "Resolution Mode",
            "Manual Resolution",
        )
    )
    resolution = hou.IntParmTemplate(
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
    ptg.append(resolution)
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
    update_rop = hou.ButtonParmTemplate(
        "create_update_usd_render_rop",
        "Create / Update USD Render ROP",
        help="Create or repair the USD Render ROP owned by this MoonRay Render Settings LOP.",
    )
    update_rop.setTags(
        {
            "script_callback": "import moonray_render_settings\nmoonray_render_settings.create_or_update_usd_render_rop(hou.pwd())",
            "script_callback_language": "python",
        }
    )
    ptg.append(update_rop)

    experimental_aovs = (
        hou.ToggleParmTemplate(
            "aov_beauty",
            "Experimental Beauty RenderVar / AOV Path",
            default_value=False,
            help="Advanced diagnostic toggle. Author a Beauty RenderVar and route beauty through Houdini/Hydra AOV binding. Leave disabled for the default artist beauty path.",
        ),
        _label(
            "experimental_aov_note",
            "AOV Status",
            "Non-beauty AOVs and this Beauty RenderVar path are experimental until the production MoonRay delegate fills buffers reliably in fresh H20.5 viewport/IPR and USD Render ROP renders.",
        ),
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
            "Default beauty uses the RenderProduct output path without an authored RenderVar. The optional Beauty RenderVar path lives in Advanced / Debug for diagnostics.",
        ),
    )

    sampling = [
        _scene_menu(
            "sampling_mode",
            "Sampling Mode",
            ("uniform", "adaptive"),
            ("Uniform", "Adaptive"),
            "uniform",
            "Controls which sampling scheme to use: uniform or adaptive.",
        ),
        _scene_menu(
            "light_sampling_mode",
            "Light Sampling Mode",
            ("uniform", "adaptive"),
            ("Uniform", "Adaptive"),
            "uniform",
            "Controls which light sampling scheme to use: uniform or adaptive.",
        ),
        _scene_int(
            "pixel_samples",
            "Pixel Samples",
            8,
            max_value=4096,
            help_text="The square root of the number of primary samples taken for each pixel in uniform sampling mode.",
        ),
        _scene_int(
            "light_samples",
            "Light Samples",
            2,
            max_value=4096,
            help_text="The square root of the number of samples taken for each light on the primary intersection.",
        ),
        _scene_int(
            "bsdf_samples",
            "BSDF Samples",
            2,
            max_value=4096,
            help_text="The square root of the number of samples taken for BSDF lobe evaluations on the primary intersection.",
        ),
        _scene_int(
            "bssrdf_samples",
            "BSSRDF Samples",
            2,
            max_value=4096,
            help_text="The square root of the number of samples taken to evaluate BSSRDF contributions on the primary intersection.",
        ),
    ]
    light_sampling_quality = _scene_float(
        "light_sampling_quality",
        "Light Sampling Quality",
        0.5,
        max_value=1,
        help_text="When the light sampling mode is adaptive, this controls how many lights are sampled per light sample, where 0.0 is low quality and 1.0 is high quality.",
    )
    light_sampling_quality.setConditional(
        hou.parmCondType.DisableWhen,
        "{ sceneVariable_light_sampling_mode != adaptive }",
    )
    sampling.insert(2, light_sampling_quality)
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
        parm = _scene_int(name.replace("sceneVariable_", ""), label, default, max_value=8192, help_text=help_text)
        parm.setConditional(hou.parmCondType.DisableWhen, adaptive_cond)
        sampling.append(parm)
    target_error = _scene_float(
        "target_adaptive_error",
        "Target Adaptive Error",
        10.0,
        max_value=100.0,
        help_text="When adaptive sampling is turned on, this represents the desired quality of the output images.",
    )
    target_error.setConditional(hou.parmCondType.DisableWhen, adaptive_cond)
    sampling.append(target_error)
    sampling.append(
        _scene_toggle(
            "lock_frame_noise",
            "Lock Frame Noise",
            False,
            help_text="Use the same random seed from frame to frame instead of considering the frame number.",
        )
    )

    tile_order = (
        _scene_menu(
            "batch_tile_order",
            "Batch Tile Order",
            TILE_ORDER_TOKENS,
            TILE_ORDER_LABELS,
            "morton",
            "Specifies the order in which tiles are prioritized for batch rendering.",
        ),
        _scene_menu(
            "progressive_tile_order",
            "Progressive Tile Order",
            TILE_ORDER_TOKENS,
            TILE_ORDER_LABELS,
            "morton",
            "Specifies the order in which tiles are prioritized for progressive rendering.",
        ),
        _scene_menu(
            "checkpoint_tile_order",
            "Checkpoint Tile Order",
            TILE_ORDER_TOKENS,
            TILE_ORDER_LABELS,
            "morton",
            "Specifies the order in which tiles are prioritized for checkpoint rendering.",
        ),
    )

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
            _scene_int(
                name.replace("sceneVariable_", ""),
                label,
                default,
                max_value=128,
                help_text="MoonRay %s SceneVariable." % name.replace("sceneVariable_", ""),
            )
        )
    ray_depth.extend(
        (
            _scene_int(
                "max_subsurface_per_path",
                "Max Subsurface Per Path",
                1,
                max_value=32,
                help_text='The maximum ray depth to allow subsurface scattering. For ray depths beyond this limit Lambertian diffuse is used to approximate subsurface scattering.',
            ),
            _scene_float(
                "russian_roulette_threshold",
                "Russian Roulette Threshold",
                0.0375,
                max_value=10,
                help_text="The Russian roulette threshold specifies the luminance point at which Russian roulette is evaluated for direct light sampling and BSDF continuation.",
            ),
            _scene_float(
                "transparency_threshold",
                "Transparency Threshold",
                1.0,
                max_value=10,
                help_text="The transparency threshold defines the point at which accumulated opacity can be considered opaque.",
            ),
            _scene_float(
                "presence_threshold",
                "Presence Threshold",
                0.999,
                max_value=10,
                help_text="The presence threshold defines the point at which accumulated presence can be considered opaque.",
            ),
            _scene_float(
                "presence_quality",
                "Presence Quality",
                0.75,
                max_value=10,
                help_text="Controls the threshold for stochastic presence sampling along paths.",
            ),
        )
    )

    clamping = (
        _scene_float(
            "sample_clamping_value",
            "Sample Clamping Value",
            10.0,
            max_value=100,
            help_text="Clamp sample radiance values to this maximum value. A value of 0 disables the effect.",
        ),
        _scene_int(
            "sample_clamping_depth",
            "Sample Clamping Depth",
            1,
            max_value=32,
            help_text="Clamp sample values only after the given non-specular ray depth.",
        ),
        _scene_float(
            "roughness_clamping_factor",
            "Roughness Clamping Factor",
            0.0,
            max_value=10,
            help_text="Clamp material roughness along paths. A value of 1 clamps values to the maximum roughness encountered, while lower values temper the clamping value. 0 disables the effect. Using this technique reduces fireflies from indirect caustics but is biased.",
        ),
    )

    volumes = (
        _scene_float("volume_quality", "Volume Quality", 0.5, max_value=10, help_text="Controls the overall quality of volume rendering."),
        _scene_float("volume_shadow_quality", "Volume Shadow Quality", 1.0, max_value=10, help_text="Controls the quality of volume shadow transmittance."),
        _scene_int("volume_illumination_samples", "Volume Illumination Samples", 4, max_value=128, help_text="Sample number along the ray when computing volume scattering radiance towards the eye. Set to 0 to turn off volume lighting completely."),
        _scene_float("volume_opacity_threshold", "Volume Opacity Threshold", 0.995, max_value=10, help_text="Stop further volume integration when accumulated opacity exceeds this threshold."),
        _scene_menu(
            "volume_overlap_mode",
            "Volume Overlap Mode",
            ("sum", "max", "rnd"),
            ("Sum", "Max", "Random"),
            "sum",
            "Selects how to handle contributions from overlapping volumes.",
        ),
        _scene_float("volume_attenuation_factor", "Volume Attenuation Factor", 0.65, max_value=10, help_text="Controls how volume attenuation gets exponentially scaled down when rendering multiple scattering volumes."),
        _scene_float("volume_contribution_factor", "Volume Contribution Factor", 0.65, max_value=10, help_text="Controls how scattering contribution gets exponentially scaled down when rendering multiple scattering volumes."),
        _scene_float("volume_phase_attenuation_factor", "Volume Phase Attenuation Factor", 0.5, max_value=10, help_text="Controls how phase function anisotropy gets exponentially scaled down when rendering multiple scattering volumes."),
        _scene_int("volume_indirect_samples", "Volume Indirect Samples", 0, max_value=128, help_text="Number of indirect illumination samples on volumes per primary ray."),
    )

    filtering = (
        _scene_float("texture_blur", "Texture Blur", 0.0, max_value=10, help_text="Adjusts the amount of texture filtering."),
        _scene_float("pixel_filter_width", "Pixel Filter Width", 3.0, max_value=10, help_text="The overall extents, in pixels, of the pixel filter."),
        _scene_menu(
            "pixel_filter",
            "Pixel Filter Type",
            ("box", "cubic b-spline", "quadratic b-spline"),
            ("Box", "Cubic B-Spline", "Quadratic B-Spline"),
            "cubic b-spline",
            "The type of filter used for filter importance sampling.",
        ),
    )

    global_toggles = (
        _scene_toggle("enable_dof", "Enable DOF", True, help_text="Enables or disables camera depth-of-field."),
        _scene_toggle("enable_displacement", "Enable Displacement", True, help_text="Enables or disables geometry displacement."),
        _scene_toggle("enable_subsurface_scattering", "Enable Subsurface Scattering", True, help_text="Enables or disables subsurface scattering."),
        _scene_toggle("enable_shadowing", "Enable Shadowing", True, help_text="Enables or disables shadowing through occlusion rays."),
        _scene_toggle("enable_presence_shadows", "Enable Presence Shadows", False, help_text='Whether or not to respect a material\'s "presence" value for shadow rays.'),
        _scene_toggle("lights_visible_in_camera", "Lights Visible in Camera", False, help_text="Globally enables or disables lights being visible in camera."),
        _scene_toggle("propagate_visibility_bounce_type", "Propagate Visibility Bounce Type", False, help_text="Turns on/off propagation for ray visibility masks."),
        _scene_menu(
            "shadow_terminator_fix",
            "Shadow Terminator Fix",
            (
                "Off",
                "On",
                "On (Sine Compensation Alternative)",
                "On (GGX Compensation Alternative)",
                "On (Cosine Compensation Alternative)",
            ),
            (
                "Off",
                "On",
                "On (Sine Compensation Alternative)",
                "On (GGX Compensation Alternative)",
                "On (Cosine Compensation Alternative)",
            ),
            "Off",
            "Attempt to soften hard shadow terminator boundaries due to shading/geometric normal deviations.",
        ),
    )

    debug = (
        _scene_toggle(
            "disable_optimized_hair_sampling",
            "Disable Optimized Hair Sampling",
            False,
            help_text="Forces all hair materials to sample each hair BSDF lobe independently. This is mainly useful for troubleshooting hair LPE label behavior.",
        ),
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
                hou.FolderParmTemplate("tile_order", "Tile Order", tile_order),
                hou.FolderParmTemplate("ray_depth", "Ray Depth / Path", ray_depth),
                hou.FolderParmTemplate("clamping", "Clamping / Fireflies", clamping),
                hou.FolderParmTemplate("volumes", "Volumes", volumes),
                hou.FolderParmTemplate("filtering", "Filtering / Textures", filtering),
                hou.FolderParmTemplate("global_toggles", "Global Toggles", global_toggles),
                hou.FolderParmTemplate(
                    "advanced_debug",
                    "Advanced / Debug",
                    tuple(debug) + (hou.FolderParmTemplate("experimental_aovs", "Experimental AOVs", experimental_aovs),),
                ),
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
    definition.addSection(
        "OnCreated",
        "import moonray_render_settings\n"
        "moonray_render_settings.on_created(kwargs)\n",
    )
    definition.setExtraFileOption("OnCreated/IsPython", True)
    try:
        definition.setIcon("ROP_usdrender")
    except hou.OperationFailed:
        pass
    definition.updateFromNode(hda_node)
    hda_node.destroy()
    return str(hda_path)

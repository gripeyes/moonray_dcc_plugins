"""MoonRay Solaris Render Settings authoring helpers."""

import hou

from pxr import Gf, Sdf, UsdRender


RENDER_SETTINGS_PRIM = "/Render/rendersettings"
RENDER_PRODUCT_PRIM = "/Render/Products/renderproduct"
BEAUTY_RENDER_VAR_PRIM = "/Render/Vars/beauty"
PRODUCT_NAME = "$HIP/render/$HIPNAME.$OS.$F4.exr"


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
    product_path = _path(node, "render_product_prim", RENDER_PRODUCT_PRIM)
    beauty_var_path = _path(node, "beauty_render_var_prim", BEAUTY_RENDER_VAR_PRIM)
    camera_path = _path(node, "camera_prim", "")

    settings = UsdRender.Settings.Define(stage, settings_path)
    product = UsdRender.Product.Define(stage, product_path)
    beauty_var = UsdRender.Var.Define(stage, beauty_var_path)

    _set_rel_targets(settings, settings.CreateProductsRel, [product_path])
    if camera_path:
        _set_rel_targets(settings, settings.CreateCameraRel, [camera_path])

    width = int(_parm(node, "resolutionx", 1280))
    height = int(_parm(node, "resolutiony", 720))
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

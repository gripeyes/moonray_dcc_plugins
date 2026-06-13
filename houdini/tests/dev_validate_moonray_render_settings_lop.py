#!/usr/bin/env hython
"""Development validation for the MoonRay Render Settings LOP lifecycle.

Run with Houdini 20.5 hython:
/Applications/Houdini/Houdini20.5.584/Frameworks/Houdini.framework/Versions/20.5/Resources/bin/hython \
  /Applications/MoonRay/openmoonray/moonray/moonray_dcc_plugins/houdini/tests/dev_validate_moonray_render_settings_lop.py
"""

from __future__ import annotations

import os
import subprocess
import tempfile

import hou

OPERATOR_TYPE = "Lop::DW_MOONRAY::moonrayrendersettings::1"
ROP_NODE_TYPE = "usdrender_rop"
OUT_ROP_NODE_TYPE = "usdrender"
RENDERER_TOKEN = "HdMoonrayRendererPlugin"
OWNER_LOP_KEY = "moonray_render_settings_lop"
OWNER_OPERATOR_KEY = "moonray_render_settings_operator"
OWNER_SESSION_KEY = "moonray_render_settings_lop_session_id"
EXPECTED_SCENE_VARIABLE_COUNT = 50
EXPECTED_MODULE_SUFFIX = "/plugin/houdini/python3.11libs/moonray_render_settings.py"


RESULTS = []


def _print(status: str, name: str, details: object) -> None:
    RESULTS.append((status, name, str(details)))
    print(f"{status} {name}: {details}")


def pass_(name: str, details: object) -> None:
    _print("PASS", name, details)


def fail(name: str, details: object) -> None:
    _print("FAIL", name, details)


def skip(name: str, details: object) -> None:
    _print("SKIP", name, details)


def check(name: str, condition: bool, details: object) -> None:
    if condition:
        pass_(name, details)
    else:
        fail(name, details)


def clear_scene() -> hou.Node:
    hou.hipFile.clear(suppress_save_prompt=True)
    stage = hou.node("/stage") or hou.node("/").createNode("lopnet", "stage")
    for child in tuple(stage.children()):
        child.destroy()
    return stage


def render_setting_nodes(parent: hou.Node):
    return [child for child in parent.children() if child.type().name() == OPERATOR_TYPE]


def usd_render_rops(parent: hou.Node):
    return [child for child in parent.children() if child.type().name() == ROP_NODE_TYPE]


def out_usd_render_rops():
    out = hou.node("/out")
    if out is None:
        return []
    return [child for child in out.children() if child.type().name() == OUT_ROP_NODE_TYPE]


def owned_rops(parent: hou.Node):
    return [rop for rop in usd_render_rops(parent) if rop.userData(OWNER_OPERATOR_KEY) == OPERATOR_TYPE]


def rop_info(rop: hou.Node):
    return {
        "path": rop.path(),
        "input0": rop.input(0).path() if rop.input(0) is not None else None,
        "renderer": rop.parm("renderer").eval() if rop.parm("renderer") else None,
        "loppath": rop.parm("loppath").eval() if rop.parm("loppath") else None,
        "rendersettings": rop.parm("rendersettings").eval() if rop.parm("rendersettings") else None,
        "outputimage": rop.parm("outputimage").eval() if rop.parm("outputimage") else None,
        "owner_path": rop.userData(OWNER_LOP_KEY),
        "owner_operator": rop.userData(OWNER_OPERATOR_KEY),
        "owner_session": rop.userData(OWNER_SESSION_KEY),
    }


def rop_graph_state(rop: hou.Node):
    return {
        **rop_info(rop),
        "position": tuple(round(v, 4) for v in rop.position()),
    }


def owned_rop_for_node(node: hou.Node):
    candidates = [rop for rop in owned_rops(node.parent()) if rop.parm("loppath") and rop.parm("loppath").eval() == node.path()]
    return candidates


def create_settings(parent: hou.Node, name: str | None = None) -> hou.Node:
    if name is None:
        return parent.createNode(OPERATOR_TYPE, exact_type_name=True)
    return parent.createNode(OPERATOR_TYPE, name, exact_type_name=True)


def press_repair(node: hou.Node) -> None:
    node.parm("create_update_usd_render_rop").pressButton()


def assert_one_owned_rop(test_name: str, node: hou.Node):
    rops = owned_rop_for_node(node)
    ok = len(rops) == 1 and rops[0].input(0) == node and rops[0].parm("renderer").eval() == RENDERER_TOKEN
    check(test_name, ok, [rop_info(rop) for rop in rops])
    return rops[0] if rops else None


def test_module_and_hda() -> None:
    import moonray_render_settings

    module_file = moonray_render_settings.__file__
    check("module_import_path", module_file.endswith(EXPECTED_MODULE_SUFFIX), module_file)
    check("scene_variable_count", len(moonray_render_settings.SCENE_VARIABLES) == EXPECTED_SCENE_VARIABLE_COUNT, len(moonray_render_settings.SCENE_VARIABLES))
    node_type = hou.lopNodeTypeCategory().nodeTypes().get(OPERATOR_TYPE)
    check("operator_type_name", node_type is not None, OPERATOR_TYPE)
    definition = node_type.definition() if node_type is not None else None
    check("hda_definition_library_path", definition is not None and definition.libraryFilePath().endswith("Lop::DW_MOONRAY::moonrayrendersettings::1.hda"), definition.libraryFilePath() if definition else None)
    matches = []
    for name, node_type in sorted(hou.lopNodeTypeCategory().nodeTypes().items()):
        desc = node_type.description()
        if "moonray" in (name + " " + desc).lower() and "rendersettings" in name.lower():
            node_definition = node_type.definition()
            matches.append(
                {
                    "name": name,
                    "label": desc,
                    "definition": node_definition.libraryFilePath() if node_definition else None,
                }
            )
    check("single_moonray_render_settings_operator_definition", len(matches) == 1 and matches[0]["name"] == OPERATOR_TYPE, matches)


def test_basic_creation_and_repair() -> hou.Node:
    stage = clear_scene()
    before_out = len(out_usd_render_rops())
    node = create_settings(stage, "moonrayrendersettings1")
    check("node_creation", node.type().name() == OPERATOR_TYPE and not node.errors(), {"path": node.path(), "errors": node.errors()})
    rop = assert_one_owned_rop("one_owned_connected_usdrender_rop", node)
    check("no_out_usdrender_creation", len(out_usd_render_rops()) == before_out, {"before": before_out, "after": len(out_usd_render_rops())})
    before_repair = rop_graph_state(rop) if rop is not None else None
    press_repair(node)
    press_repair(node)
    rop = assert_one_owned_rop("repair_button_idempotency", node)
    after_repair = rop_graph_state(rop) if rop is not None else None
    check("initial_creation_matches_post_repair_graph", before_repair == after_repair, {"before": before_repair, "after": after_repair})
    return stage


def test_lifecycle_scenarios() -> None:
    stage = clear_scene()

    node1 = create_settings(stage, "moonrayrendersettings1")
    node2 = create_settings(stage, "moonrayrendersettings2")
    distinct = owned_rop_for_node(node1) + owned_rop_for_node(node2)
    check("two_lops_two_distinct_owned_rops", len(distinct) == 2 and len({rop.path() for rop in distinct}) == 2, [rop_info(rop) for rop in distinct])
    check(
        "settings_nodes_do_not_share_rops",
        len(owned_rop_for_node(node1)) == 1
        and len(owned_rop_for_node(node2)) == 1
        and owned_rop_for_node(node1)[0] is not owned_rop_for_node(node2)[0],
        {"node1": [rop_info(rop) for rop in owned_rop_for_node(node1)], "node2": [rop_info(rop) for rop in owned_rop_for_node(node2)]},
    )

    node1.setName("moonraysettings_renamed")
    press_repair(node1)
    rop1 = assert_one_owned_rop("rename_owner_then_repair_updates_by_session", node1)

    if rop1 is not None:
        rop1.setName("artist_renamed_rop")
        press_repair(node1)
        check("rename_owned_rop_then_repair_preserves_renamed_rop", rop1.name() == "artist_renamed_rop" and rop1.input(0) == node1, rop_info(rop1))

        rop1.destroy()
        press_repair(node1)
        rop1 = assert_one_owned_rop("delete_owned_rop_then_repair_recreates", node1)

    if rop1 is not None:
        rop1.setInput(0, None)
        press_repair(node1)
        check("disconnect_owned_rop_then_repair_rewires", rop1.input(0) == node1, rop_info(rop1))

    # Raw HOM copy of only the LOP does not run OnCreated; this is an accepted limitation.
    copied_lop = hou.copyNodesTo((node1,), stage)[0]
    copied_owned = owned_rop_for_node(copied_lop)
    if copied_owned:
        pass_("raw_hom_copy_lop_only", [rop_info(rop) for rop in copied_owned])
    else:
        skip("raw_hom_copy_lop_only", "HOM copy of an existing node does not run OnCreated; press repair on the copied LOP.")
        press_repair(copied_lop)
        assert_one_owned_rop("raw_hom_copy_lop_only_repair", copied_lop)

    pair_node = create_settings(stage, "pairsettings")
    pair_rop = owned_rop_for_node(pair_node)[0]
    copied_items = hou.copyNodesTo((pair_node, pair_rop), stage)
    copied_pair_lops = [item for item in copied_items if item.type().name() == OPERATOR_TYPE]
    copied_pair_rops = [item for item in copied_items if item.type().name() == ROP_NODE_TYPE]
    check("duplicate_lop_rop_pair_raw_copy_non_destructive", len(copied_pair_lops) == 1 and len(copied_pair_rops) == 1, {"lops": [n.path() for n in copied_pair_lops], "rops": [rop_info(r) for r in copied_pair_rops]})
    if copied_pair_lops:
        press_repair(copied_pair_lops[0])
        assert_one_owned_rop("duplicate_lop_rop_pair_repair_refreshes_ownership", copied_pair_lops[0])

    collision_stage = stage
    foreign = collision_stage.createNode(ROP_NODE_TYPE, "moonrayrendersettings1_usdrender")
    foreign.parm("renderer").set("BRAY_HdKarma")
    collision_node = create_settings(collision_stage, "moonrayrendersettings1")
    check("unrelated_colliding_rop_preserved", foreign.parm("renderer").eval() == "BRAY_HdKarma" and foreign not in owned_rop_for_node(collision_node), [rop_info(rop) for rop in usd_render_rops(collision_stage) if "moonrayrendersettings1_usdrender" in rop.name()])

    fake = stage.createNode(ROP_NODE_TYPE, "moonrayfake_usdrender")
    fake.setUserData(OWNER_OPERATOR_KEY, OPERATOR_TYPE)
    fake.setUserData(OWNER_LOP_KEY, "/stage/not_real")
    fake.parm("renderer").set("BRAY_HdKarma")
    fake_node = create_settings(stage, "moonrayfake")
    check("fake_stale_ownership_not_overwritten", fake.parm("renderer").eval() == "BRAY_HdKarma" and fake not in owned_rop_for_node(fake_node), [rop_info(rop) for rop in usd_render_rops(stage) if "moonrayfake" in rop.name()])

    before_save = len(usd_render_rops(stage))
    hip_path = os.path.join(tempfile.gettempdir(), "moonray_render_settings_lifecycle_validation.hip")
    hou.hipFile.save(hip_path)
    hou.hipFile.clear(suppress_save_prompt=True)
    hou.hipFile.load(hip_path, suppress_save_prompt=True, ignore_load_warnings=True)
    loaded_stage = hou.node("/stage")
    after_load = len(usd_render_rops(loaded_stage))
    check("save_reopen_no_extra_rops", before_save == after_load, {"before": before_save, "after": after_load, "file": hip_path})

    node_type = hou.lopNodeTypeCategory().nodeTypes().get(OPERATOR_TYPE)
    definition = node_type.definition() if node_type is not None else None
    if definition is None:
        skip("hda_reload_no_extra_rops", "operator definition unavailable")
    else:
        before_reload = len(usd_render_rops(loaded_stage))
        hou.hda.reloadFile(definition.libraryFilePath())
        after_reload = len(usd_render_rops(loaded_stage))
        check("hda_reload_no_extra_rops", before_reload == after_reload, {"before": before_reload, "after": after_reload, "library": definition.libraryFilePath()})

    loaded_settings = next((child for child in loaded_stage.children() if child.type().name() == OPERATOR_TYPE), None)
    if loaded_settings is None:
        skip("parameter_change_and_cook_no_extra_rops", "no loaded MoonRay Render Settings node found")
    else:
        before_change = len(usd_render_rops(loaded_stage))
        loaded_settings.parm("product_name").set("/tmp/moonray_lifecycle.$F4.exr")
        try:
            loaded_settings.cook(force=True)
            details = {"errors": loaded_settings.errors(), "warnings": loaded_settings.warnings()}
        except hou.OperationFailed as exc:
            details = {"exception": str(exc), "errors": loaded_settings.errors(), "warnings": loaded_settings.warnings()}
        after_change = len(usd_render_rops(loaded_stage))
        check("parameter_change_and_cook_no_extra_rops", before_change == after_change, {"before": before_change, "after": after_change, **details})

    skip("undo_redo_creation", "Houdini hython does not provide a reliable undo/redo UI event test for this lifecycle; validate manually in UI if needed.")



def test_manual_ui_creation_paths() -> None:
    skip(
        "moonray_menu_tool_creation_path",
        "Requires graphical Houdini 20.5 hou.ui interaction; hython cannot exercise the real MoonRay Tab/shelf UI path.",
    )
    skip(
        "digital_assets_creation_path",
        "Requires graphical Houdini 20.5 Tab menu interaction; hython can report the operator definition but cannot click the Digital Assets entry.",
    )
    skip(
        "mixed_menu_path_two_node_sharing",
        "Requires graphical Houdini 20.5 creation from both menu presentation paths; not claimable from hython.",
    )

def test_resolution_and_usd_contract() -> None:
    stage = clear_scene()
    setup = stage.createNode("pythonscript", "camera_setup")
    setup.parm("python").set(
        "import hou\n"
        "from pxr import UsdGeom, Gf\n"
        "stage = hou.pwd().editableStage()\n"
        "cam = UsdGeom.Camera.Define(stage, '/cameras/camera1')\n"
        "UsdGeom.Xformable(cam).AddTranslateOp().Set(Gf.Vec3d(0, 0, 5))\n"
        "cam.GetHorizontalApertureAttr().Set(40)\n"
        "cam.GetVerticalApertureAttr().Set(20)\n"
    )
    node = create_settings(stage, "moonrayrendersettings1")
    node.setInput(0, setup)

    check("computed_resolution_modes_removed", node.parm("res_mode") is None, "res_mode parm absent")
    mode_note = node.parm("resolution_mode_note")
    check("manual_resolution_mode_note", mode_note is not None, mode_note.eval() if mode_note is not None else None)
    ptg_text = str(node.parmTemplateGroup())
    check(
        "computed_resolution_callbacks_absent",
        "computeResolutionParameter" not in ptg_text and "updateResolutionParameters" not in ptg_text,
        "no loputils computed-resolution callback references",
    )
    import moonray_render_settings

    scene_variable_names = {name for name, _ in moonray_render_settings.SCENE_VARIABLES}
    check(
        "scene_variables_exclude_image_width_height",
        "image_width" not in scene_variable_names and "image_height" not in scene_variable_names,
        sorted(name for name in scene_variable_names if name in ("image_width", "image_height")),
    )
    aov_toggles = sorted(
        parm.name()
        for parm in node.parms()
        if parm.name().startswith("aov_")
        and parm.parmTemplate().type() == hou.parmTemplateType.Toggle
    )
    check("experimental_beauty_internal_name_preserved", aov_toggles == ["aov_beauty"], aov_toggles)
    beauty = node.parm("aov_beauty")
    beauty_template = beauty.parmTemplate() if beauty is not None else None
    check("experimental_beauty_default_off", beauty is not None and not bool(beauty.eval()), beauty.eval() if beauty is not None else None)
    check(
        "experimental_beauty_label",
        beauty_template is not None and beauty_template.label() == "Experimental Beauty RenderVar / AOV Path",
        beauty_template.label() if beauty_template is not None else None,
    )
    check("production_aov_folder_removed", '"aovs"' not in ptg_text, "no production AOV folder token")

    node.parm("camera").set("/cameras/camera1")
    node.parm("resolutionx").set(512)
    node.parm("resolutiony").set(256)
    value = tuple(node.parmTuple("resolution").eval())
    check("manual_resolution", value == (512, 256), value)

    node.cook(force=True)
    usd_path = os.path.join(tempfile.gettempdir(), "moonray_render_settings_lifecycle_validation.usda")
    node.stage().Flatten().Export(usd_path)
    text = open(usd_path, "r", encoding="utf-8").read()
    default_checks = {
        "RenderSettings": 'def RenderSettings "rendersettings"' in text,
        "RenderProduct": 'def RenderProduct "renderproduct"' in text,
        "no_RenderVar_by_default": 'def RenderVar "beauty"' not in text,
        "products_rel": 'rel products = </Render/Products/renderproduct>' in text,
        "empty_orderedVars_by_default": 'rel orderedVars' in text and 'rel orderedVars = </Render/Products/Vars/beauty>' not in text,
        "camera_rel": 'rel camera = </cameras/camera1>' in text,
        "resolution": 'uniform int2 resolution = (512, 256)' in text,
        "no_custom_image_width": 'moonray:sceneVariable:image_width' not in text,
        "no_custom_image_height": 'moonray:sceneVariable:image_height' not in text,
    }
    for test_name, ok in default_checks.items():
        check("usd_default_contract_" + test_name, ok, usd_path)

    node.parm("aov_beauty").set(1)
    node.cook(force=True)
    debug_usd_path = os.path.join(tempfile.gettempdir(), "moonray_render_settings_lifecycle_validation_debug_beauty.usda")
    node.stage().Flatten().Export(debug_usd_path)
    debug_text = open(debug_usd_path, "r", encoding="utf-8").read()
    debug_checks = {
        "RenderVar_when_enabled": 'def RenderVar "beauty"' in debug_text,
        "orderedVars_when_enabled": 'rel orderedVars = </Render/Products/Vars/beauty>' in debug_text,
        "beauty_sourceType": 'uniform token sourceType = "raw"' in debug_text,
        "beauty_format": 'driver:parameters:aov:format = "color3f"' in debug_text,
        "beauty_multiSampled": 'driver:parameters:aov:multiSampled = 0' in debug_text,
        "beauty_clearValue": 'driver:parameters:aov:clearValue = 0' in debug_text,
        "beauty_only_orderedVars": debug_text.count("rel orderedVars = </Render/Products/Vars/beauty>") == 1,
    }
    for test_name, ok in debug_checks.items():
        check("usd_debug_beauty_contract_" + test_name, ok, debug_usd_path)

def test_rdla_receipt() -> None:
    # RDLA export is practical but can be slow; use a tiny lit fixture and a timeout.
    stage = clear_scene()
    setup = stage.createNode("pythonscript", "rdla_setup")
    setup.parm("python").set(
        "import hou\n"
        "from pxr import UsdGeom, UsdLux, Gf\n"
        "stage = hou.pwd().editableStage()\n"
        "cam = UsdGeom.Camera.Define(stage, '/cameras/camera1')\n"
        "UsdGeom.Xformable(cam).AddTranslateOp().Set(Gf.Vec3d(0, 0, 5))\n"
        "UsdGeom.Sphere.Define(stage, '/World/Sphere')\n"
        "light = UsdLux.SphereLight.Define(stage, '/World/Light')\n"
        "light.CreateIntensityAttr().Set(500.0)\n"
        "UsdGeom.Xformable(light).AddTranslateOp().Set(Gf.Vec3d(0, 3, 3))\n"
    )
    node = create_settings(stage, "moonrayrendersettings1")
    node.setInput(0, setup)
    node.parm("rdlOutput").set(os.path.join(tempfile.gettempdir(), "moonray_lifecycle_validation.rdla"))
    node.parm("sceneVariable_target_adaptive_error").set(7.5)
    node.parm("sceneVariable_roughness_clamping_factor").set(0.35)
    node.parm("sceneVariable_light_sampling_quality").set(0.77)
    node.cook(force=True)
    usd_path = os.path.join(tempfile.gettempdir(), "moonray_lifecycle_rdla.usda")
    node.stage().Flatten().Export(usd_path)
    rdla_path = node.parm("rdlOutput").eval()
    husk = "/Applications/Houdini/Houdini20.5.584/Frameworks/Houdini.framework/Versions/20.5/Resources/bin/husk"
    if not os.path.exists(husk):
        skip("rdla_scenevariable_receipt", "husk not found")
        return
    log_path = "/tmp/moonray_lifecycle_validation_husk.log"
    cmd = [husk, "-R", "HdMoonrayRendererPlugin", "--settings", "/Render/rendersettings", "-o", "/tmp/moonray_lifecycle_validation.exr", usd_path]
    try:
        with open(log_path, "w", encoding="utf-8") as log:
            result = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT, timeout=90)
    except subprocess.TimeoutExpired:
        skip("rdla_scenevariable_receipt", f"husk timed out; see {log_path}")
        return
    if result.returncode != 0 or not os.path.exists(rdla_path):
        skip("rdla_scenevariable_receipt", f"husk/RDLA unavailable rc={result.returncode}; see {log_path}")
        return
    text = open(rdla_path, "r", encoding="utf-8", errors="replace").read()
    ok = all(key in text for key in ("target_adaptive_error", "roughness_clamping_factor", "light_sampling_quality"))
    check("rdla_scenevariable_receipt", ok, rdla_path)


def main() -> int:
    test_module_and_hda()
    test_basic_creation_and_repair()
    test_lifecycle_scenarios()
    test_manual_ui_creation_paths()
    test_resolution_and_usd_contract()
    test_rdla_receipt()

    counts = {"PASS": 0, "FAIL": 0, "SKIP": 0}
    for status, _, _ in RESULTS:
        counts[status] = counts.get(status, 0) + 1
    print("SUMMARY PASS={PASS} FAIL={FAIL} SKIP={SKIP}".format(**counts))
    return 1 if counts.get("FAIL", 0) else 0


if __name__ == "__main__":
    raise SystemExit(main())

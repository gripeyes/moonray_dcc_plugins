"""Generate MoonRay light-filter VOP HDAs for Solaris Light Filter Library.

The standard Houdini Light Filter Library LOP consumes VOP nodes whose shader
type is ``lightfilter`` and authors UsdLux PluginLightFilter prims. These
generated nodes keep MoonRay on that native Solaris path while preserving the
native MoonRay filter class and parameter names.
"""

from __future__ import annotations

import os
from pathlib import Path

import hou


TEMPLATE_NODE = "kma_lfilter_attenuation"
USD_LIGHTFILTER_EXTRA_INFO = "shadertype=lightfilter visibleoutputs=0 vopnetmask='usdlightfilter' "

def toggle(name, label, default="0", help_text=""):
    return {
        "name": name,
        "label": label,
        "vop_type": "int",
        "parm_type": "toggle",
        "default": default,
        "script_ritype": "int",
        "help": help_text,
    }


def int_parm(name, label, default="0", value_range=None, help_text="", menu=None):
    item = {
        "name": name,
        "label": label,
        "vop_type": "int",
        "parm_type": "integer",
        "default": default,
        "script_ritype": "int",
        "help": help_text,
    }
    if value_range is not None:
        item["range"] = value_range
    if menu is not None:
        item["menu"] = menu
    return item


def float_parm(name, label, default="0", value_range=None, help_text=""):
    item = {
        "name": name,
        "label": label,
        "vop_type": "float",
        "parm_type": "float",
        "default": default,
        "script_ritype": "float",
        "help": help_text,
    }
    if value_range is not None:
        item["range"] = value_range
    return item


def color_parm(name, label, default=("1", "1", "1"), help_text=""):
    return {
        "name": name,
        "label": label,
        "vop_type": "vector",
        "parm_type": "color",
        "default": default,
        "range": (0, 1),
        "script_ritype": "color",
        "help": help_text,
    }


def string_parm(name, label, default="", help_text=""):
    return {
        "name": name,
        "label": label,
        "vop_type": "string",
        "parm_type": "string",
        "default": default,
        "script_ritype": "string",
        "help": help_text,
    }


LIGHT_FILTERS = {
    "IntensityLightFilter": {
        "label": "MoonRay Intensity Light Filter",
        "folder": ("intensity_filter", "Intensity Filter"),
        "inputs": [
            {
                "name": "on",
                "label": "On",
                "vop_type": "int",
                "parm_type": "toggle",
                "default": "1",
                "script_ritype": "int",
                "help": "Turns the light filter on/off.",
            },
            {
                "name": "intensity",
                "label": "Intensity",
                "vop_type": "float",
                "parm_type": "float",
                "default": "1",
                "range": (0, 10),
                "script_ritype": "float",
                "help": "Multiply the light radiance by this intensity value",
            },
            {
                "name": "exposure",
                "label": "Exposure",
                "vop_type": "float",
                "parm_type": "float",
                "default": "0",
                "range": (-10, 10),
                "script_ritype": "float",
                "help": "Multiply the light radiance by exposure = pow(2, exposure)",
            },
            {
                "name": "color",
                "label": "Color",
                "vop_type": "vector",
                "parm_type": "color",
                "default": ("1", "1", "1"),
                "range": (0, 1),
                "script_ritype": "color",
                "help": "Multiply the light radiance by this RGB color value",
            },
            {
                "name": "invert",
                "label": "Invert",
                "vop_type": "int",
                "parm_type": "toggle",
                "default": "0",
                "script_ritype": "int",
                "help": "Invert the light radiance by 1/radiance",
            },
            {
                "name": "light_path_selection",
                "label": "Light Path Selection",
                "vop_type": "int",
                "parm_type": "integer",
                "default": "0",
                "script_ritype": "int",
                "menu": [
                    ("0", "All Light Paths"),
                    ("1", "All Indirect"),
                    ("2", "All Indirect First Bounce"),
                    ("3", "Indirect Diffuse"),
                    ("4", "Indirect Diffuse First Bounce"),
                    ("5", "Indirect Specular"),
                    ("6", "Indirect Specular First Bounce"),
                ],
                "help": "Controls which light paths the filter is applied to.",
            },
        ],
    },
    "DecayLightFilter": {
        "label": "MoonRay Decay Light Filter",
        "folder": ("decay_filter", "Decay Filter"),
        "inputs": [
            {
                "name": "on",
                "label": "On",
                "vop_type": "int",
                "parm_type": "toggle",
                "default": "1",
                "script_ritype": "int",
                "help": "Turns the light filter on or off.",
            },
            {
                "name": "falloff_near",
                "label": "Falloff Near",
                "vop_type": "int",
                "parm_type": "toggle",
                "default": "0",
                "script_ritype": "int",
                "help": "does the light fade in?",
            },
            {
                "name": "near_start",
                "label": "Near Start",
                "vop_type": "float",
                "parm_type": "float",
                "default": "0",
                "range": (0, 100),
                "script_ritype": "float",
                "help": "distance from light to start of fade in",
            },
            {
                "name": "near_end",
                "label": "Near End",
                "vop_type": "float",
                "parm_type": "float",
                "default": "0",
                "range": (0, 100),
                "script_ritype": "float",
                "help": "distance from light to end of fade in",
            },
            {
                "name": "falloff_far",
                "label": "Falloff Far",
                "vop_type": "int",
                "parm_type": "toggle",
                "default": "0",
                "script_ritype": "int",
                "help": "does the light fade out?",
            },
            {
                "name": "far_start",
                "label": "Far Start",
                "vop_type": "float",
                "parm_type": "float",
                "default": "0",
                "range": (0, 100),
                "script_ritype": "float",
                "help": "distance from light to start of fade out",
            },
            {
                "name": "far_end",
                "label": "Far End",
                "vop_type": "float",
                "parm_type": "float",
                "default": "0",
                "range": (0, 100),
                "script_ritype": "float",
                "help": "distance from light to end of fade out",
            },
        ],
    },
        "BarnDoorLightFilter": {
        "label": "MoonRay Barn Door Light Filter",
        "folder": ("barn_door_filter", "Barn Door Filter"),
        "inputs": [
            toggle("on", "On", "1", "Turns the light filter on or off."),
            int_parm(
                "projector_type",
                "Projector Type",
                "0",
                menu=[
                    ("0", "Perspective"),
                    ("1", "Orthographic"),
                ],
                help_text="The projection type used to map points to the flap opening.",
            ),
            float_parm(
                "projector_focal_distance",
                "Projector Focal Distance",
                "30",
                (0, 100),
                "Distance of the flap opening from the projector origin.",
            ),
            float_parm(
                "projector_width",
                "Projector Width",
                "1",
                (0, 100),
                "Width of the flap opening.",
            ),
            float_parm(
                "projector_height",
                "Projector Height",
                "1",
                (0, 100),
                "Height of the flap opening.",
            ),
            float_parm(
                "edge_scale_top",
                "Edge Scale Top",
                "1",
                (0, 10),
                "Scale factor for the top edge.",
            ),
            float_parm(
                "edge_scale_bottom",
                "Edge Scale Bottom",
                "1",
                (0, 10),
                "Scale factor for the bottom edge.",
            ),
            float_parm(
                "edge_scale_left",
                "Edge Scale Left",
                "1",
                (0, 10),
                "Scale factor for the left edge.",
            ),
            float_parm(
                "edge_scale_right",
                "Edge Scale Right",
                "1",
                (0, 10),
                "Scale factor for the right edge.",
            ),
            int_parm(
                "pre_barn_mode",
                "Pre Barn Mode",
                "2",
                menu=[
                    ("0", "Black"),
                    ("1", "White"),
                    ("2", "Default"),
                ],
                help_text="Controls the region before the pre barn distance.",
            ),
            float_parm(
                "pre_barn_distance",
                "Pre Barn Distance",
                "0.5",
                (0, 100),
                "Distance where the pre barn mode takes effect.",
            ),
            float_parm(
                "density",
                "Density",
                "1",
                (0, 1),
                "Fades the filter effect.",
            ),
            toggle(
                "invert",
                "Invert",
                "0",
                "Swap application of the filter from inside to outside.",
            ),
            float_parm(
                "radius",
                "Radius",
                "0",
                (0, 1),
                "Rounded box radius.",
            ),
            float_parm(
                "edge",
                "Edge",
                "0",
                (0, 1),
                "Transition zone size.",
            ),
            int_parm(
                "mode",
                "Mode",
                "0",
                menu=[
                    ("0", "Analytical"),
                    ("1", "Physical"),
                ],
                help_text="Analytical or physical barn door mode.",
            ),
            float_parm(
                "size_top",
                "Size Top",
                "0",
                (-100, 100),
                "Additional size on the top edge.",
            ),
            float_parm(
                "size_bottom",
                "Size Bottom",
                "0",
                (-100, 100),
                "Additional size on the bottom edge.",
            ),
            float_parm(
                "size_left",
                "Size Left",
                "0",
                (-100, 100),
                "Additional size on the left edge.",
            ),
            float_parm(
                "size_right",
                "Size Right",
                "0",
                (-100, 100),
                "Additional size on the right edge.",
            ),
            toggle(
                "use_light_xform",
                "Use Light Xform",
                "1",
                "Attach the filter to the light and ignore node_xform.",
            ),
            float_parm(
                "rotation",
                "Rotation",
                "0",
                (-180, 180),
                "Rotation around the focal direction, in degrees.",
            ),
            color_parm(
                "color",
                "Color",
                ("1", "1", "1"),
                "Color within the Barn Door lit region.",
            ),
        ],
    },
}


TYPE_OPTIONS = """SaveSpareParms := 0;
CheckExternal := 1;
SaveIcon := 1;
GzipContents := 1;
ContentsCompressionType := 1;
UnlockOnCreate := 0;
SaveCachedCode := 0;
LockContents := 1;
MakeDefault := 1;
UseDSParms := 1;
ForbidOutsideParms := 1;
PrefixDroppedParmLabel := 0;
PrefixDroppedParmName := 0;
ParmsFromVfl := 0;
"""


TOOLS_SHELF = """<?xml version="1.0" encoding="UTF-8"?>
<shelfDocument>
  <tool name="$HDA_DEFAULT_TOOL" label="$HDA_LABEL" icon="$HDA_ICON">
    <toolMenuContext name="viewer">
      <contextNetType>VOP</contextNetType>
    </toolMenuContext>
    <toolMenuContext name="network">
      <contextOpType>$HDA_TABLE_AND_NAME</contextOpType>
    </toolMenuContext>
    <toolSubmenu>MoonRay/Light Filters</toolSubmenu>
    <toolSubmenu>DW Moonray</toolSubmenu>
    <script scriptType="python"><![CDATA[import voptoolutils
voptoolutils.genericTool(kwargs, '$HDA_NAME')
]]></script>
  </tool>
</shelfDocument>
"""


def _quote(value: str) -> str:
    return '"' + str(value).replace("\\", "\\\\").replace('"', '\\"') + '"'


def _default_values(default):
    if isinstance(default, (tuple, list)):
        return " ".join(_quote(v) for v in default)
    return _quote(default)


def _parm_dialog(input_def: dict) -> str:
    lines = [
        "        parm {",
        f"            name {_quote(input_def['name'])}",
        f"            label {_quote(input_def['label'])}",
        f"            type {input_def['parm_type']}",
        f"            size {3 if input_def['parm_type'] == 'color' else 1}",
        "            export none",
        f"            default {{ {_default_values(input_def['default'])} }}",
    ]
    if "range" in input_def:
        lo, hi = input_def["range"]
        lines.append(f"            range {{ {lo} {hi} }}")
    if "menu" in input_def:
        lines.append("            menu {")
        for token, label in input_def["menu"]:
            lines.append(f"                {_quote(token)} {_quote(label)}")
        lines.append("            }")
    if "help" in input_def:
        lines.append(f"            help {_quote(input_def['help'])}")
    lines.append(f"            parmtag {{ script_ritype {_quote(input_def['script_ritype'])} }}")
    lines.append("        }")
    return "\n".join(lines)


def _dialog_script(class_name: str, spec: dict) -> str:
    folder_name, folder_label = spec["folder"]
    input_lines = [
        f"    input {item['vop_type']} {item['name']} {_quote(item['label'])}"
        for item in spec["inputs"]
    ]
    input_flags = [f"    inputflags {item['name']} 0" for item in spec["inputs"]]
    signature_types = " ".join(item["vop_type"] for item in spec["inputs"])
    parms = "\n".join(_parm_dialog(item) for item in spec["inputs"])
    return f"""# Dialog script for Vop::DW_MOONRAY::{class_name}::1 automatically generated
{{
    name {_quote(f"Vop::DW_MOONRAY::{class_name}::1")}
    script {_quote(class_name)}
    label {_quote(spec['label'])}
    rendermask moonray
    shadertype lightfilter
    externalshader 1

{chr(10).join(input_lines)}
    output lightfilter filter Filter
{chr(10).join(input_flags)}
    signature "Default Inputs" default {{ {signature_types} }}

    help {{
        {_quote(spec['label'])}
    }}

    group {{
        name {_quote(folder_name)}
        label {_quote(folder_label)}
{parms}
    }}
}}
"""


def generate(output_dir: str | os.PathLike[str] | None = None) -> list[Path]:
    if output_dir is None:
        output_dir = Path(__file__).resolve().parents[1] / "otls"
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    template = hou.nodeType(hou.vopNodeTypeCategory(), TEMPLATE_NODE)
    if template is None or template.definition() is None:
        raise RuntimeError(f"Could not find template VOP node {TEMPLATE_NODE}")

    written = []
    for class_name, spec in LIGHT_FILTERS.items():
        hda_name = f"Vop::DW_MOONRAY::{class_name}::1"
        hda_path = output_dir / f"{hda_name}.hda"

        if hda_path.exists():
            hda_path.unlink()

        template.definition().copyToHDAFile(
            str(hda_path),
            new_name=hda_name,
            new_menu_name=spec["label"],
        )

        hou.hda.installFile(str(hda_path))
        node_type = hou.nodeType(hou.vopNodeTypeCategory(), hda_name)

        if node_type is None or node_type.definition() is None:
            raise RuntimeError(f"Generated HDA did not register {hda_name}")

        definition = node_type.definition()

        definition.addSection("DialogScript", _dialog_script(class_name, spec))
        definition.addSection("TypePropertiesOptions", TYPE_OPTIONS)
        definition.addSection("Tools.shelf", TOOLS_SHELF)

        # Critical for Solaris Light Filter Library visibility.
        # The generated node must belong to the USD light-filter VOP context,
        # not RIS / RenderMan.
        definition.setExtraInfo(USD_LIGHTFILTER_EXTRA_INFO)

        definition.setDescription(spec["label"])
        definition.setIcon("NETWORKS/shop")

        # Persist the edited definition into the HDA file.
        definition.save(str(hda_path), create_backup=False)

        # Reinstall/requery so validation checks the saved definition.
        hou.hda.installFile(str(hda_path))
        node_type = hou.nodeType(hou.vopNodeTypeCategory(), hda_name)

        if node_type is None or node_type.definition() is None:
            raise RuntimeError(f"Generated HDA disappeared after save: {hda_name}")

        definition = node_type.definition()
        mask = node_type.vopnetMask()
        extra_info = definition.extraInfo()

        if mask != "usdlightfilter":
            raise RuntimeError(
                f"{hda_name} has wrong vopnetMask {mask!r}; "
                "expected 'usdlightfilter'"
            )

        if "risnet" in extra_info.lower():
            raise RuntimeError(
                f"{hda_name} still contains RIS extraInfo: {extra_info!r}"
            )

        if "shadertype=lightfilter" not in extra_info:
            raise RuntimeError(
                f"{hda_name} is missing shadertype=lightfilter extraInfo: "
                f"{extra_info!r}"
            )

        written.append(hda_path)

    return written


if __name__ == "__main__":
    for path in generate():
        print(path)

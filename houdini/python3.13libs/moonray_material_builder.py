"""MoonRay Solaris material builder helpers."""

import hou
import voptoolutils


MOONRAY_TAB_MASK = (
    "moonray parameter constant rampparm collect null subnet "
    "subnetconnector suboutput subinput genericshader"
)


def _set_if_present(node, parms):
    existing = {parm.name() for parm in node.parms()}
    node.setParms({name: value for name, value in parms.items() if name in existing})


def _create_output_connector(subnet_node, name, label, parm_type, color, input_node):
    connector = subnet_node.createNode("subnetconnector", "{}_output".format(name))
    _set_if_present(
        connector,
        {
            "parmname": name,
            "parmlabel": label,
            "parmtype": parm_type,
            "connectorkind": 1,
            "useasparmdefiner": 0,
        },
    )
    connector.setColor(hou.Color(color))
    connector.setInput(0, input_node, 0)
    return connector


def setup_moonray_material_builder(subnet_node):
    """Configure a plain VOP subnet as a MoonRay-native material builder."""
    subnet_node.setShaderLanguageName("VEX")
    voptoolutils._addMtlSubnetParms(  # pylint: disable=protected-access
        subnet_node, MOONRAY_TAB_MASK, "moonray", "MoonRay Material Builder"
    )

    suboutput = subnet_node.node("suboutput1")
    if suboutput is not None:
        suboutput.destroy()
    subinput = subnet_node.node("subinput1")
    if subinput is not None:
        subinput.setName("inputs", unique_name=True)

    surface = subnet_node.createNode("Vop::DW_MOONRAY::DwaBaseMaterial::1", "dwa_base")
    displacement = subnet_node.createNode(
        "Vop::DW_MOONRAY::NormalDisplacement::1", "normal_displacement"
    )
    _set_if_present(displacement, {"height": 0.0, "height_multiplier": 0.0})
    _create_output_connector(
        subnet_node, "surface", "Surface", 24, (0.89, 0.69, 0.6), surface
    )
    _create_output_connector(
        subnet_node, "displacement", "Displacement", 25, (0.6, 0.69, 0.89), displacement
    )
    subnet_node.setMaterialFlag(True)
    subnet_node.layoutChildren()
    return subnet_node


def create_moonray_material_builder(kwargs, name="moonraymaterial"):
    """Create the artist-facing MoonRay Material Builder subnet."""
    destination = kwargs.get("node")
    if destination is not None and not hasattr(hou, "ui"):
        subnet_node = destination.createNode("subnet", name)
    else:
        subnet_node = voptoolutils.genericTool(kwargs, "subnet", name)
    return setup_moonray_material_builder(subnet_node)

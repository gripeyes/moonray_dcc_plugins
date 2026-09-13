#!/usr/bin/env hython
"""Validate the public output connectors on shipped MoonRay VOP HDAs."""

from __future__ import print_function

import argparse
import glob
import os
import shlex
import sys

import hou


HOUDINI_OUTPUT_TYPES = {
    # Houdini calls a VEX volume shader connector "atmosphere" in HOM.
    "volume": "atmosphere",
}


def _output_declaration(definition):
    dialog_script = definition.sections()["DialogScript"].contents()
    output_lines = [
        shlex.split(line)
        for line in dialog_script.splitlines()
        if line.strip().startswith("output")
        and not line.strip().startswith("outputoverrides")
    ]
    if len(output_lines) != 1 or len(output_lines[0]) != 4:
        raise ValueError("expected one output declaration, got {}".format(output_lines))
    _, data_type, name, label = output_lines[0]
    return name, label, HOUDINI_OUTPUT_TYPES.get(data_type, data_type)


def _node_problems(node):
    if node.errors() or node.warnings():
        return "errors={}, warnings={}".format(node.errors(), node.warnings())
    return None


def _validate_imagemap_connection(material_network, failures):
    image = material_network.createNode("Vop::DW_MOONRAY::ImageMap::1")
    material = material_network.createNode("Vop::DW_MOONRAY::DwaBaseMaterial::1")
    try:
        if len(image.outputNames()) != 1 or image.outputDataTypes() != ("vector",):
            failures.append(
                "ImageMap integration: expected one vector output, got names={} types={}".format(
                    image.outputNames(), image.outputDataTypes()))
            return

        try:
            albedo_index = material.inputNames().index("albedo")
        except ValueError:
            failures.append("ImageMap integration: DwaBaseMaterial has no albedo input")
            return

        material.setInput(albedo_index, image, 0)
        if material.input(albedo_index) != image:
            failures.append("ImageMap integration: albedo connection was not retained")
        if material.inputDataTypes()[albedo_index] != image.outputDataTypes()[0]:
            failures.append(
                "ImageMap integration: output type {} does not match albedo type {}".format(
                    image.outputDataTypes()[0], material.inputDataTypes()[albedo_index]))
        for node in (image, material):
            problem = _node_problems(node)
            if problem:
                failures.append("ImageMap integration {}: {}".format(node.name(), problem))
    finally:
        material.destroy()
        image.destroy()


def _validate_material_builder(material_network, failures):
    python_lib = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "houdini", "python3.13libs"))
    if python_lib not in sys.path:
        sys.path.insert(0, python_lib)
    import moonray_material_builder

    subnet = material_network.createNode("subnet", "moonray_output_validation")
    builder = moonray_material_builder.setup_moonray_material_builder(subnet)
    try:
        expected = (("surface", "displacement"), ("Surface", "Displacement"),
                    ("surface", "displacement"))
        actual = (builder.outputNames(), builder.outputLabels(), builder.outputDataTypes())
        if actual != expected:
            failures.append(
                "Material builder: expected outputs {}, got {}".format(expected, actual))

        suboutput = builder.node("suboutput1")
        surface = builder.node("dwa_base")
        displacement = builder.node("normal_displacement")
        if suboutput is None or surface is None or displacement is None:
            failures.append("Material builder: missing generated child nodes")
        else:
            if suboutput.input(0) != surface or suboutput.input(1) != displacement:
                failures.append("Material builder: child output connections are incorrect")
            if surface.outputDataTypes() != ("surface",):
                failures.append(
                    "Material builder: DwaBaseMaterial output is {}".format(
                        surface.outputDataTypes()))
            if displacement.outputDataTypes() != ("displacement",):
                failures.append(
                    "Material builder: NormalDisplacement output is {}".format(
                        displacement.outputDataTypes()))
        problem = _node_problems(builder)
        if problem:
            failures.append("Material builder: {}".format(problem))
    finally:
        builder.destroy()


def validate(output_dir):
    failures = []
    material_network = hou.node("/mat")
    hda_paths = sorted(glob.glob(os.path.join(output_dir, "otls", "Vop::DW_MOONRAY*.hda")))
    validated = 0
    for hda_path in hda_paths:
        shader_name = os.path.basename(hda_path)

        hou.hda.installFile(hda_path)
        definition = hou.hda.definitionsInFile(hda_path)[0]
        definition.setIsPreferred(True)
        try:
            expected_name, expected_label, expected_type = _output_declaration(definition)
        except ValueError as error:
            failures.append("{}: {}".format(shader_name, error))
            continue

        node = material_network.createNode(definition.nodeTypeName())
        try:
            actual = (node.outputNames(), node.outputLabels(), node.outputDataTypes())
            expected = ((expected_name,), (expected_label,), (expected_type,))
            if actual != expected:
                failures.append(
                    "{}: expected {}, got {}".format(shader_name, expected, actual)
                )
            problem = _node_problems(node)
            if problem:
                failures.append("{}: {}".format(shader_name, problem))
            validated += 1
        finally:
            node.destroy()

    if not validated:
        failures.append("No MoonRay VOP HDAs with output declarations were found")
    _validate_imagemap_connection(material_network, failures)
    _validate_material_builder(material_network, failures)

    if failures:
        raise RuntimeError("\n".join(failures))
    print("Validated {} MoonRay VOP output connectors".format(validated))
    print("Validated ImageMap -> DwaBaseMaterial.albedo connection")
    print("Validated MoonRay material builder outputs")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "output_dir", help="Generated Houdini output directory containing otls/"
    )
    args = parser.parse_args()
    validate(os.path.abspath(args.output_dir))


if __name__ == "__main__":
    main()

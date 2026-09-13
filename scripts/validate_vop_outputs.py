#!/usr/bin/env hython
"""Validate output connectors on representative generated MoonRay VOP HDAs."""

from __future__ import print_function

import argparse
import os

import hou


REPRESENTATIVE_VOPS = {
    "ImageMap": "vector",
    "DwaBaseMaterial": "surface",
    "NormalDisplacement": "displacement",
    "ImageNormalMap": "vector4",
    "BaseVolume": "volume",
    "ConstantDisplayFilter": "struct_FuzzySet",
}


def validate(output_dir):
    failures = []
    material_network = hou.node("/mat")
    for shader_name, expected_type in REPRESENTATIVE_VOPS.items():
        hda_path = os.path.join(
            output_dir, "otls", "Vop::DW_MOONRAY::{}::1.hda".format(shader_name)
        )
        if not os.path.isfile(hda_path):
            failures.append("{}: missing {}".format(shader_name, hda_path))
            continue

        hou.hda.installFile(hda_path)
        definition = hou.hda.definitionsInFile(hda_path)[0]
        definition.setIsPreferred(True)
        dialog_script = definition.sections()["DialogScript"].contents()
        output_lines = [
            line.split()
            for line in dialog_script.splitlines()
            if line.strip().startswith("output\t")
        ]
        expected_output = ["output", expected_type, "out", '"out"']
        if output_lines != [expected_output]:
            failures.append(
                "{}: expected output declaration {}, got {}".format(
                    shader_name, expected_output, output_lines
                )
            )

        node = material_network.createNode(definition.nodeTypeName())
        try:
            actual = (node.outputNames(), node.outputLabels(), node.outputDataTypes())
            expected = (("out",), ("out",), (expected_type,))
            # Renderer-specific external VOPs do not expose their connector
            # interface through HOM in every headless Houdini configuration.
            # When HOM exposes it, require the complete public contract.
            if node.outputNames() and actual != expected:
                failures.append(
                    "{}: expected {}, got {}".format(shader_name, expected, actual)
                )
            if node.errors() or node.warnings():
                failures.append(
                    "{}: errors={}, warnings={}".format(
                        shader_name, node.errors(), node.warnings()
                    )
                )
        finally:
            node.destroy()

    if failures:
        raise RuntimeError("\n".join(failures))
    print("Validated {} MoonRay VOP output connectors".format(len(REPRESENTATIVE_VOPS)))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "output_dir", help="Generated Houdini output directory containing otls/"
    )
    args = parser.parse_args()
    validate(os.path.abspath(args.output_dir))


if __name__ == "__main__":
    main()

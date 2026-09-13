# Copyright 2026 DreamWorks Animation LLC
# SPDX-License-Identifier: Apache-2.0
"""Houdini 22 dynamic menus backed by the active process OCIO config."""


def source_color_space_menu():
    """Return token/label pairs for MoonRay texture source color spaces."""
    items = ["auto", "Auto (OCIO File Rules)", "raw", "Raw / Data"]
    try:
        import PyOpenColorIO as ocio

        config = ocio.GetCurrentConfig()
        seen = {"auto", "raw", "data"}

        # Roles are valid OCIO source identifiers and are useful when a studio
        # config changes the concrete space behind a stable semantic name.
        for role in config.getRoleNames():
            role = str(role)
            if role not in seen:
                items.extend((role, "Role: " + role))
                seen.add(role)

        for name in config.getColorSpaceNames():
            name = str(name)
            if name not in seen:
                items.extend((name, name))
                seen.add(name)
    except Exception:
        # Keep the node usable when OCIO is unset or malformed.  Runtime
        # diagnostics from MoonRay provide the full fallback reason.
        pass
    return items

# Tool for filtering your current selection

import maya.cmds as cmds

def filter_selection_ui():
    window_name = "filterSelectionUI_v3"
    if cmds.window(window_name, exists=True):
        cmds.deleteUI(window_name)

    # Make the window sizeable/resizable
    cmds.window(window_name, title="Filter Selection Tool", widthHeight=(420, 460), sizeable=True)

    # Main column that will expand with the window
    cmds.columnLayout(adjustableColumn=True, rowSpacing=6, columnAlign="center")

    # Mode: Keep or Drop
    cmds.rowLayout(numberOfColumns=2, adjustableColumn=2, columnAttach=[(1, "left", 6), (2, "both", 6)])
    cmds.text(label="Mode:", align="left")
    mode_radio = cmds.radioButtonGrp(numberOfRadioButtons=2, labelArray2=["Keep", "Drop"], select=1)
    cmds.setParent("..")

    cmds.separator(height=8, style="in")
    cmds.text(label="Select Object Types to (Keep / Drop):", align="center")
    cmds.separator(height=4, style="none")

    # Filter UI mapping
    filter_options = {
        "Joints": ["joint"],
        "Curves": ["nurbsCurve"],
        "Geometry": ["mesh", "nurbsSurface", "subdiv"],
        "Groups (Transforms only)": ["__GROUP__"],
        "Locators": ["locator"],
        "Lights": ["light"],   # shape type; gather_matches handles exact matching
        "Cameras": ["camera"]
    }

    # Put the checkbox list inside a scrollLayout so it behaves well when resizing
    scroll_name = cmds.scrollLayout(horizontalScrollBarThickness=0, childResizable=True, height=220)
    cmds.columnLayout(adjustableColumn=True, rowSpacing=4, columnAlign="left")
    checkboxes = {}
    for label in filter_options.keys():
        checkboxes[label] = cmds.checkBox(label=label, value=False, align="left", width=380)
    cmds.setParent("..")
    cmds.setParent("..")

    cmds.separator(height=8, style="in")

    # ---------- Matching logic ----------
    def gather_matches(selection, active_types, include_groups):
        matches = set()
        types_set = set(active_types)

        for item in selection:
            try:
                node_type = cmds.nodeType(item)
            except:
                continue

            # direct joint match
            if node_type == "joint" and "joint" in types_set:
                matches.add(item)
                continue

            # if a transform, check its shapes for desired types
            if node_type == "transform":
                shapes = cmds.listRelatives(item, shapes=True, fullPath=True) or []
                for s in shapes:
                    stype = cmds.nodeType(s)
                    if stype in types_set:
                        matches.add(item)
                        break
                continue

            # if the selected item itself is a shape (mesh, nurbsCurve, etc.)
            if node_type in types_set:
                parent = cmds.listRelatives(item, parent=True, fullPath=True) or []
                if parent:
                    matches.add(parent[0])
                else:
                    matches.add(item)
                continue

        # Groups: exact transforms with no shapes and without joint/constraint descendants
        if include_groups:
            for item in selection:
                if cmds.nodeType(item) != "transform":
                    continue
                shapes = cmds.listRelatives(item, shapes=True, fullPath=True) or []
                if shapes:
                    continue
                descendants = cmds.listRelatives(item, ad=True, fullPath=True) or []
                bad = False
                for d in descendants:
                    try:
                        dt = cmds.nodeType(d)
                    except:
                        dt = ""
                    # filter joints and constraint-like nodes
                    if dt == "joint" or dt.lower().endswith("constraint"):
                        bad = True
                        break
                # defensive: ensure the transform itself isn't another special node
                if cmds.nodeType(item) != "transform":
                    bad = True
                if not bad:
                    matches.add(item)

        return matches

    # ---------- Button callbacks ----------
    def on_select_pressed(*args):
        sel = cmds.ls(sl=True, long=True) or []
        if not sel:
            cmds.warning("Nothing selected!")
            return

        mode_index = cmds.radioButtonGrp(mode_radio, query=True, select=True)
        mode = "keep" if mode_index == 1 else "drop"

        active_types = []
        include_groups = False
        for label, types in filter_options.items():
            if not cmds.checkBox(checkboxes[label], query=True, value=True):
                continue
            if "__GROUP__" in types:
                include_groups = True
            else:
                active_types.extend(types)

        if not active_types and not include_groups:
            cmds.warning("No object types selected in the UI.")
            return

        matched = gather_matches(sel, active_types, include_groups)

        if mode == "keep":
            if matched:
                # select matched items (order isn't preserved)
                cmds.select(list(matched), r=True)
                cmds.inViewMessage(amg=f"<hl>Keeping {len(matched)} objects</hl>", pos="topCenter", fade=True)
            else:
                cmds.select(clear=True)
                cmds.warning("No matching objects found in selection.")
        else:  # drop mode
            current_sel = set(sel)
            new_sel = list(current_sel - matched)
            if new_sel:
                cmds.select(new_sel, r=True)
                cmds.inViewMessage(amg=f"<hl>Dropped {len(current_sel & matched)} objects — {len(new_sel)} remain</hl>", pos="topCenter", fade=True)
            else:
                cmds.select(clear=True)
                cmds.inViewMessage(amg=f"<hl>Dropped all matching objects (selection cleared)</hl>", pos="topCenter", fade=True)

    def on_select_hierarchy(*args):
        sel = cmds.ls(sl=True, long=True) or []
        if not sel:
            cmds.warning("Nothing selected!")
            return
        all_descendants = cmds.listRelatives(sel, ad=True, fullPath=True) or []
        if all_descendants:
            cmds.select(sel + all_descendants, r=True)
            cmds.inViewMessage(amg=f"<hl>Selected hierarchy ({len(all_descendants)} descendants)</hl>", pos="topCenter", fade=True)
        else:
            cmds.inViewMessage(amg="<hl>No descendants found</hl>", pos="topCenter", fade=True)

    # Buttons: placed in a row that will expand with the window
    cmds.rowLayout(numberOfColumns=3, columnAlign=[(1, "center"), (2, "center"), (3, "center")],
                   adjustableColumn=2, columnAttach=[(1, "both", 6), (2, "both", 6), (3, "both", 6)])
    cmds.button(label="Filter Selection", height=34, command=on_select_pressed, bgc=(0.28, 0.52, 0.28))
    cmds.button(label="Select Hierarchy", height=34, command=on_select_hierarchy, bgc=(0.28, 0.36, 0.64))
    cmds.button(label="Close", height=34, command=lambda *_: cmds.deleteUI(window_name), bgc=(0.55, 0.32, 0.32))
    cmds.setParent("..")

    cmds.showWindow(window_name)

# Run the UI
filter_selection_ui()
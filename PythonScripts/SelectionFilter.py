# Tool for filtering your current selection, now with reparenting capabilities
# Filter Selection Tool v6.4_fix2 — layout flag error fixed (removed invalid columnWidth7)


import re
import maya.cmds as cmds

def filter_selection_ui_v6_4_fix2():
    win = "filterSelectionUI_v6_4_fix2"
    if cmds.window(win, exists=True):
        cmds.deleteUI(win)

    cmds.window(win, title="Filter Selection Tool (v6.4_fix2)", widthHeight=(820, 980), sizeable=True)
    main_col = cmds.columnLayout(adjustableColumn=True, rowSpacing=8, columnAlign="center")

    # -----------------------
    # OptionVar keys (persist UI)
    # -----------------------
    OPT_PREFIX = "fs_v6_prefix"
    OPT_SUFFIX = "fs_v6_suffix"
    OPT_ORDER = "fs_v6_order"
    OPT_NUMERIC_SORT = "fs_v6_numeric_sort"
    OPT_AUTO_SCAN = "fs_v6_auto_scan_chains"

    def opt_get(key, default):
        try:
            if cmds.optionVar(exists=key):
                return cmds.optionVar(q=key)
        except Exception:
            pass
        return default

    def opt_set(key, value):
        try:
            if isinstance(value, bool):
                cmds.optionVar(iv=(key, int(value)))
            elif isinstance(value, int):
                cmds.optionVar(iv=(key, value))
            else:
                cmds.optionVar(sv=(key, str(value)))
        except Exception:
            pass

    # -----------------------
    # Utilities
    # -----------------------
    def short_name(node):
        return node.split("|")[-1] if node else node

    def safe_node_type(node):
        try:
            return cmds.nodeType(node)
        except Exception:
            return ""

    def ordered_unique(seq):
        seen = set()
        out = []
        for x in seq:
            if x not in seen:
                out.append(x)
                seen.add(x)
        return out

    def collect_selected():
        return cmds.ls(sl=True, long=True) or []

    # -----------------------
    # Type / Name / Nth sections (kept similar to v6.3)
    # -----------------------
    # Type filter
    cmds.frameLayout(label="Object Type Filter", collapsable=False, marginWidth=6)
    cmds.columnLayout(adjustableColumn=True, rowSpacing=4)
    type_mode_radio = cmds.radioButtonGrp(numberOfRadioButtons=2, labelArray2=["Keep","Drop"], select=1)
    filter_options = {
        "Joints": ["joint"],
        "Curves": ["nurbsCurve"],
        "Geometry": ["mesh", "nurbsSurface", "subdiv"],
        "Groups (Transforms only)": ["__GROUP__"],
        "Locators": ["locator"],
        "Lights": ["light"],
        "Cameras": ["camera"]
    }
    type_checkboxes = {}
    for label in filter_options:
        type_checkboxes[label] = cmds.checkBox(label=label, value=False)
    cmds.button(label="Apply Type Filter (section)", height=34, bgc=(0.28, 0.52, 0.28),
                command=lambda *_: apply_type_filter(type_mode_radio, filter_options, type_checkboxes))
    cmds.setParent(".."); cmds.setParent("..")

    # Name filter
    cmds.frameLayout(label="Name Filter", collapsable=False, marginWidth=6)
    cmds.columnLayout(adjustableColumn=True, rowSpacing=4)
    name_mode_radio = cmds.radioButtonGrp(numberOfRadioButtons=2, labelArray2=["Keep","Drop"], select=1)
    cmds.rowLayout(numberOfColumns=2, adjustableColumn=2)
    cmds.text(label="Name contains:")
    name_field = cmds.textField()
    cmds.setParent("..")
    cmds.rowLayout(numberOfColumns=3)
    case_cb = cmds.checkBox(label="Case sensitive", value=False)
    fullpath_cb = cmds.checkBox(label="Match full path", value=False)
    cmds.setParent("..")
    cmds.button(label="Apply Name Filter (section)", height=34, bgc=(0.35, 0.45, 0.7),
                command=lambda *_: apply_name_filter(name_mode_radio, name_field, case_cb, fullpath_cb))
    cmds.setParent(".."); cmds.setParent("..")

    # Nth
    cmds.frameLayout(label="Nth Selection", collapsable=False, marginWidth=6)
    cmds.columnLayout(adjustableColumn=True, rowSpacing=4)
    nth_mode_radio = cmds.radioButtonGrp(numberOfRadioButtons=2, labelArray2=["Keep","Drop"], select=1)
    cmds.rowLayout(numberOfColumns=4, columnWidth4=[100,80,120,80])
    cmds.text(label="Step (N):")
    nth_step_field = cmds.intField(value=2, minValue=1)
    cmds.text(label="Offset (1-based):")
    nth_offset_field = cmds.intField(value=1, minValue=1)
    cmds.setParent("..")
    cmds.button(label="Apply Nth Filter (section)", height=34, bgc=(0.45, 0.6, 0.35),
                command=lambda *_: apply_nth_filter(nth_mode_radio, nth_step_field, nth_offset_field))
    cmds.setParent(".."); cmds.setParent("..")

    # -----------------------
    # Reparenting / Grouping section (with updated numbering UI)
    # -----------------------
    cmds.frameLayout(label="Reparenting / Grouping", collapsable=False, marginWidth=6)
    cmds.columnLayout(adjustableColumn=True, rowSpacing=6)

    # Method selector
    cmds.text(label="Method:")
    method_menu = cmds.optionMenu()
    cmds.menuItem(label="Name-based (parent string / child string)")
    cmds.menuItem(label="Numbering-based (prefix, number, suffix)")

    cmds.separator(h=6)

    # Name-based minimal inputs (kept)
    cmds.text(label="Name-based options (unchanged):", align="left")
    cmds.rowLayout(numberOfColumns=4, columnWidth4=[90,200,90,200])
    cmds.text(label="Parent string:")
    parent_string_field = cmds.textField(text="")
    cmds.text(label="Parent match mode:")
    parent_mode_menu = cmds.optionMenu()
    cmds.menuItem(label="suffix"); cmds.menuItem(label="prefix"); cmds.menuItem(label="contains")
    cmds.setParent("..")
    cmds.rowLayout(numberOfColumns=4, columnWidth4=[90,200,90,200])
    cmds.text(label="Child string:")
    child_string_field = cmds.textField(text="")
    cmds.text(label="Child match mode:")
    child_mode_menu = cmds.optionMenu()
    cmds.menuItem(label="suffix"); cmds.menuItem(label="prefix"); cmds.menuItem(label="contains")
    cmds.setParent("..")

    cmds.separator(h=8)

    # Numbering-based UI with saved prefs
    saved_prefix = opt_get(OPT_PREFIX, "")
    saved_suffix = opt_get(OPT_SUFFIX, "")
    saved_order = opt_get(OPT_ORDER, "increasing")
    saved_numeric_sort = bool(int(opt_get(OPT_NUMERIC_SORT, 1)))
    saved_auto_scan = bool(int(opt_get(OPT_AUTO_SCAN, 1)))

    cmds.text(label="Numbering-based options (prefix + number + suffix):", align="left")
    cmds.rowLayout(numberOfColumns=2, columnWidth2=[200,560])
    cmds.text(label="Prefix (text before number):")
    prefix_field = cmds.textField(text=saved_prefix, width=560)
    cmds.setParent("..")
    cmds.rowLayout(numberOfColumns=2, columnWidth2=[200,560])
    cmds.text(label="Suffix (text after number):")
    suffix_field = cmds.textField(text=saved_suffix, width=560)
    cmds.setParent("..")

    # FIX: do not pass an invalid columnWidth7 flag — use columnAttach to space columns instead
    cmds.rowLayout(numberOfColumns=7, columnAttach=[(1, "left", 6), (2, "both", 6), (3, "both", 6),
                                                   (4, "both", 6), (5, "both", 6), (6, "both", 6), (7, "both", 6)])
    cmds.text(label="Ordering:")
    order_option = cmds.optionMenu()
    cmds.menuItem(label="increasing"); cmds.menuItem(label="decreasing")
    try:
        cmds.optionMenu(order_option, edit=True, value=saved_order)
    except Exception:
        pass
    numeric_sort_cb = cmds.checkBox(label="Sort numbers as integers (01→1)", value=saved_numeric_sort)
    auto_scan_cb = cmds.checkBox(label="Auto-scan distinct bases → one chain per base", value=saved_auto_scan)
    cmds.text(label="Apply chains:")
    apply_all_checkbox = cmds.checkBox(label="Apply ALL chains", value=True)
    chain_index_field = cmds.intField(value=1, minValue=1)
    cmds.setParent("..")

    cmds.rowLayout(numberOfColumns=3, columnWidth3=[280,280,240])
    create_missing_parents_cb = cmds.checkBox(label="Create missing parent transforms (for group root)", value=True)
    reparent_root_field = cmds.textField(text="", placeholderText="Optional parent for created groups (full path)", width=280)
    prevent_cycles_checkbox = cmds.checkBox(label="Prevent cycles (recommended)", value=True)
    cmds.setParent("..")

    cmds.separator(h=6)
    cmds.rowLayout(numberOfColumns=3, columnWidth3=[260,260,260])
    cmds.button(label="Preview Reparenting", height=36, bgc=(0.3,0.5,0.7),
                command=lambda *_: preview_reparenting())
    cmds.button(label="Apply Reparenting", height=36, bgc=(0.28,0.52,0.28),
                command=lambda *_: apply_reparenting())
    cmds.button(label="Undo (quick)", height=36, bgc=(0.8,0.4,0.4), command=lambda *_: cmds.undo())
    cmds.setParent("..")

    cmds.setParent("..")  # end frameLayout
    cmds.setParent("..")  # end main column

    # -----------------------
    # Implementation helpers
    # -----------------------
    def apply_type_filter(mode_radio, filter_options, checkboxes):
        sel = collect_selected()
        if not sel:
            cmds.warning("Nothing selected."); return
        mode_index = cmds.radioButtonGrp(mode_radio, query=True, select=True)
        mode_keep = (mode_index == 1)
        active_types = []
        include_groups = False
        for label, types in filter_options.items():
            if cmds.checkBox(checkboxes[label], q=True, value=True):
                if "__GROUP__" in types:
                    include_groups = True
                else:
                    active_types.extend(types)
        if not active_types and not include_groups:
            cmds.warning("No object types enabled."); return
        result = []
        for item in sel:
            nt = safe_node_type(item)
            if nt == "joint" and "joint" in active_types:
                result.append(item); continue
            if nt == "transform":
                shapes = cmds.listRelatives(item, shapes=True, fullPath=True) or []
                matched = False
                for s in shapes:
                    if safe_node_type(s) in active_types:
                        result.append(item); matched = True; break
                if matched: continue
            if nt in active_types:
                parents = cmds.listRelatives(item, parent=True, fullPath=True) or []
                if parents: result.extend(parents)
                else: result.append(item)
        if include_groups:
            for item in sel:
                if safe_node_type(item) != "transform": continue
                shapes = cmds.listRelatives(item, shapes=True) or []
                if shapes: continue
                descendants = cmds.listRelatives(item, ad=True, fullPath=True) or []
                bad = any(safe_node_type(d) == "joint" or safe_node_type(d).lower().endswith("constraint") for d in descendants)
                if not bad: result.append(item)
        result = ordered_unique(result)
        if mode_keep:
            cmds.select(result, r=True); cmds.inViewMessage(amg=f"<hl>Type filter (keep) → {len(result)} objects</hl>", pos="topCenter", fade=True)
        else:
            to_remove = set(result)
            new_sel = [x for x in sel if x not in to_remove]
            if new_sel:
                cmds.select(new_sel, r=True); cmds.inViewMessage(amg=f"<hl>Type filter (drop) → removed {len(sel)-len(new_sel)} objects</hl>", pos="topCenter", fade=True)
            else:
                cmds.select(clear=True); cmds.inViewMessage(amg=f"<hl>Type filter (drop) → removed all</hl>", pos="topCenter", fade=True)

    def apply_name_filter(mode_radio, name_field, case_cb, fullpath_cb):
        sel = collect_selected()
        if not sel:
            cmds.warning("Nothing selected."); return
        mode_index = cmds.radioButtonGrp(mode_radio, query=True, select=True)
        mode_keep = (mode_index == 1)
        text = cmds.textField(name_field, q=True, text=True)
        if not text:
            cmds.warning("Name filter is empty."); return
        case = cmds.checkBox(case_cb, q=True, value=True)
        full = cmds.checkBox(fullpath_cb, q=True, value=True)
        needle = text if case else text.lower()
        result = []
        for item in sel:
            target = item if full else short_name(item)
            target = target if case else target.lower()
            if needle in target:
                result.append(item)
        result = ordered_unique(result)
        if mode_keep:
            cmds.select(result, r=True); cmds.inViewMessage(amg=f"<hl>Name filter (keep) → {len(result)} objects</hl>", pos="topCenter", fade=True)
        else:
            to_remove = set(result)
            new_sel = [x for x in sel if x not in to_remove]
            if new_sel:
                cmds.select(new_sel, r=True); cmds.inViewMessage(amg=f"<hl>Name filter (drop) → removed {len(sel)-len(new_sel)} objects</hl>", pos="topCenter", fade=True)
            else:
                cmds.select(clear=True); cmds.inViewMessage(amg=f"<hl>Name filter (drop) → removed all</hl>", pos="topCenter", fade=True)

    def apply_nth_filter(nth_mode_radio, nth_step_field, nth_offset_field):
        sel = collect_selected()
        if not sel:
            cmds.warning("Nothing selected."); return
        mode_index = cmds.radioButtonGrp(nth_mode_radio, query=True, select=True)
        mode_keep = (mode_index == 1)
        step = cmds.intField(nth_step_field, q=True, value=True)
        offset = cmds.intField(nth_offset_field, q=True, value=True)
        offset = max(1, offset)
        picked = [sel[i] for i in range(offset - 1, len(sel), step)]
        picked = ordered_unique(picked)
        if mode_keep:
            cmds.select(picked, r=True); cmds.inViewMessage(amg=f"<hl>Nth (keep) → {len(picked)} objects</hl>", pos="topCenter", fade=True)
        else:
            to_remove = set(picked)
            new_sel = [x for x in sel if x not in to_remove]
            if new_sel:
                cmds.select(new_sel, r=True); cmds.inViewMessage(amg=f"<hl>Nth (drop) → removed {len(sel)-len(new_sel)} objects</hl>", pos="topCenter", fade=True)
            else:
                cmds.select(clear=True); cmds.inViewMessage(amg=f"<hl>Nth (drop) → removed all</hl>", pos="topCenter", fade=True)

    # -----------------------
    # Reparenting logic (name-based unchanged, numbering updated + fix)
    # -----------------------
    def remove_pattern_once(name, pattern, mode="contains", case_sensitive=False):
        if not pattern:
            return None
        if not case_sensitive:
            nl = name.lower(); pl = pattern.lower()
        else:
            nl = name; pl = pattern
        if mode == "prefix":
            if nl.startswith(pl):
                return name[len(pattern):]
            return None
        if mode == "suffix":
            if nl.endswith(pl):
                return name[:len(name)-len(pattern)]
            return None
        idx = nl.find(pl)
        if idx == -1:
            return None
        return name[:idx] + name[idx+len(pattern):]

    def plan_name_based_reparent(sel):
        parent_pat = cmds.textField(parent_string_field, q=True, text=True) or ""
        child_pat = cmds.textField(child_string_field, q=True, text=True) or ""
        parent_mode = cmds.optionMenu(parent_mode_menu, q=True, value=True)
        child_mode = cmds.optionMenu(child_mode_menu, q=True, value=True)
        if not parent_pat or not child_pat:
            return {}, []
        parents_by_base = {}
        children_by_base = {}
        all_children = set()
        for item in sel:
            sname = short_name(item)
            base_p = remove_pattern_once(sname, parent_pat, mode=parent_mode, case_sensitive=False)
            if base_p is not None:
                parents_by_base.setdefault(base_p, []).append(item)
            base_c = remove_pattern_once(sname, child_pat, mode=child_mode, case_sensitive=False)
            if base_c is not None:
                children_by_base.setdefault(base_c, []).append(item)
                all_children.add(item)
        plan = {}; unassigned = []
        for base_key in children_by_base.keys():
            if base_key in parents_by_base:
                parent_candidates = parents_by_base[base_key]
                chosen_parent = parent_candidates[0]
                kids = children_by_base[base_key]
                kids_filtered = [k for k in kids if k != chosen_parent]
                if kids_filtered:
                    plan[chosen_parent] = kids_filtered
        for c in all_children:
            matched = any(c in kids for kids in plan.values())
            if not matched:
                unassigned.append(c)
        return plan, unassigned

    def plan_numbering_reparent(sel):
        prefix = cmds.textField(prefix_field, q=True, text=True) or ""
        suffix = cmds.textField(suffix_field, q=True, text=True) or ""
        ordering = cmds.optionMenu(order_option, q=True, value=True)
        numeric_sort_as_int = bool(cmds.checkBox(numeric_sort_cb, q=True, value=True))
        auto_scan = bool(cmds.checkBox(auto_scan_cb, q=True, value=True))

        # persist prefs
        opt_set(OPT_PREFIX, prefix)
        opt_set(OPT_SUFFIX, suffix)
        opt_set(OPT_ORDER, ordering)
        opt_set(OPT_NUMERIC_SORT, int(numeric_sort_as_int))
        opt_set(OPT_AUTO_SCAN, int(auto_scan))

        pat = r"^" + re.escape(prefix) + r"(\d+)" + re.escape(suffix) + r"$"
        regex = re.compile(pat)

        matched = []   # list of tuples (base_key, num_key, node, num_text)
        unmatched = []

        for item in sel:
            sname = short_name(item)
            m = regex.match(sname)
            if m:
                num_text = m.group(1)
                if numeric_sort_as_int:
                    try:
                        num_key = int(num_text)
                    except:
                        num_key = num_text
                else:
                    num_key = num_text
                base_key = sname[:m.start(1)] + sname[m.end(1):]
                matched.append((base_key, num_key, item, num_text))
            else:
                unmatched.append(item)

        if not matched:
            return [], unmatched

        groups = {}
        if auto_scan:
            for base, num_key, node, num_text in matched:
                groups.setdefault(base, []).append((num_key, node, num_text))
        else:
            key = "_ALL_"
            groups[key] = [(num_key, node, num_text) for (_, num_key, node, num_text) in matched]

        chains = []
        reverse = (ordering == "decreasing")
        for base, entries in groups.items():
            try:
                entries.sort(key=lambda t: t[0], reverse=reverse)
            except Exception:
                entries.sort(key=lambda t: str(t[0]), reverse=reverse)
            ordered_nodes = [t[1] for t in entries]
            ordered_info = [(t[1], t[2], t[0]) for t in entries]  # (node, num_text, num_key)
            chains.append((ordered_nodes, ordered_info, base))  # keep info for preview
        return chains, unmatched

    # Resolve a node to its current transform path just before parenting.
    def resolve_transform_current(node):
        if cmds.objExists(node):
            nt = safe_node_type(node)
            if nt in ("transform", "joint"):
                return node
            parents = cmds.listRelatives(node, parent=True, fullPath=True) or []
            return parents[0] if parents else node
        s = short_name(node)
        candidates = cmds.ls(s, long=True) or []
        if not candidates:
            return node
        candidates_sorted = sorted(candidates, key=lambda c: len(c))
        return candidates_sorted[0]

    def preview_reparenting():
        sel = collect_selected()
        if not sel:
            cmds.warning("Nothing selected for reparenting."); return
        method = cmds.optionMenu(method_menu, q=True, value=True)
        preview_lines = []
        if "Name-based" in method:
            plan, unassigned = plan_name_based_reparent(sel)
            if not plan and not unassigned:
                cmds.confirmDialog(title="Preview Reparenting", message="No parent/child pairs found with current name filters.", button=["OK"]); return
            for p, kids in plan.items():
                preview_lines.append(f"Parent: {short_name(p)} -> {len(kids)} child(ren)")
                for k in kids[:200]:
                    preview_lines.append("  - " + short_name(k))
            if unassigned:
                preview_lines.append(""); preview_lines.append("Unassigned children (no matching parent):")
                for u in unassigned[:200]:
                    preview_lines.append("  - " + short_name(u))
        else:
            chains, unmatched = plan_numbering_reparent(sel)
            if not chains:
                cmds.confirmDialog(title="Preview Reparenting", message="No numeric matches found for given prefix/suffix.", button=["OK"]); return
            for i, (chain_nodes, chain_info, base) in enumerate(chains):
                preview_lines.append(f"Planned chain #{i+1} (top -> ... -> bottom) base='{base}':")
                for node, num_text, num_key in chain_info:
                    preview_lines.append(f"  - {short_name(node)}   (token='{num_text}', parsed={num_key})")
            if unmatched:
                preview_lines.append(""); preview_lines.append("Unmatched (did not fit prefix+number+suffix):")
                for u in unmatched[:200]:
                    preview_lines.append("  - " + short_name(u))
        message = "\n".join(preview_lines[:4000]) or "No planned changes."
        cmds.confirmDialog(title="Preview Reparenting", message=message, button=["OK"], defaultButton="OK", dismissString="OK")

    def apply_reparenting():
        sel = collect_selected()
        if not sel:
            cmds.warning("Nothing selected for reparenting."); return
        method = cmds.optionMenu(method_menu, q=True, value=True)
        create_missing = cmds.checkBox(create_missing_parents_cb, q=True, value=True)
        reparent_root = cmds.textField(reparent_root_field, q=True, text=True) or ""
        prevent_cycles = bool(cmds.checkBox(prevent_cycles_checkbox, q=True, value=True))
        apply_all = bool(cmds.checkBox(apply_all_checkbox, q=True, value=True))
        chain_index = cmds.intField(chain_index_field, q=True, value=True)

        if "Name-based" in method:
            plan, unassigned = plan_name_based_reparent(sel)
            if not plan and not unassigned:
                cmds.warning("No reparent actions planned."); return
            applied = 0
            for p, kids in plan.items():
                parent_node = p
                if not cmds.objExists(parent_node):
                    continue
                for kid in kids:
                    if not cmds.objExists(kid):
                        continue
                    if prevent_cycles:
                        if parent_node == kid: continue
                        descendants = cmds.listRelatives(kid, ad=True, fullPath=True) or []
                        if parent_node in descendants: continue
                    try:
                        cmds.parent(kid, parent_node)
                        applied += 1
                    except Exception as e:
                        cmds.warning(f"Failed to parent {kid} to {parent_node}: {e}")
            if unassigned:
                cmds.inViewMessage(amg=f"<hl>Reparenting done. {applied} moved. {len(unassigned)} children unassigned.</hl>", pos="topCenter", fade=True)
            else:
                cmds.inViewMessage(amg=f"<hl>Reparenting done. {applied} moved.</hl>", pos="topCenter", fade=True)
        else:
            chains, unmatched = plan_numbering_reparent(sel)
            if not chains:
                cmds.warning("No numeric matches found for given prefix/suffix."); return

            chosen_chains = []
            if apply_all:
                chosen_chains = chains
            else:
                if chain_index < 1 or chain_index > len(chains):
                    cmds.warning(f"Invalid chain index: {chain_index}. There are {len(chains)} chains. Set 'Apply ALL chains' or choose a valid index.")
                    return
                chosen_chains = [chains[chain_index - 1]]

            applied = 0
            for chain_nodes, chain_info, base in chosen_chains:
                for i in range(len(chain_nodes) - 1, 0, -1):
                    child_node_orig = chain_nodes[i]
                    parent_node_orig = chain_nodes[i - 1]
                    parent_r = resolve_transform_current(parent_node_orig)
                    child_r = resolve_transform_current(child_node_orig)
                    if not cmds.objExists(parent_r) or not cmds.objExists(child_r):
                        continue
                    if prevent_cycles:
                        if parent_r == child_r:
                            continue
                        descendants = cmds.listRelatives(child_r, ad=True, fullPath=True) or []
                        if parent_r in descendants:
                            continue
                    try:
                        cmds.parent(child_r, parent_r)
                        applied += 1
                    except Exception as e:
                        cmds.warning(f"Failed to parent {child_r} under {parent_r}: {e}")

            if unmatched:
                cmds.inViewMessage(amg=f"<hl>Numbering reparent done. {applied} moved. {len(unmatched)} unmatched.</hl>", pos="topCenter", fade=True)
            else:
                cmds.inViewMessage(amg=f"<hl>Numbering reparent done. {applied} moved.</hl>", pos="topCenter", fade=True)

    # -----------------------
    # Bottom utilities
    # -----------------------
    cmds.separator(h=8)
    cmds.rowLayout(numberOfColumns=3, columnWidth3=[280,280,280])
    def select_hierarchy(*_):
        sel = collect_selected()
        if not sel:
            cmds.warning("Nothing selected."); return
        descendants = cmds.listRelatives(sel, ad=True, fullPath=True) or []
        cmds.select(sel + descendants, r=True)

    cmds.button(label="Select Hierarchy", height=34, bgc=(0.28, 0.36, 0.64), command=select_hierarchy)
    cmds.button(label="Reset UI (close & reopen)", height=34, bgc=(0.7,0.45,0.2), command=lambda *_: (cmds.deleteUI(win), filter_selection_ui_v6_4_fix2()))
    cmds.button(label="Close", height=34, bgc=(0.55,0.32,0.32), command=lambda *_: cmds.deleteUI(win))
    cmds.setParent("..")

    cmds.showWindow(win)

# Run UI
filter_selection_ui_v6_4_fix2()
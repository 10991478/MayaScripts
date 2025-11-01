# Maya Python Renaming Tool - Updated

import re
import maya.cmds as cmds

WINDOW_NAME = "simpleRenamerWindow_v2"

def safe_int(field, default=0):
    try:
        return int(cmds.intField(field, query=True, value=True))
    except Exception:
        return default

def get_selection():
    return cmds.ls(sl=True, long=False) or []

# ------------------ Core operations ------------------

def add_prefix_suffix(prefix_field, suffix_field):
    sel = get_selection()
    if not sel:
        cmds.warning("No selection.")
        return
    prefix = cmds.textField(prefix_field, q=True, text=True) or ""
    suffix = cmds.textField(suffix_field, q=True, text=True) or ""
    if prefix == "" and suffix == "":
        cmds.warning("No prefix or suffix entered.")
        return
    try:
        cmds.undoInfo(openChunk=True)
        for obj in sel:
            newname = prefix + obj + suffix
            try:
                cmds.rename(obj, newname)
            except Exception:
                cmds.warning("Couldn't rename '%s' to '%s' exactly; Maya adjusted name." % (obj, newname))
    finally:
        cmds.undoInfo(closeChunk=True)

def build_number_string(num, padding):
    if padding and padding > 0:
        return str(num).zfill(padding)
    return str(num)

def rename_with_numbering(base_field, use_number_checkbox, start_field, padding_field, placement_radio, prefix_field, suffix_field, separator_field):
    sel = get_selection()
    if not sel:
        cmds.warning("No selection.")
        return
    base = cmds.textField(base_field, q=True, text=True) or ""
    use_number = cmds.checkBox(use_number_checkbox, q=True, value=True)
    start_num = safe_int(start_field, 1)
    padding = safe_int(padding_field, 0)
    placement = cmds.radioButtonGrp(placement_radio, q=True, select=True)  # 1 or 2
    prefix = cmds.textField(prefix_field, q=True, text=True) or ""
    suffix = cmds.textField(suffix_field, q=True, text=True) or ""
    sep = cmds.textField(separator_field, q=True, text=True) or ""
    try:
        cmds.undoInfo(openChunk=True)
        idx = start_num
        for obj in sel:
            numstr = build_number_string(idx, padding) if use_number else ""
            if base == "":
                base_for_obj = obj
            else:
                base_for_obj = base
            if use_number:
                if placement == 1:
                    # number before suffix: base + sep + number then suffix
                    name_core = base_for_obj + (sep + numstr if sep else numstr)
                    newname = prefix + name_core + suffix
                else:
                    # number after suffix: base + suffix + sep + number
                    name_core = base_for_obj + suffix
                    newname = prefix + name_core + (sep + numstr if sep else numstr)
            else:
                newname = prefix + base_for_obj + suffix
            try:
                cmds.rename(obj, newname)
            except Exception:
                cmds.warning("Couldn't rename '%s' to '%s' exactly; Maya adjusted name." % (obj, newname))
            idx += 1
    finally:
        cmds.undoInfo(closeChunk=True)

def remove_substring_from_selection(remove_field):
    sel = get_selection()
    if not sel:
        cmds.warning("No selection.")
        return
    rem = cmds.textField(remove_field, q=True, text=True) or ""
    if rem == "":
        cmds.warning("No substring entered to remove.")
        return
    try:
        cmds.undoInfo(openChunk=True)
        for obj in sel:
            newname = obj.replace(rem, "")
            try:
                cmds.rename(obj, newname)
            except Exception:
                cmds.warning("Couldn't rename '%s' to '%s' exactly; Maya adjusted name." % (obj, newname))
    finally:
        cmds.undoInfo(closeChunk=True)

def remove_chars_from_selection(num_start_field, num_end_field):
    sel = get_selection()
    if not sel:
        cmds.warning("No selection.")
        return
    num_start = safe_int(num_start_field, 0)
    num_end = safe_int(num_end_field, 0)
    if num_start <= 0 and num_end <= 0:
        cmds.warning("Numbers to remove are both zero; nothing to remove.")
        return
    try:
        cmds.undoInfo(openChunk=True)
        for obj in sel:
            s = obj
            if num_start > 0:
                if num_start >= len(s):
                    s = ""
                else:
                    s = s[num_start:]
            if num_end > 0:
                if num_end >= len(s):
                    s = ""
                else:
                    s = s[:-num_end]
            try:
                cmds.rename(obj, s)
            except Exception:
                cmds.warning("Couldn't rename '%s' to '%s' exactly; Maya adjusted name." % (obj, s))
    finally:
        cmds.undoInfo(closeChunk=True)

def remove_numbers_at_ends(remove_start_checkbox, remove_end_checkbox):
    sel = get_selection()
    if not sel:
        cmds.warning("No selection.")
        return
    remove_start = cmds.checkBox(remove_start_checkbox, q=True, value=True)
    remove_end = cmds.checkBox(remove_end_checkbox, q=True, value=True)
    if not remove_start and not remove_end:
        cmds.warning("Pick at least one: remove leading or trailing numbers.")
        return
    try:
        cmds.undoInfo(openChunk=True)
        for obj in sel:
            s = obj
            if remove_start:
                s = re.sub(r'^\d+', '', s)
            if remove_end:
                s = re.sub(r'\d+$', '', s)
            try:
                cmds.rename(obj, s)
            except Exception:
                cmds.warning("Couldn't rename '%s' to '%s' exactly; Maya adjusted name." % (obj, s))
    finally:
        cmds.undoInfo(closeChunk=True)

# ------------------ Search & Replace (new section) ------------------

def search_replace_selection(search_field, replace_field, regex_checkbox, case_checkbox, whole_name_checkbox):
    sel = get_selection()
    if not sel:
        cmds.warning("No selection.")
        return
    pattern = cmds.textField(search_field, q=True, text=True) or ""
    repl = cmds.textField(replace_field, q=True, text=True) or ""
    use_regex = cmds.checkBox(regex_checkbox, q=True, value=True)
    case_sensitive = cmds.checkBox(case_checkbox, q=True, value=True)
    whole_name = cmds.checkBox(whole_name_checkbox, q=True, value=True)

    if pattern == "":
        cmds.warning("Enter a search pattern.")
        return

    flags = 0
    if not case_sensitive:
        flags |= re.IGNORECASE

    try:
        cmds.undoInfo(openChunk=True)
        for obj in sel:
            source = obj
            newname = source
            if use_regex:
                pat = pattern
                if whole_name:
                    # ensure it matches whole name
                    if not pat.startswith('^'):
                        pat = '^' + pat
                    if not pat.endswith('$'):
                        pat = pat + '$'
                try:
                    newname = re.sub(pat, repl, source, flags=flags)
                except re.error as e:
                    cmds.warning("Invalid regex pattern: %s" % e)
                    cmds.undoInfo(closeChunk=True)
                    return
            else:
                if whole_name:
                    # replace only if entire name matches (respecting case option)
                    if (case_sensitive and source == pattern) or (not case_sensitive and source.lower() == pattern.lower()):
                        newname = repl
                else:
                    if case_sensitive:
                        newname = source.replace(pattern, repl)
                    else:
                        # case-insensitive simple replace via regex escape
                        try:
                            newname = re.sub(re.escape(pattern), repl, source, flags=re.IGNORECASE)
                        except re.error as e:
                            cmds.warning("Replace failed (regex escape issue): %s" % e)
                            cmds.undoInfo(closeChunk=True)
                            return
            if newname != source:
                try:
                    cmds.rename(source, newname)
                except Exception:
                    cmds.warning("Couldn't rename '%s' to '%s' exactly; Maya adjusted name." % (source, newname))
        cmds.undoInfo(closeChunk=True)
    except Exception:
        try:
            cmds.undoInfo(closeChunk=False)
        except Exception:
            pass

def print_preview_search_replace(search_field, replace_field, regex_checkbox, case_checkbox, whole_name_checkbox):
    sel = get_selection()
    if not sel:
        print("[Preview] No selection.")
        return
    pattern = cmds.textField(search_field, q=True, text=True) or ""
    repl = cmds.textField(replace_field, q=True, text=True) or ""
    use_regex = cmds.checkBox(regex_checkbox, q=True, value=True)
    case_sensitive = cmds.checkBox(case_checkbox, q=True, value=True)
    whole_name = cmds.checkBox(whole_name_checkbox, q=True, value=True)

    print("[Preview] Search & Replace (pattern: '%s' -> '%s', regex=%s, case_sensitive=%s, whole_name=%s)" %
          (pattern, repl, use_regex, case_sensitive, whole_name))
    flags = 0
    if not case_sensitive:
        flags |= re.IGNORECASE

    for s in sel:
        newname = s
        if pattern == "":
            newname = s
        else:
            if use_regex:
                pat = pattern
                if whole_name:
                    if not pat.startswith('^'):
                        pat = '^' + pat
                    if not pat.endswith('$'):
                        pat = pat + '$'
                try:
                    newname = re.sub(pat, repl, s, flags=flags)
                except re.error as e:
                    print("[Preview] Invalid regex: %s" % e)
                    return
            else:
                if whole_name:
                    if (case_sensitive and s == pattern) or (not case_sensitive and s.lower() == pattern.lower()):
                        newname = repl
                else:
                    if case_sensitive:
                        newname = s.replace(pattern, repl)
                    else:
                        newname = re.sub(re.escape(pattern), repl, s, flags=re.IGNORECASE)
        print("  %s  ->  %s" % (s, newname))

# ------------------ Preview helpers (existing) ------------------

def print_selection_names():
    sel = get_selection()
    if not sel:
        print("[Preview] No selection.")
        return
    print("[Preview] Selection names:")
    for i, s in enumerate(sel, start=1):
        print("  %02d: %s" % (i, s))

def print_preview_add_prefix_suffix(prefix_field, suffix_field):
    sel = get_selection()
    if not sel:
        print("[Preview] No selection.")
        return
    prefix = cmds.textField(prefix_field, q=True, text=True) or ""
    suffix = cmds.textField(suffix_field, q=True, text=True) or ""
    print("[Preview] Add Prefix/Suffix:")
    for s in sel:
        print("  %s  ->  %s" % (s, prefix + s + suffix))

def print_preview_rename(base_field, use_number_checkbox, start_field, padding_field, placement_radio, prefix_field, suffix_field, separator_field):
    sel = get_selection()
    if not sel:
        print("[Preview] No selection.")
        return
    base = cmds.textField(base_field, q=True, text=True) or ""
    use_number = cmds.checkBox(use_number_checkbox, q=True, value=True)
    start_num = safe_int(start_field, 1)
    padding = safe_int(padding_field, 0)
    placement = cmds.radioButtonGrp(placement_radio, q=True, select=True)
    prefix = cmds.textField(prefix_field, q=True, text=True) or ""
    suffix = cmds.textField(suffix_field, q=True, text=True) or ""
    sep = cmds.textField(separator_field, q=True, text=True) or ""
    print("[Preview] Rename with numbering:")
    idx = start_num
    for s in sel:
        if base == "":
            base_for_obj = s
        else:
            base_for_obj = base
        if use_number:
            numstr = build_number_string(idx, padding)
            if placement == 1:
                name_core = base_for_obj + (sep + numstr if sep else numstr)
                newname = prefix + name_core + suffix
            else:
                name_core = base_for_obj + suffix
                newname = prefix + name_core + (sep + numstr if sep else numstr)
        else:
            newname = prefix + base_for_obj + suffix
        print("  %s  ->  %s" % (s, newname))
        idx += 1

def print_preview_remove_substring(remove_field):
    sel = get_selection()
    if not sel:
        print("[Preview] No selection.")
        return
    rem = cmds.textField(remove_field, q=True, text=True) or ""
    if rem == "":
        print("[Preview] No substring entered.")
        return
    print("[Preview] Remove substring '%s':" % rem)
    for s in sel:
        print("  %s  ->  %s" % (s, s.replace(rem, "")))

def print_preview_remove_chars(num_start_field, num_end_field):
    sel = get_selection()
    if not sel:
        print("[Preview] No selection.")
        return
    num_start = safe_int(num_start_field, 0)
    num_end = safe_int(num_end_field, 0)
    print("[Preview] Remove %d chars from start, %d chars from end" % (num_start, num_end))
    for s in sel:
        new = s
        if num_start > 0:
            new = new[num_start:] if num_start < len(new) else ""
        if num_end > 0:
            new = new[:-num_end] if num_end < len(new) else ""
        print("  %s  ->  %s" % (s, new))

def print_preview_remove_numbers(remove_start_checkbox, remove_end_checkbox):
    sel = get_selection()
    if not sel:
        print("[Preview] No selection.")
        return
    remove_start = cmds.checkBox(remove_start_checkbox, q=True, value=True)
    remove_end = cmds.checkBox(remove_end_checkbox, q=True, value=True)
    print("[Preview] Remove leading numbers: %s, trailing numbers: %s" % (remove_start, remove_end))
    for s in sel:
        new = s
        if remove_start:
            new = re.sub(r'^\d+', '', new)
        if remove_end:
            new = re.sub(r'\d+$', '', new)
        print("  %s  ->  %s" % (s, new))

# ------------------ UI ------------------

def create_ui():
    if cmds.window(WINDOW_NAME, exists=True):
        cmds.deleteUI(WINDOW_NAME)
    win = cmds.window(WINDOW_NAME, title="Simple Renamer", widthHeight=(520, 620), sizeable=True)
    main_col = cmds.columnLayout(adjustableColumn=True, rowSpacing=8, columnAlign="center")

    # Prefix / Suffix Frame
    f1 = cmds.frameLayout(label="Add Prefix / Suffix", collapsable=True, marginHeight=8, parent=main_col)
    c1 = cmds.columnLayout(adjustableColumn=True)
    prefix_field = cmds.textField(placeholderText="Enter prefix...", annotation="Prefix text to add to beginning")
    suffix_field = cmds.textField(placeholderText="Enter suffix...", annotation="Suffix text to add to end")
    cmds.rowLayout(numberOfColumns=3, columnWidth3=(160,160,160), adjustableColumn=2)
    cmds.button(label="Add Prefix+Suffix", c=lambda *_: add_prefix_suffix(prefix_field, suffix_field), annotation="Add prefix and/or suffix to each selected object")
    cmds.button(label="Preview (print)", c=lambda *_: print_preview_add_prefix_suffix(prefix_field, suffix_field))
    cmds.button(label="Select (reselect)", c=lambda *_: cmds.select(get_selection(), r=True))
    cmds.setParent('..')
    cmds.setParent('..')

    # Rename with number frame
    f2 = cmds.frameLayout(label="Rename / Numbering", collapsable=True, marginHeight=8, parent=main_col)
    c2 = cmds.columnLayout(adjustableColumn=True)
    base_field = cmds.textField(placeholderText="New base name (leave blank to use current names)", annotation="If blank, uses current object name as base")
    use_number_checkbox = cmds.checkBox(label="Use numbering", value=True)
    cmds.rowLayout(numberOfColumns=6, adjustableColumn=2, columnAttach=[(1,"right",0),(2,"both",5),(3,"right",0),(4,"both",5),(5,"right",0),(6,"both",5)])
    start_field = cmds.intField(value=1)
    cmds.text(label="Start #")
    padding_field = cmds.intField(value=2)
    cmds.text(label="Padding")
    separator_field = cmds.textField(placeholderText="_ or - (optional)", annotation="Text to place between name and number")
    cmds.text(label="Separator")
    cmds.setParent('..')
    # Shorter radio labels to avoid overlap
    placement_radio = cmds.radioButtonGrp(label='Number position:', labelArray2=['Before suffix','After suffix'], numberOfRadioButtons=2, select=2)
    cmds.text(label="(Before = name + number + suffix ; After = name + suffix + number)")
    cmds.rowLayout(numberOfColumns=3, columnWidth3=(160,160,160))
    prefix_field2 = cmds.textField(placeholderText="Prefix (optional)", annotation="Prefix used for this rename operation")
    suffix_field2 = cmds.textField(placeholderText="Suffix (optional)", annotation="Suffix used for this rename operation")
    cmds.setParent('..')
    cmds.rowLayout(numberOfColumns=2, columnWidth2=(260,260))
    cmds.button(label="Rename Selection", c=lambda *_: rename_with_numbering(base_field, use_number_checkbox, start_field, padding_field, placement_radio, prefix_field2, suffix_field2, separator_field), annotation="Rename selection according to fields. Numbering uses selection order.")
    cmds.button(label="Preview (print)", c=lambda *_: print_preview_rename(base_field, use_number_checkbox, start_field, padding_field, placement_radio, prefix_field2, suffix_field2, separator_field))
    cmds.setParent('..')
    cmds.setParent('..')

    # Remove frame
    f3 = cmds.frameLayout(label="Remove from Names", collapsable=True, marginHeight=8, parent=main_col)
    c3 = cmds.columnLayout(adjustableColumn=True)
    cmds.text(label="Remove substring (all occurrences):")
    remove_field = cmds.textField(placeholderText="Substring to remove")
    cmds.rowLayout(numberOfColumns=2, columnWidth2=(260,260))
    cmds.button(label="Remove substring", c=lambda *_: remove_substring_from_selection(remove_field))
    cmds.button(label="Preview (print)", c=lambda *_: print_preview_remove_substring(remove_field))
    cmds.setParent('..')

    cmds.separator(height=8)
    cmds.text(label="Remove N characters from Start/End (enter numbers):")
    num_start_field = cmds.intField(value=0)
    cmds.text(label="N chars to remove from start")
    num_end_field = cmds.intField(value=0)
    cmds.text(label="N chars to remove from end")
    cmds.rowLayout(numberOfColumns=2, columnWidth2=(260,260))
    cmds.button(label="Remove N chars", c=lambda *_: remove_chars_from_selection(num_start_field, num_end_field))
    cmds.button(label="Preview (print)", c=lambda *_: print_preview_remove_chars(num_start_field, num_end_field))
    cmds.setParent('..')

    cmds.separator(height=8)
    cmds.text(label="Remove numbers at start / end:")
    remove_start_checkbox = cmds.checkBox(label="Remove leading numbers", value=True)
    remove_end_checkbox = cmds.checkBox(label="Remove trailing numbers", value=True)
    cmds.rowLayout(numberOfColumns=2, columnWidth2=(260,260))
    cmds.button(label="Remove numbers", c=lambda *_: remove_numbers_at_ends(remove_start_checkbox, remove_end_checkbox))
    cmds.button(label="Preview (print)", c=lambda *_: print_preview_remove_numbers(remove_start_checkbox, remove_end_checkbox))
    cmds.setParent('..')
    cmds.setParent('..')

    # Search & Replace Frame (new)
    f4 = cmds.frameLayout(label="Search & Replace Names", collapsable=True, marginHeight=8, parent=main_col)
    c4 = cmds.columnLayout(adjustableColumn=True)
    cmds.text(label="Search for (enter text or regex):")
    search_field = cmds.textField(placeholderText="Search pattern")
    cmds.text(label="Replace with:")
    replace_field = cmds.textField(placeholderText="Replacement text (can be empty)")
    regex_checkbox = cmds.checkBox(label="Use Regular Expression", value=False)
    case_checkbox = cmds.checkBox(label="Case Sensitive", value=True)
    whole_name_checkbox = cmds.checkBox(label="Match whole name only", value=False)
    cmds.rowLayout(numberOfColumns=2, columnWidth2=(260,260))
    cmds.button(label="Apply Search & Replace", c=lambda *_: search_replace_selection(search_field, replace_field, regex_checkbox, case_checkbox, whole_name_checkbox))
    cmds.button(label="Preview (print)", c=lambda *_: print_preview_search_replace(search_field, replace_field, regex_checkbox, case_checkbox, whole_name_checkbox))
    cmds.setParent('..')

    # Bottom controls
    cmds.separator(height=8)
    cmds.rowLayout(numberOfColumns=2, columnWidth2=(260,260))
    cmds.button(label="Print current selection names", c=lambda *_: print_selection_names())
    cmds.button(label="Close Window", c=lambda *_: cmds.deleteUI(WINDOW_NAME))
    cmds.setParent('..')

    cmds.showWindow(win)

# Create UI on import/run
create_ui()
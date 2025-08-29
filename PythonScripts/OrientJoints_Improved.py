"""
Select 3 joints in a hierarchy, starting with parent going to child, to orient joints orthogonally and ready for IK
"""

import maya.cmds as cmds
import math

WINDOW_NAME = "threeJointOrthoOrientWin_v3"

# -------------------
# Vector helpers
# -------------------
def vec_sub(a, b): return [a[i] - b[i] for i in range(3)]
def vec_add(a, b): return [a[i] + b[i] for i in range(3)]
def vec_mul(a, s): return [a[i] * s for i in range(3)]
def vec_dot(a, b): return a[0]*b[0] + a[1]*b[1] + a[2]*b[2]
def vec_length(a): return math.sqrt(vec_dot(a,a))
def vec_normalize(a):
    L = vec_length(a)
    return [a[i] / L for i in range(3)] if L and L > 1e-12 else [0.0,0.0,0.0]
def vec_cross(a, b):
    return [a[1]*b[2] - a[2]*b[1],
            a[2]*b[0] - a[0]*b[2],
            a[0]*b[1] - a[1]*b[0]]

# -------------------
# Axis maps
# -------------------
AXIS_MAP = {
    '+X': (1,0,0), '-X': (-1,0,0),
    '+Y': (0,1,0), '-Y': (0,-1,0),
    '+Z': (0,0,1), '-Z': (0,0,-1),
}
AXIS_ABS = {'+X':(1,0,0), '-X':(1,0,0), '+Y':(0,1,0), '-Y':(0,1,0), '+Z':(0,0,1), '-Z':(0,0,1)}

# -------------------
# Utility / validation
# -------------------
def warn(msg):
    cmds.warning(msg)
    try:
        cmds.confirmDialog(title='Warning', message=msg, button=['OK'])
    except Exception:
        pass

def validate_selection(sel):
    if not sel or len(sel) != 3:
        warn("Please select exactly 3 joints (parent -> child -> grandchild).")
        return False
    for s in sel:
        if cmds.objectType(s) != 'joint':
            warn("Selection contains a non-joint item: %s" % s)
            return False
    p1 = cmds.listRelatives(sel[1], parent=True) or []
    p2 = cmds.listRelatives(sel[2], parent=True) or []
    if not p1 or p1[0] != sel[0] or not p2 or p2[0] != sel[1]:
        warn("Joints must be selected in hierarchy order: parent -> child -> grandchild.")
        return False
    return True

def compute_plane_normal(p1, p2, p3):
    v1 = vec_sub(p2, p1)
    v2 = vec_sub(p3, p1)
    n = vec_cross(v1, v2)
    L = vec_length(n)
    if L < 1e-6:
        return None
    return vec_normalize(n)

# -------------------
# Axis display toggle
# -------------------
def toggle_joint_axis_display():
    """
    Toggle displayLocalAxis on selected joints, or on all joints if none selected.
    """
    joints_sel = cmds.ls(sl=True, type='joint')
    if not joints_sel:
        joints_sel = cmds.ls(type='joint') or []
        if not joints_sel:
            cmds.inViewMessage(amg='No joints found to toggle axis display.', pos='topCenter', fade=True)
            return

    turn_off = False
    for j in joints_sel:
        try:
            val = cmds.getAttr(j + ".displayLocalAxis")
            if val:
                turn_off = True
                break
        except Exception:
            continue

    for j in joints_sel:
        try:
            cmds.setAttr(j + ".displayLocalAxis", 0 if turn_off else 1)
        except Exception:
            pass

    cmds.inViewMessage(amg=('Joint Local Rotation Axes %s' % ('Hidden' if turn_off else 'Shown')),
                       pos='topCenter', fade=True)

# -------------------
# Core orient routine
# -------------------
def orient_chain(primary_choice, secondary_choice):
    sel = cmds.ls(sl=True)
    if not validate_selection(sel):
        return
    j1, j2, j3 = sel

    # cache original parents (None if world)
    orig_parent_j1 = (cmds.listRelatives(j1, parent=True) or [None])[0]
    orig_parent_j2 = (cmds.listRelatives(j2, parent=True) or [None])[0]
    orig_parent_j3 = (cmds.listRelatives(j3, parent=True) or [None])[0]

    # read world positions first
    p1 = cmds.xform(j1, q=True, ws=True, t=True)
    p2 = cmds.xform(j2, q=True, ws=True, t=True)
    p3 = cmds.xform(j3, q=True, ws=True, t=True)

    plane_normal = compute_plane_normal(p1, p2, p3)
    if plane_normal is None:
        warn("Selected joints appear collinear or too close — cannot compute a stable plane normal.")
        return

    # axis validation (ignoring sign)
    if primary_choice[1] == secondary_choice[1]:
        warn("Primary and secondary axes cannot be the same axis (ignoring sign). Pick orthogonal axes.")
        return

    aimVec = AXIS_MAP[primary_choice]
    upVec_local = AXIS_ABS[secondary_choice]
    sec_sign = -1.0 if secondary_choice.startswith('-') else 1.0
    worldUpVec = vec_mul(plane_normal, sec_sign)

    temp_nodes = []
    opened_chunk = False
    try:
        cmds.undoInfo(openChunk=True)
        opened_chunk = True

        # Unparent chain to world to prevent children from moving when parent rotates
        for j in (j1, j2, j3):
            try:
                cmds.parent(j, world=True)
            except Exception:
                pass

        # Zero jointOrient (fail if locked)
        for j in (j1, j2, j3):
            try:
                cmds.setAttr(j + ".jointOrient", 0, 0, 0)
            except Exception:
                warn("Could not zero jointOrient for %s — attribute may be locked." % j)
                raise RuntimeError("jointOrient locked on %s" % j)

        # Create world-space locators as aim targets (avoid cycles)
        loc_j2 = cmds.spaceLocator(name='__tmp_orient_loc_j2__')[0]
        loc_j3 = cmds.spaceLocator(name='__tmp_orient_loc_j3__')[0]
        temp_nodes.extend([loc_j2, loc_j3])
        cmds.xform(loc_j2, ws=True, t=p2)
        cmds.xform(loc_j3, ws=True, t=p3)

        # j3 offset locator for aim direction (using j2->j3)
        desired_primary_vec = vec_sub(p3, p2)
        if vec_length(desired_primary_vec) < 1e-6:
            desired_primary_vec = [1.0, 0.0, 0.0]
        desired_primary_vec = vec_normalize(desired_primary_vec)
        dist = vec_length(vec_sub(p3, p2)) or 1.0
        loc_j3_offset = cmds.spaceLocator(name='__tmp_orient_loc_j3_dir__')[0]
        temp_nodes.append(loc_j3_offset)
        cmds.xform(loc_j3_offset, ws=True, t=vec_add(p3, vec_mul(desired_primary_vec, dist)))

        # Aim j1 at loc_j2
        c1 = cmds.aimConstraint(loc_j2, j1,
                                aimVector=aimVec,
                                upVector=upVec_local,
                                worldUpType='vector',
                                worldUpVector=worldUpVec,
                                mo=False)
        rot1 = cmds.getAttr(j1 + ".rotate")[0]
        cmds.delete(c1)
        cmds.setAttr(j1 + ".jointOrient", rot1[0], rot1[1], rot1[2])
        cmds.setAttr(j1 + ".rotate", 0, 0, 0)

        # Aim j2 at loc_j3
        c2 = cmds.aimConstraint(loc_j3, j2,
                                aimVector=aimVec,
                                upVector=upVec_local,
                                worldUpType='vector',
                                worldUpVector=worldUpVec,
                                mo=False)
        rot2 = cmds.getAttr(j2 + ".rotate")[0]
        cmds.delete(c2)
        cmds.setAttr(j2 + ".jointOrient", rot2[0], rot2[1], rot2[2])
        cmds.setAttr(j2 + ".rotate", 0, 0, 0)

        # Aim j3 at offset locator
        c3 = cmds.aimConstraint(loc_j3_offset, j3,
                                aimVector=aimVec,
                                upVector=upVec_local,
                                worldUpType='vector',
                                worldUpVector=worldUpVec,
                                mo=False)
        rot3 = cmds.getAttr(j3 + ".rotate")[0]
        cmds.delete(c3)
        cmds.setAttr(j3 + ".jointOrient", rot3[0], rot3[1], rot3[2])
        cmds.setAttr(j3 + ".rotate", 0, 0, 0)

        # Restore original parenting (root, middle, leaf)
        try:
            if orig_parent_j1:
                cmds.parent(j1, orig_parent_j1)
        except Exception:
            cmds.warning("Failed to reparent %s to original parent %s" % (j1, str(orig_parent_j1)))
        try:
            if orig_parent_j2:
                cmds.parent(j2, orig_parent_j2)
        except Exception:
            cmds.warning("Failed to reparent %s to original parent %s" % (j2, str(orig_parent_j2)))
        try:
            if orig_parent_j3:
                cmds.parent(j3, orig_parent_j3)
        except Exception:
            cmds.warning("Failed to reparent %s to original parent %s" % (j3, str(orig_parent_j3)))

    except Exception as e:
        cmds.warning("Orienting failed: %s" % str(e))
    finally:
        # cleanup temp nodes
        for n in temp_nodes:
            if cmds.objExists(n):
                try:
                    cmds.delete(n)
                except Exception:
                    pass
        if opened_chunk:
            try:
                cmds.undoInfo(closeChunk=True)
            except Exception:
                pass

    cmds.select(sel)
    cmds.inViewMessage(amg='Oriented joints: <hl>%s, %s, %s</hl>' % tuple(sel), pos='topCenter', fade=True)

# -------------------
# UI
# -------------------
def show_ui():
    if cmds.window(WINDOW_NAME, exists=True):
        try:
            cmds.deleteUI(WINDOW_NAME)
        except Exception:
            pass

    win = cmds.window(WINDOW_NAME, title="3-Joint Orthogonal Orientation Tool", sizeable=True, widthHeight=(420,180))

    # Simple column and row layouts which behave well when window is sizeable
    cmds.columnLayout(adjustableColumn=True, rowSpacing=8, columnAlign='center', columnAttach=('both', 8))
    cmds.text(label="Select exactly 3 joints in hierarchy order (parent -> child -> grandchild).", align='center')

    # Primary axis
    cmds.rowLayout(numberOfColumns=2, columnWidth2=(220,180), adjustableColumn=1)
    cmds.text(label="Primary axis (aim down chain):", align='left')
    prim_menu = cmds.optionMenu('primMenu_v3')
    for opt in ['+X','-X','+Y','-Y','+Z','-Z']:
        cmds.menuItem(label=opt)
    cmds.setParent('..')

    # Secondary axis (default to +Z)
    cmds.rowLayout(numberOfColumns=2, columnWidth2=(220,180), adjustableColumn=1)
    cmds.text(label="Secondary axis (orthogonal to joint plane):", align='left')
    sec_menu = cmds.optionMenu('secMenu_v3')
    for opt in ['+X','-X','+Y','-Y','+Z','-Z']:
        cmds.menuItem(label=opt)
    try:
        cmds.optionMenu(sec_menu, e=True, value='+Z')
    except Exception:
        pass
    cmds.setParent('..')

    cmds.separator(height=6, style='in')

    # Buttons row
    cmds.rowLayout(numberOfColumns=3, columnWidth3=(140,200,80), adjustableColumn=2)
    cmds.button(label="Orient Joints", height=36, command=lambda *a: _on_orient())
    cmds.button(label="Toggle Joint Axis Visibility", height=36, command=lambda *a: toggle_joint_axis_display())
    cmds.button(label="Close", height=36, command=lambda *a: cmds.deleteUI(win))
    cmds.setParent('..')

    cmds.showWindow(win)

    # local helper for orient button so we can query optionMenus
    def _on_orient():
        primary_choice = cmds.optionMenu('primMenu_v3', q=True, value=True)
        secondary_choice = cmds.optionMenu('secMenu_v3', q=True, value=True)
        sel = cmds.ls(sl=True)
        if not sel or len(sel) != 3:
            warn("Please select exactly 3 joints before pressing Orient.")
            return
        if primary_choice[1] == secondary_choice[1]:
            warn("Primary and secondary axes cannot be the same (ignoring sign). Pick orthogonal axes.")
            return
        orient_chain(primary_choice, secondary_choice)

# show UI immediately
show_ui()

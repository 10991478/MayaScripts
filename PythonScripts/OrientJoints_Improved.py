"""
Select 3 joints in a hierarchy in hierarchy order to orient them for IK
"""

import maya.cmds as cmds
import math

WINDOW_NAME = "orientThreeJointsWin_unparent_fix"

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

AXIS_MAP = {
    '+X': (1,0,0), '-X': (-1,0,0),
    '+Y': (0,1,0), '-Y': (0,-1,0),
    '+Z': (0,0,1), '-Z': (0,0,-1),
}
AXIS_ABS = {'+X':(1,0,0), '-X':(1,0,0), '+Y':(0,1,0), '-Y':(0,1,0), '+Z':(0,0,1), '-Z':(0,0,1)}

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

def orient_chain(primary_choice, secondary_choice):
    sel = cmds.ls(sl=True)
    if not validate_selection(sel):
        return
    j1, j2, j3 = sel

    # cache original parents (None if world)
    orig_parent_j1 = (cmds.listRelatives(j1, parent=True) or [None])[0]
    orig_parent_j2 = (cmds.listRelatives(j2, parent=True) or [None])[0]
    orig_parent_j3 = (cmds.listRelatives(j3, parent=True) or [None])[0]

    # read positions first (so temp locators get constant world positions)
    p1 = cmds.xform(j1, q=True, ws=True, t=True)
    p2 = cmds.xform(j2, q=True, ws=True, t=True)
    p3 = cmds.xform(j3, q=True, ws=True, t=True)

    plane_normal = compute_plane_normal(p1, p2, p3)
    if plane_normal is None:
        warn("Selected joints appear collinear or too close — cannot compute a stable plane normal.")
        return

    # validate axes (can't pick same axis ignoring sign)
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

        # Unparent all three to world (preserve world transform)
        # This prevents j2/j3 from moving when j1 gets reoriented.
        for j in (j1, j2, j3):
            try:
                cmds.parent(j, world=True)
            except Exception:
                # if already world or cannot, ignore and continue
                pass

        # Zero jointOrient first (if locked this will fail and we warn)
        for j in (j1, j2, j3):
            try:
                cmds.setAttr(j + ".jointOrient", 0, 0, 0)
            except Exception:
                warn("Could not zero jointOrient for %s — attribute may be locked." % j)
                # attempt to restore parents before exiting
                # break out by raising
                raise

        # create world-space locators to aim at (no chance of cycles)
        loc_j2 = cmds.spaceLocator(name='__orient_temp_loc_j2__')[0]
        loc_j3 = cmds.spaceLocator(name='__orient_temp_loc_j3__')[0]
        temp_nodes.extend([loc_j2, loc_j3])
        cmds.xform(loc_j2, ws=True, t=p2)
        cmds.xform(loc_j3, ws=True, t=p3)

        # create offset locator for j3 aim direction (j3 -> direction from j2->j3)
        desired_primary_vec = vec_sub(p3, p2)
        if vec_length(desired_primary_vec) < 1e-6:
            desired_primary_vec = [1.0, 0.0, 0.0]
        desired_primary_vec = vec_normalize(desired_primary_vec)
        dist = vec_length(vec_sub(p3, p2)) or 1.0
        loc_j3_offset = cmds.spaceLocator(name='__orient_temp_loc_j3_dir__')[0]
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

        # Aim j3 at loc_j3_offset
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

        # Restore original parenting in order: root, middle, leaf.
        # Use cmds.parent(child, parent) which preserves world transforms by default.
        try:
            if orig_parent_j1:
                cmds.parent(j1, orig_parent_j1)
        except Exception:
            cmds.warning("Failed to reparent %s to its original parent %s" % (j1, str(orig_parent_j1)))

        try:
            if orig_parent_j2:
                cmds.parent(j2, orig_parent_j2)
        except Exception:
            # If original parent was the original j1, it has been restored above.
            cmds.warning("Failed to reparent %s to its original parent %s" % (j2, str(orig_parent_j2)))

        try:
            if orig_parent_j3:
                cmds.parent(j3, orig_parent_j3)
        except Exception:
            cmds.warning("Failed to reparent %s to its original parent %s" % (j3, str(orig_parent_j3)))

    except Exception as e:
        # If an exception occurred (e.g., locked attrs), ensure we still try to cleanup and restore parents
        cmds.warning("Orienting failed: %s" % str(e))
    finally:
        # cleanup temp locators
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

    # re-select original joints and notify
    cmds.select(sel)
    cmds.inViewMessage(amg='Oriented joints: <hl>%s, %s, %s</hl>' % tuple(sel), pos='topCenter', fade=True)

# UI
def show_ui():
    if cmds.window(WINDOW_NAME, exists=True):
        cmds.deleteUI(WINDOW_NAME)
    win = cmds.window(WINDOW_NAME, title="Orient 3-Joint Chain (Unparent Fix)", widthHeight=(400,160), sizeable=False)
    cmds.columnLayout(adjustableColumn=True, columnAlign='center', rowSpacing=6, columnAttach=('both', 6))
    cmds.text(label="Select exactly 3 joints in hierarchy order (parent -> child -> grandchild).", align='center')

    cmds.rowLayout(numberOfColumns=2, columnWidth2=(200,200), columnAlign2=('left','left'), columnAttach2=('both','both'))
    cmds.text(label="Primary axis (aim down chain):", align='left')
    primary_menu = cmds.optionMenu('primaryMenu_upf')
    for opt in ['+X','-X','+Y','-Y','+Z','-Z']:
        cmds.menuItem(label=opt)
    cmds.setParent('..')

    cmds.rowLayout(numberOfColumns=2, columnWidth2=(200,200), columnAlign2=('left','left'), columnAttach2=('both','both'))
    cmds.text(label="Secondary axis (orthogonal to joint plane):", align='left')
    secondary_menu = cmds.optionMenu('secondaryMenu_upf')
    for opt in ['+X','-X','+Y','-Y','+Z','-Z']:
        cmds.menuItem(label=opt)
    cmds.setParent('..')

    cmds.separator(height=8, style='in')

    def on_orient(*args):
        primary_choice = cmds.optionMenu('primaryMenu_upf', q=True, value=True)
        secondary_choice = cmds.optionMenu('secondaryMenu_upf', q=True, value=True)
        sel = cmds.ls(sl=True)
        if not sel or len(sel) != 3:
            warn("Please select exactly 3 joints before pressing Orient.")
            return
        if primary_choice[1] == secondary_choice[1]:
            warn("Primary and secondary axes cannot be the same (ignoring sign). Pick orthogonal axes.")
            return
        orient_chain(primary_choice, secondary_choice)

    cmds.rowLayout(numberOfColumns=2, columnWidth2=(200,200), columnAlign2=('center','center'))
    cmds.button(label="Orient Joints", height=36, command=on_orient)
    cmds.button(label="Close", height=36, command=lambda *a: cmds.deleteUI(win))
    cmds.setParent('..')

    cmds.showWindow(win)

# Show the UI immediately when this script runs
show_ui()
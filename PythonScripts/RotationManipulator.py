#A tool for manipulating rotations of objects with a couple standard ways of changing rotation

import maya.cmds as cmds

def rotate_objects(axis, mode, keep_minimal):
    selection = cmds.ls(selection=True)
    if not selection:
        cmds.warning("No objects selected!")
        return
    
    for obj in selection:
        # Get the current rotation as a float
        current_rotation = cmds.getAttr("{}.rotate{}".format(obj, axis))
        new_rotation = current_rotation
        
        if mode == "invert":
            new_rotation = -current_rotation
        elif mode == "180":
            # Add 180 if current rotation is negative, subtract 180 if it's positive or zero.
            if current_rotation < 0:
                new_rotation = current_rotation + 180
            else:
                new_rotation = current_rotation - 180
        elif mode == "90_pos":
            new_rotation = current_rotation + 90
            if keep_minimal:
                new_rotation %= 360
        elif mode == "90_neg":
            new_rotation = current_rotation - 90
            if keep_minimal:
                new_rotation %= 360
        
        cmds.setAttr("{}.rotate{}".format(obj, axis), new_rotation)

def create_ui():
    window_name = "RotateUI"
    if cmds.window(window_name, exists=True):
        cmds.deleteUI(window_name)
    
    window = cmds.window(window_name, title="Rotation Tool", widthHeight=(300, 200))
    cmds.columnLayout(adjustableColumn=True)
    
    # Create the checkbox for keeping minimal rotations
    keep_minimal_rot = cmds.checkBox(label="Keep Minimal Rotations", value=True)
    
    def create_axis_section(axis):
        cmds.frameLayout(label="Rotate " + axis, collapsable=True, marginHeight=5)
        cmds.columnLayout()
        cmds.button(label="Invert", command=lambda _: rotate_objects(axis, "invert", cmds.checkBox(keep_minimal_rot, query=True, value=True)))
        cmds.button(label="Rotate 180°", command=lambda _: rotate_objects(axis, "180", cmds.checkBox(keep_minimal_rot, query=True, value=True)))
        cmds.button(label="Rotate 90° +", command=lambda _: rotate_objects(axis, "90_pos", cmds.checkBox(keep_minimal_rot, query=True, value=True)))
        cmds.button(label="Rotate 90° -", command=lambda _: rotate_objects(axis, "90_neg", cmds.checkBox(keep_minimal_rot, query=True, value=True)))
        cmds.setParent("..")
        cmds.setParent("..")
    
    for axis in ["X", "Y", "Z"]:
        create_axis_section(axis)
    
    cmds.showWindow(window)

create_ui()
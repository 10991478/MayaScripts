#select three joints in a hierarchy to orient them no matter their position

import maya.cmds as cmds
import maya.api.OpenMaya as om

def orient_three_joints():
    # Get selected joints
    selection = cmds.ls(selection=True, type="joint")
    
    # Validate selection
    if len(selection) != 3:
        cmds.error("Please select exactly three joints.")
    
    j1, j2, j3 = selection
    
    # Validate hierarchy
    if cmds.listRelatives(j2, parent=True) != [j1]:
        cmds.error("Second joint must be a child of the first joint.")
    if cmds.listRelatives(j3, parent=True) != [j2]:
        cmds.error("Third joint must be a child of the second joint.")
    if cmds.listRelatives(j1, parent=True) is not None:
        cmds.error("First joint must be parented to the world.")
    
    # Unparent joints
    cmds.parent(j2, world=True)
    cmds.parent(j3, world=True)
    
    # Get joint positions
    pos1 = om.MVector(cmds.xform(j1, query=True, worldSpace=True, translation=True))
    pos2 = om.MVector(cmds.xform(j2, query=True, worldSpace=True, translation=True))
    pos3 = om.MVector(cmds.xform(j3, query=True, worldSpace=True, translation=True))
    
    # Compute vectors
    x_axis = (pos2 - pos1).normalize()
    temp_vec = (pos3 - pos2).normalize()
    z_axis = (x_axis ^ temp_vec).normalize()  # Cross product for orthogonal vector
    y_axis = (z_axis ^ x_axis).normalize()  # Ensure orthogonality
    
    # Create transformation matrix
    matrix = [
        x_axis.x, x_axis.y, x_axis.z, 0,
        y_axis.x, y_axis.y, y_axis.z, 0,
        z_axis.x, z_axis.y, z_axis.z, 0,
        pos1.x, pos1.y, pos1.z, 1
    ]
    
    # Apply orientation to first joint
    cmds.xform(j1, worldSpace=True, matrix=matrix)
    cmds.makeIdentity(j1, apply=True, rotate=True)
    
    # Reparent joints
    cmds.parent(j2, j1)
    cmds.parent(j3, j2)
    
    #Point seconds joint towards third, then set x and y orientation to 0, set third joint orientation to all 0s
    cmds.joint(j2, edit=True, orientJoint='xyz', secondaryAxisOrient='yup', zeroScaleOrient=True)
    cmds.setAttr(f"{j2}.jointOrientX", 0)
    cmds.setAttr(f"{j2}.jointOrientY", 0)
    cmds.setAttr(f"{j3}.jointOrientX", 0)
    cmds.setAttr(f"{j3}.jointOrientY", 0)
    cmds.setAttr(f"{j3}.jointOrientZ", 0)
    
    print("Joints oriented successfully and hierarchy restored.")

# Run the function
orient_three_joints()

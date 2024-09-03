import maya.cmds as cmds


sels = cmds.ls(sl = True)

for index in range(0,len(sels) - 1, 1):
    parent_ctrl = sels[index]
    child_ctrl = sels[index + 1]
    
    child_ctrl_grp = cmds.listRelatives(child_ctrl, parent = True)[0]
    
    
    #creating parent constraints with and without translate/rotate
    p_constraint1 = cmds.parentConstraint(parent_ctrl, child_ctrl_grp, mo=True, skipRotate = ['x','y','z'], weight = 1)[0]
    p_constraint2 = cmds.parentConstraint(parent_ctrl, child_ctrl_grp, mo=True, skipTranslate = ['x','y','z'], weight = 1)[0]
    
    
    #adding custom attributes
    cmds.addAttr(child_ctrl, ln="Follow_Translate", at = "double", min = 0, max = 1, dv = 1)
    cmds.setAttr(f"{child_ctrl}.Follow_Translate", e=True, keyable=True)
    cmds.addAttr(child_ctrl, ln="Follow_Rotate", at = "double", min = 0, max = 1, dv = 1)
    cmds.setAttr(f"{child_ctrl}.Follow_Rotate", e=True, keyable=True)
    
    #connecting custom attributes to parent constraints
    cmds.connectAttr(f"{child_ctrl}.Follow_Translate", f"{p_constraint1}.w0", f=True)
    cmds.connectAttr(f"{child_ctrl}.Follow_Rotate", f"{p_constraint2}.w0", f=True)
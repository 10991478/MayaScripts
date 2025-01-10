#This script is for creating lower-limb twist joints setup. Select the elbow & wrist (or knee and ankle) joints then run!



import maya.cmds as cmds

def create_lower_limb_twist_joints():
    def on_execute(*args):
        num_joints = cmds.intField(number_of_joints_field, query=True, value=True)
        joint_radius = cmds.floatField(joint_radius_field, query=True, value=True)
        left_side = cmds.checkBox(left_side_checkbox, query=True, value=True)
        prefix = cmds.textField(name_prefix_field, query=True, text=True)

        selection = cmds.ls(selection=True, type="joint")

        if len(selection) != 2:
            cmds.error("Please select exactly two joints (elbow and wrist).")

        elbow_joint, wrist_joint = selection
        left_right_multiplier = 1 if left_side else -1

        # Create the group
        loc_group_name = f"{prefix}Lower_Twist_Loc_Grp"
        loc_group = cmds.group(empty=True, name=loc_group_name)
        cmds.delete(cmds.parentConstraint(wrist_joint, loc_group))
        cmds.parentConstraint(wrist_joint, loc_group, maintainOffset=True)

        # Create locators
        aim_loc = cmds.spaceLocator(name=f"{prefix}Lower_Twist_Aim_Loc")[0]
        target_loc = cmds.spaceLocator(name=f"{prefix}Lower_Twist_Target_Loc")[0]
        up_loc = cmds.spaceLocator(name=f"{prefix}Lower_Twist_Up_Loc")[0]

        cmds.parent(aim_loc, loc_group)
        cmds.parent(target_loc, loc_group)
        cmds.parent(up_loc, loc_group)

        # Position locators
        cmds.delete(cmds.parentConstraint(wrist_joint, aim_loc))
        cmds.delete(cmds.parentConstraint(elbow_joint, target_loc))
        cmds.parentConstraint(elbow_joint, target_loc)

        cmds.setAttr(f"{aim_loc}.translateX", 0)
        cmds.setAttr(f"{aim_loc}.translateY", 0)
        cmds.setAttr(f"{aim_loc}.translateZ", 0)

        cmds.setAttr(f"{up_loc}.translateX", 0)
        cmds.setAttr(f"{up_loc}.translateY", 10)
        cmds.setAttr(f"{up_loc}.translateZ", 0)

        # Set up aim constraint
        cmds.aimConstraint(
            target_loc, aim_loc, 
            aimVector=(-1*left_right_multiplier, 0, 0), 
            upVector=(0, 1, 0), 
            worldUpObject=up_loc, 
            worldUpType="object")

        # Create end joint
        end_joint = cmds.joint(name=f"{prefix}Lower_Twist_End_Jnt", radius=joint_radius)
        cmds.delete(cmds.parentConstraint(wrist_joint, end_joint))
        cmds.parent(end_joint, elbow_joint)
        cmds.matchTransform(end_joint, wrist_joint)
        cmds.makeIdentity(end_joint, apply=True, rotate=True)
        cmds.parentConstraint(aim_loc, end_joint)

        # Create twist joints
        for i in range(1, num_joints + 1):
            joint_name = f"{prefix}Lower_Twist_{i:02}_Jnt"
            twist_joint = cmds.joint(name=joint_name, radius=joint_radius)
            cmds.parent(twist_joint, elbow_joint)
            cmds.matchTransform(twist_joint, wrist_joint)
            cmds.makeIdentity(twist_joint, apply=True, rotate=True)
            cmds.pointConstraint(elbow_joint, twist_joint, weight=(num_joints - i + 1))
            cmds.pointConstraint(end_joint, twist_joint, weight=i)
            cmds.orientConstraint(elbow_joint, twist_joint, weight=(num_joints - i + 1))
            cmds.orientConstraint(end_joint, twist_joint, weight=i)

    # Create UI
    if cmds.window("lowerLimbTwistWindow", exists=True):
        cmds.deleteUI("lowerLimbTwistWindow")

    window = cmds.window("lowerLimbTwistWindow", title="Lower-Limb Twist Joints", sizeable=False, widthHeight=(400, 300))
    layout = cmds.columnLayout(adjustableColumn=True)

    cmds.text(label="Number of Joints:")
    number_of_joints_field = cmds.intField(value=3, minValue=1, maxValue=20)

    cmds.text(label="Joint Radius:")
    joint_radius_field = cmds.floatField(value=0.5)

    cmds.text(label="Left Side:")
    left_side_checkbox = cmds.checkBox(label = "Left Side", value=True)

    cmds.text(label="Name Prefix:")
    name_prefix_field = cmds.textField()

    cmds.button(label="Create Twist Joints", command=on_execute)

    cmds.setParent('..')
    cmds.showWindow(window)

# Run the function to create the UI
create_lower_limb_twist_joints()
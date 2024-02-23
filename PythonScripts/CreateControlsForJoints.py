import maya.cmds as cmds

def create_control_and_group(joint):
    # Get joint position
    joint_position = cmds.xform(joint, q=True, ws=True, t=True)
    
    # Get joint orientation
    joint_orientation = cmds.joint(joint, q=True, orientation = True)
    
    # Create control curve (circle)
    control_curve = cmds.circle(normal=(0, 1, 0), radius=1)[0]
    
    # Move control curve to joint position
    cmds.xform(control_curve, ws=True, t=joint_position, ro=joint_orientation)
    
    # Create parent group
    parent_group = cmds.group(em=True)
    
    # Move parent group to joint position
    cmds.xform(parent_group, ws=True, t=joint_position)
    
    # Match rotation of parent group to joint orientation
    cmds.xform(parent_group, ws=True, ro=joint_orientation)
    
    # Parent control under parent group
    cmds.parent(control_curve, parent_group)
    cmds.setAttr(f"{control_curve}.rx", 90)
    cmds.makeIdentity(control_curve, apply = True, rotate = True)
    
    # Rename control and parent group
    control_name = joint + '_ctrl'
    parent_group_name = joint + '_grp'
    cmds.rename(control_curve, control_name)
    cmds.rename(parent_group, parent_group_name)
    
    return control_name, parent_group_name

def main():
    # Get selected joints
    selected_joints = cmds.ls(selection=True, type='joint')
    
    if not selected_joints:
        cmds.warning("No joints selected. Please select one or more joints.")
        return
    
    for joint in selected_joints:
        control_name, parent_group_name = create_control_and_group(joint)
        print(f"Created control: {control_name}, parent group: {parent_group_name}")

if __name__ == "__main__":
    main()
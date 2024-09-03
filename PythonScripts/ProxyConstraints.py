import maya.cmds as cmds

def constrain_geometry_to_joint():
    # Get selected geometry and joint
    selected_geo = cmds.ls(selection=True, type='transform')
    if not selected_geo:
        cmds.warning("Please select the geometry to constrain.")
        return
    selected_joint = cmds.ls(selection=True, type='joint')
    if not selected_joint:
        cmds.warning("Please select the joint to constrain to.")
        return

    # Parent and scale constrain selected geometry to joint
    for geo in selected_geo:
        parent_constraint = cmds.parentConstraint(selected_joint, geo, maintainOffset=True)
        scale_constraint = cmds.scaleConstraint(selected_joint, geo, maintainOffset=True)

        # Rename geometry using joint name
        joint_name = selected_joint[0]
        new_name = joint_name.rpartition('_Jnt')[0] + '_Proxy_Geo'
        cmds.rename(geo, new_name)

        cmds.select(clear=True)

constrain_geometry_to_joint()
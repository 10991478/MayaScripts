#Create constraints and switch for functioning RK system


import maya.cmds as cmds

def create_rk_ui():
    # Check if the window exists, delete if it does
    if cmds.window("rkSystemUI", exists=True):
        cmds.deleteUI("rkSystemUI")

    # Create the window
    window = cmds.window("rkSystemUI", title="RK System Creator", widthHeight=(400, 200))

    # Layout
    cmds.columnLayout(adjustableColumn=True, rowSpacing=10)

    # Text fields and buttons
    global rk_field, switch_field, fk_field, ik_field

    rk_field = cmds.textFieldButtonGrp(label="RK Joints: ", buttonLabel="Set", cw=[(1, 200), (2, 200)], buttonCommand=set_rk_joints)
    switch_field = cmds.textFieldButtonGrp(label="IKFK Switch Control: ", buttonLabel="Set", cw=[(1, 200), (2, 200)], buttonCommand=set_switch_control)
    fk_field = cmds.textFieldButtonGrp(label="FK Visibility Objects: ", buttonLabel="Set", cw=[(1, 200), (2, 200)], buttonCommand=set_fk_visibility)
    ik_field = cmds.textFieldButtonGrp(label="IK Visibility Objects: ", buttonLabel="Set", cw=[(1, 200), (2, 200)], buttonCommand=set_ik_visibility)

    # Create button to execute the RK system creation
    cmds.button(label="Create RK System", command=create_rk_system)

    # Show the window
    cmds.showWindow(window)

# Functions to populate text fields with current selection
def set_rk_joints(*args):
    selection = cmds.ls(selection=True)
    if selection:
        cmds.textFieldButtonGrp(rk_field, edit=True, text=", ".join(selection))

def set_switch_control(*args):
    selection = cmds.ls(selection=True)
    if selection:
        cmds.textFieldButtonGrp(switch_field, edit=True, text=selection[0])

def set_fk_visibility(*args):
    selection = cmds.ls(selection=True)
    if selection:
        cmds.textFieldButtonGrp(fk_field, edit=True, text=", ".join(selection))

def set_ik_visibility(*args):
    selection = cmds.ls(selection=True)
    if selection:
        cmds.textFieldButtonGrp(ik_field, edit=True, text=", ".join(selection))

def create_rk_system(*args):
    # Get user input from fields
    rk_joints = cmds.textFieldButtonGrp(rk_field, query=True, text=True).split(", ")
    ikfk_switch_control = cmds.textFieldButtonGrp(switch_field, query=True, text=True)
    fk_objects = cmds.textFieldButtonGrp(fk_field, query=True, text=True).split(", ")
    ik_objects = cmds.textFieldButtonGrp(ik_field, query=True, text=True).split(", ")

    if not rk_joints or not ikfk_switch_control or not fk_objects or not ik_objects:
        cmds.warning("Please ensure all fields are filled before creating the RK system.")
        return

    # Create FK and IK joint lists
    fk_joints = [joint.replace("RK_", "FK_") for joint in rk_joints]
    ik_joints = [joint.replace("RK_", "IK_") for joint in rk_joints]

    # Add IKFK_Switch attribute to the control
    if not cmds.attributeQuery("IKFK_Switch", node=ikfk_switch_control, exists=True):
        cmds.addAttr(ikfk_switch_control, longName="IKFK_Switch", attributeType="float", min=0, max=1, defaultValue=0, keyable=True)

    # Create constraints and connect visibility
    for rk, fk, ik in zip(rk_joints, fk_joints, ik_joints):
        if not cmds.objExists(fk):
            cmds.warning(f"FK joint {fk} does not exist. Skipping.")
            continue

        if not cmds.objExists(ik):
            cmds.warning(f"IK joint {ik} does not exist. Skipping.")
            continue

        # Parent and scale constraints
        parent_constraint = cmds.parentConstraint(fk, ik, rk, maintainOffset=True)[0]
        scale_constraint = cmds.scaleConstraint(fk, ik, rk, maintainOffset=True)[0]

        # Connect the constraints to the IKFK_Switch attribute
        cmds.connectAttr(f"{ikfk_switch_control}.IKFK_Switch", f"{parent_constraint}.{ik}W1")
        cmds.connectAttr(f"{ikfk_switch_control}.IKFK_Switch", f"{scale_constraint}.{ik}W1")

        reverse_node = cmds.createNode("reverse", name=f"{rk}_IKFK_Reverse")
        cmds.connectAttr(f"{ikfk_switch_control}.IKFK_Switch", f"{reverse_node}.inputX")

        cmds.connectAttr(f"{reverse_node}.outputX", f"{parent_constraint}.{fk}W0")
        cmds.connectAttr(f"{reverse_node}.outputX", f"{scale_constraint}.{fk}W0")

    # Connect visibility
    for fk_obj in fk_objects:
        if cmds.objExists(fk_obj):
            reverse_node = cmds.createNode("reverse", name=f"{fk_obj}_Vis_Reverse")
            cmds.connectAttr(f"{ikfk_switch_control}.IKFK_Switch", f"{reverse_node}.inputX")
            cmds.connectAttr(f"{reverse_node}.outputX", f"{fk_obj}.visibility")

    for ik_obj in ik_objects:
        if cmds.objExists(ik_obj):
            cmds.connectAttr(f"{ikfk_switch_control}.IKFK_Switch", f"{ik_obj}.visibility")

# Run the script
create_rk_ui()
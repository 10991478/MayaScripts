#create parent groups/offset groups for all selected objects

import maya.cmds as cmds

def create_groups(*args):
    # Query checkbox values
    parentChecked = cmds.checkBox("parentCheckBox", q=True, value=True)
    offsetChecked = cmds.checkBox("offsetCheckBox", q=True, value=True)

    # Warn if neither checkbox is selected
    if not (parentChecked or offsetChecked):
        cmds.warning("You must check at least one of the options (Parent Group or Offset Group).")
        return

    # Get current selection
    selection = cmds.ls(selection=True)
    if not selection:
        cmds.warning("No objects selected!")
        return

    # Process each selected object
    for obj in selection:
        # Get object's original parent (if any)
        origParent = cmds.listRelatives(obj, parent=True) or []

        # Both Parent Group and Offset Group are checked:
        if parentChecked and offsetChecked:
            # Create the Parent Group
            parentGrpName = "{}_Grp".format(obj)
            parentGrp = cmds.group(em=True, name=parentGrpName)
            if origParent:
                cmds.parent(parentGrp, origParent[0])
            cmds.delete(cmds.parentConstraint(obj, parentGrp))

            # Create the Offset Group as a child of the Parent Group
            offsetGrpName = "{}_Offset_Grp".format(obj)
            offsetGrp = cmds.group(em=True, name=offsetGrpName)
            cmds.parent(offsetGrp, parentGrp)
            cmds.delete(cmds.parentConstraint(obj, offsetGrp))
            cmds.parent(obj, offsetGrp)

        # Only Parent Group is checked:
        elif parentChecked:
            parentGrpName = "{}_Grp".format(obj)
            parentGrp = cmds.group(em=True, name=parentGrpName)
            if origParent:
                cmds.parent(parentGrp, origParent[0])
            cmds.delete(cmds.parentConstraint(obj, parentGrp))
            cmds.parent(obj, parentGrp)

        # Only Offset Group is checked:
        elif offsetChecked:
            offsetGrpName = "{}_Offset_Grp".format(obj)
            offsetGrp = cmds.group(em=True, name=offsetGrpName)
            if origParent:
                cmds.parent(offsetGrp, origParent[0])
            cmds.delete(cmds.parentConstraint(obj, offsetGrp))
            cmds.parent(obj, offsetGrp)

def create_ui():
    # If the window already exists, delete it
    if cmds.window("groupWindow", exists=True):
        cmds.deleteUI("groupWindow")
    
    # Create a new window with a slightly larger size
    window = cmds.window("groupWindow", title="Group Creator", widthHeight=(250, 120), sizeable=False)
    cmds.columnLayout(adjustableColumn=True, rowSpacing=10, columnAlign='center')
    
    # Create checkboxes for Parent Group and Offset Group
    cmds.checkBox("parentCheckBox", label="Parent Group", value=False)
    cmds.checkBox("offsetCheckBox", label="Offset Group", value=False)
    
    # Create a button to run the script
    cmds.button(label="Create Groups", command=create_groups, height=35)
    
    cmds.showWindow(window)

# Run the UI creation function
create_ui()
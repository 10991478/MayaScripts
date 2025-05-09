#Maya script for adding space switching to any objects in a parent group

import maya.cmds as cmds

def get_selected_objects(text_field):
    """Get selected objects and set the text field with their names."""
    selection = cmds.ls(selection=True)
    if selection:
        cmds.textField(text_field, edit=True, text=', '.join(selection))
    else:
        cmds.warning("No objects selected.")

def apply_space_switch(target_control, object_spaces, maintain_offset):
    """Apply space switching logic."""
    if not target_control or not object_spaces:
        cmds.warning("Target control or object spaces are missing.")
        return

    object_spaces_list = object_spaces.split(', ')
    
    # Create or find parent group for the target control
    target_group = target_control + "_Grp"
    if not cmds.objExists(target_group):
        cmds.group(target_control, name=target_group)
    
    # Check if constraint exists
    existing_constraints = cmds.listRelatives(target_group, type='parentConstraint') or []
    if existing_constraints:
        cmds.delete(existing_constraints)
    
    # Add parent constraint with offset option
    constraint = cmds.parentConstraint(object_spaces_list, target_group, maintainOffset=maintain_offset)[0]
    
    # Add or update enum attribute
    enum_values = ':'.join(object_spaces_list)
    if cmds.attributeQuery('Operating_Space', node=target_control, exists=True):
        cmds.addAttr(target_control, edit=True, enumName=enum_values)
    else:
        cmds.addAttr(target_control, longName='Operating_Space', attributeType='enum', enumName=enum_values, keyable=True)
    
    # Set driven keys for space switching
    for i, obj_space in enumerate(object_spaces_list):
        cmds.setAttr(f"{target_control}.Operating_Space", i)
        cmds.setAttr(f"{constraint}.w{i}", 1)
        cmds.setDrivenKeyframe(f"{constraint}.w{i}", cd=f"{target_control}.Operating_Space")
        for j in range(len(object_spaces_list)):
            if j != i:
                cmds.setAttr(f"{constraint}.w{j}", 0)
                cmds.setDrivenKeyframe(f"{constraint}.w{j}", cd=f"{target_control}.Operating_Space")

def remove_space_switch(target_control):
    """Remove space switching setup."""
    if not target_control:
        cmds.warning("No target control specified.")
        return
    
    target_group = target_control + "_Grp"
    if cmds.objExists(target_group):
        cmds.delete(target_group)
    
    if cmds.attributeQuery('Operating_Space', node=target_control, exists=True):
        cmds.deleteAttr(f"{target_control}.Operating_Space")

def create_ui():
    """Create a UI for inputting the target control and object spaces."""
    if cmds.window("spaceSwitchUI", exists=True):
        cmds.deleteUI("spaceSwitchUI")
    
    window = cmds.window("spaceSwitchUI", title="Space Switching Setup", widthHeight=(400, 200))
    cmds.columnLayout(adjustableColumn=True, rowSpacing=10)
    
    # Target Control UI
    cmds.text(label="Target Control:")
    target_control_field = cmds.textField()
    cmds.button(label="Set Target Control", 
                command=lambda x: get_selected_objects(target_control_field))
    
    # Object Spaces UI
    cmds.text(label="Object Spaces (select multiple objects):")
    object_spaces_field = cmds.textField()
    cmds.button(label="Set Object Spaces", 
                command=lambda x: get_selected_objects(object_spaces_field))
    
    # Checkbox for Maintain Offset
    maintain_offset_checkbox = cmds.checkBox(label="Maintain Offset", value=True)
    
    # Apply Button
    cmds.button(label="Apply Space Switching", 
                command=lambda x: apply_space_switch(
                    cmds.textField(target_control_field, query=True, text=True), 
                    cmds.textField(object_spaces_field, query=True, text=True),
                    cmds.checkBox(maintain_offset_checkbox, query=True, value=True)
                ))
    
    # Remove Space Switching Button
    cmds.button(label="Remove Space Switching", 
                command=lambda x: remove_space_switch(
                    cmds.textField(target_control_field, query=True, text=True)))
    
    cmds.showWindow(window)

# Run the UI
create_ui()

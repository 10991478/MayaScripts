#Create parent constraints going down the list of selected objects, constraining the next object's parent group to the current object


import maya.cmds as cmds

def create_parent_constraints():
    # Get the current selection
    selection = cmds.ls(sl=True)
    
    # Check if the selection has more than 1 object
    if len(selection) < 2:
        cmds.warning("Please select at least two objects.")
        return
    
    # Cycle through the selection
    for i in range(len(selection) - 1):
        # Current item
        current_item = selection[i]
        
        # Next item in the list
        next_item = selection[i + 1]
        
        # Generate the next item's group name by appending '_Grp'
        next_item_grp = next_item + "_Grp"
        
        # Check if the group exists, if not, create it
        if not cmds.objExists(next_item_grp):
            cmds.group(empty=True, name=next_item_grp)
            cmds.parent(next_item, next_item_grp)
        
        # Create the parent constraint (current_item constraining the next_item's group)
        cmds.parentConstraint(current_item, next_item_grp, mo=True)
    
    # Print message after completion
    print("Parent constraints created for selection.")

# Run the function
create_parent_constraints()
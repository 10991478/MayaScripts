#Create parent and scale constraints for the objects corresponding to your current selection


import maya.cmds as cmds

class ConstraintTool:
    def __init__(self):
        self.window = "constraintToolWindow"
        self.create_ui()

    def create_ui(self):
        if cmds.window(self.window, exists=True):
            cmds.deleteUI(self.window)
        
        self.window = cmds.window(self.window, title="Constraint Tool", widthHeight=(300, 200))
        cmds.columnLayout(adjustableColumn=True)
        
        self.constrainerPrefix = cmds.textFieldGrp(label="Constrainer Prefix: ")
        self.constrainerSuffix = cmds.textFieldGrp(label="Constrainer Suffix: ", text="_Ctrl")
        self.constrainedPrefix = cmds.textFieldGrp(label="Constrained Prefix: ")
        self.constrainedSuffix = cmds.textFieldGrp(label="Constrained Suffix: ", text="_Jnt")
        
        self.parentConstraint = cmds.checkBox(label="Parent Constraint", value=True)
        self.scaleConstraint = cmds.checkBox(label="Scale Constraint", value=True)
        
        cmds.button(label="Create Constraints", command=self.create_constraints)
        
        cmds.showWindow(self.window)

    def create_constraints(self, *args):
        selection = cmds.ls(selection=True)
        if not selection:
            cmds.warning("No objects selected.")
            return

        constrainer_prefix = cmds.textFieldGrp(self.constrainerPrefix, query=True, text=True)
        constrainer_suffix = cmds.textFieldGrp(self.constrainerSuffix, query=True, text=True)
        constrained_prefix = cmds.textFieldGrp(self.constrainedPrefix, query=True, text=True)
        constrained_suffix = cmds.textFieldGrp(self.constrainedSuffix, query=True, text=True)
        
        apply_parent_constraint = cmds.checkBox(self.parentConstraint, query=True, value=True)
        apply_scale_constraint = cmds.checkBox(self.scaleConstraint, query=True, value=True)
        
        constrainers = [obj for obj in selection if obj.startswith(constrainer_prefix) and obj.endswith(constrainer_suffix)]
        
        if len(constrainers) < len(selection):
            cmds.warning("Not all selected items matched the constrainer prefix and suffix.")
        
        for constrainer in constrainers:
            constrained = constrainer.replace(constrainer_prefix, constrained_prefix).replace(constrainer_suffix, constrained_suffix)
            if cmds.objExists(constrained):
                if apply_parent_constraint:
                    cmds.parentConstraint(constrainer, constrained, maintainOffset=True)
                if apply_scale_constraint:
                    cmds.scaleConstraint(constrainer, constrained, maintainOffset=True)
            else:
                cmds.warning(f"Constrained object '{constrained}' does not exist.")

ConstraintTool()
#Basic Maya python script for creating curves based on edge loop

import maya.cmds as cmds

class EdgeToCurveTool(object):
    WINDOW_NAME = "edgeToCurveWindow"

    def __init__(self):
        # If window exists, delete it
        if cmds.window(self.WINDOW_NAME, exists=True):
            cmds.deleteUI(self.WINDOW_NAME)
        self.build_ui()

    def build_ui(self):
        # Create window
        self.window = cmds.window(self.WINDOW_NAME, title="Edge to Curve Tool", widthHeight=(250, 100))
        self.layout = cmds.columnLayout(adjustableColumn=True, rowSpacing=10, columnAlign="center")

        # Smooth checkbox (on by default)
        self.smooth_cb = cmds.checkBox(label="Smooth (Degree 3)", value=True)

        # Create Curve button
        cmds.button(label="Create Curve", command=self.create_curve)

        cmds.showWindow(self.window)

    def create_curve(self, *args):
        # Get edge selection
        sel = cmds.ls(selection=True, flatten=True)
        if not sel:
            cmds.warning("Please select one or more edges.")
            return

        # Filter to edges only
        edges = cmds.filterExpand(sel, selectionMask=32)  # mask 32 = edges
        if not edges:
            cmds.warning("Selection must contain edges.")
            return

        # Determine degree and form (closed)
        smooth = cmds.checkBox(self.smooth_cb, query=True, value=True)
        degree = 3 if smooth else 1
        form = 1  # closed curve

        # Create curve from selected edges
        try:
            # polyToCurve will generate a degree-based, closed curve from the selected edges
            result = cmds.polyToCurve(form=form, degree=degree)
            # polyToCurve returns [curveTransform, curveShape]
            curve_transform = result[0] if isinstance(result, (list, tuple)) else result
            # Rename curve
            curve_name = cmds.rename(curve_transform, "edgeCurve#")
            # Center pivot on the newly created curve
            cmds.xform(curve_name, centerPivots=True)
            cmds.select(curve_name)
            cmds.inViewMessage(amg='Created closed curve <hl>%s</hl> with pivot centered.' % curve_name, pos='topCenter', fade=True)
        except Exception as e:
            cmds.error("Failed to create curve: %s" % e)

# Instantiate and display the tool
EdgeToCurveTool()
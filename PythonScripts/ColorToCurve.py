# changes the wireframe/shape color of the selection(s)

import maya.cmds as cmds


def SetColor(colorNum):
    colorNum = int(colorNum)

    if colorNum > 31 or colorNum < 0:
        colorNum = 0
        cmds.warning("Number must be between 0-31")

    selectedObjects = []
    selectedObjects = cmds.ls(selection = True)
    if len(selectedObjects) < 1:
        cmds.error("No objects selected")
    selectedShapes = []
    selectedShapes = cmds.listRelatives(selectedObjects, shapes = True)

    if len(selectedObjects) < 1:
        cmds.error("No shapes in selection")


    for shape in selectedShapes:
        cmds.setAttr((shape + ".overrideEnabled"), 1)
        cmds.setAttr((shape + ".overrideColor"), colorNum)

SetColor(2)
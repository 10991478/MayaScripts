import maya.cmds as cmds
import random


def SetColor(colorNum, makeRandom = False):
    if makeRandom == False:
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
        if makeRandom == True:
            colorNum = random.randint(0, 31)
        cmds.setAttr((shape + ".overrideEnabled"), 1)
        cmds.setAttr((shape + ".overrideColor"), colorNum)
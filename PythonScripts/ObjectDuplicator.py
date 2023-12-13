import maya.cmds as cmds
import random

def PlacementGenerator(numOfDupes, xMin, xMax, yMin, yMax, zMin, zMax):
    numOfDupes = int(numOfDupes)

    objectArray = cmds.ls(selection = True)

    temp = 0
    if xMin > xMax:
        temp = xMin
        xMin = xMax
        xMax = temp
    if yMin > yMax:
        temp = yMin
        yMin = yMax
        yMax = temp
    if zMin > zMax:
        temp = zMin
        zMin = zMax
        zMax = temp
    del temp

    for obj in objectArray:
        for i in range(numOfDupes):
            dups = cmds.duplicate(obj)
            dup = dups[0]

            xPos =  random.uniform(xMin, xMax)
            yPos =  random.uniform(yMin, yMax)
            zPos =  random.uniform(zMin, zMax)

            cmds.xform(dup, worldSpace = True, translation = [xPos, yPos, zPos])
import maya.cmds as cmds
import random

def PlacementGenerator(numOfDupes, xMin, xMax, yMin, yMax, zMin, zMax):
    numOfDupes = int(numOfDupes)

    objectArray = cmds.ls(selection = True)

    for obj in objectArray:
        for i in range(numOfDupes):
            dups = cmds.duplicate(obj)
            dup = dups[0]

            xPos =  random.randrange(xMin, xMax)
            yPos =  random.randrange(yMin, yMax)
            zPos =  random.randrange(zMin, zMax)

            cmds.xform(dup, worldSpace = True, translation = [xPos, yPos, zPos])

PlacementGenerator(20,1,10,1,10,1,10)
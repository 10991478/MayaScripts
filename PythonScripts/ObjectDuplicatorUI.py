import sys
path = "D:/GitHubStuff/University/MayaScripts/PythonScripts"

if path not in sys.path:
    sys.path.append(path)

import maya.cmds as cmds
import ObjectDuplicator as od
#import importlib
#importlib.reload(od)


class ObjectDuplicatorUI:
    mainWindow = "DuplicatorWindow"
    def __init__(self):
        pass
    
    def delete(self):
        if cmds.window(ObjectDuplicatorUI.mainWindow, exists = True):
            cmds.deleteUI(self.mainWindow)
    
    def duplicateObjects(self):
        dups = cmds.intField(self.numDups, q = True, value = True)
        xmin = cmds.floatField(self.xMin, q = True, value = True)
        xmax = cmds.floatField(self.xMax, q = True, value = True)
        ymin = cmds.floatField(self.yMin, q = True, value = True)
        ymax = cmds.floatField(self.yMax, q = True, value = True)
        zmin = cmds.floatField(self.zMin, q = True, value = True)
        zmax = cmds.floatField(self.zMax, q = True, value = True)
        od.PlacementGenerator(dups, xmin, xmax, ymin, ymax, zmin, zmax)


    def create(self):
        self.delete()
        ObjectDuplicatorUI.mainWindow = cmds.window(ObjectDuplicatorUI.mainWindow,
                                title = "Duplicator Tool")

        self.mainColumn = cmds.columnLayout(parent = ObjectDuplicatorUI.mainWindow)
        self.minRow = cmds.rowLayout(parent = self.mainColumn, numberOfColumns = 6)
        self.maxRow = cmds.rowLayout(parent = self.mainColumn, numberOfColumns = 6)
        self.numsAndRunRow = cmds.rowLayout(parent = self.mainColumn, numberOfColumns = 3)

        cmds.text("X Min" , parent = self.minRow)
        self.xMin = cmds.floatField(parent = self.minRow)
        cmds.text("Y Min" , parent = self.minRow)
        self.yMin = cmds.floatField(parent = self.minRow)
        cmds.text("Z Min" , parent = self.minRow)
        self.zMin = cmds.floatField(parent = self.minRow)
        
        cmds.text("X Max" , parent = self.maxRow)
        self.xMax = cmds.floatField(parent = self.maxRow)
        cmds.text("Y Max" , parent = self.maxRow)
        self.yMax = cmds.floatField(parent = self.maxRow)
        cmds.text("Z Max" , parent = self.maxRow)
        self.zMax = cmds.floatField(parent = self.maxRow)

        cmds.text("Number of Duplicates", parent = self.numsAndRunRow)
        self.numDups = cmds.intField(parent = self.numsAndRunRow)
        cmds.button("Run", parent = self.numsAndRunRow, command = lambda a: self.duplicateObjects())

    def show(self):
        cmds.showWindow(ObjectDuplicatorUI.mainWindow)
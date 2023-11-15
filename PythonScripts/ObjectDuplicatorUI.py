import maya.cmds as cmds
import ObjectDuplicator as od


class ObjectDuplicatorUI:
    def __init__(self):
        self.mainWindow = "Duplicator"
        self.mainColumn = ""
        self.minRow = ""
        self.maxRow = ""
        self.numsAndRunRow = ""
    
    def delete(self):
        if cmds.window(f"{self.mainWindow}Window", exists = True):
            cmds.deleteUI(f"{self.mainWindow}Window")
    

    def create(self):
        self.delete()
        self.mainWindow = cmds.window(f"{self.mainWindow}Window",
                                title = f"{self.mainWindow} Tool")

        self.mainColumn = cmds.columnLayout(parent = self.mainWindow)
        self.minRow = cmds.rowLayout(parent = self.mainColumn, numberOfColumns = 6)
        self.maxRow = cmds.rowLayout(parent = self.mainColumn, numberOfColumns = 6)
        self.numsAndRunRow = cmds.rowLayout(parent = self.mainColumn, numberOfColumns = 3)


    def show(self):
        cmds.showWindow(self.mainWindow)

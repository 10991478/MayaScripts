import sys
path = "D:/GitHubStuff/University/MayaScripts/PythonScripts"

if path not in sys.path:
    sys.path.append(path)

import maya.cmds as cmds
import ColorToCurve as ctc
#import importlib
#importlib.reload(ctc)


class ColorToCurveUI:
    mainWindow = "ColorWindow"
    def __init__(self):
        pass
    
    def delete(self):
        if cmds.window(ColorToCurveUI.mainWindow, exists = True):
            cmds.deleteUI(self.mainWindow)

    def create(self):
        self.delete()
        ColorToCurveUI.mainWindow = cmds.window(ColorToCurveUI.mainWindow,
                                title = "Duplicator Tool")

        self.mainColumn = cmds.columnLayout(parent = ColorToCurveUI.mainWindow)
        self.mainRow = cmds.rowLayout(parent = self.mainColumn, numberOfColumns = 4)

        self.isRandom = cmds.checkBox("Random Colors", parent = self.mainRow)
        cmds.text("Color Number", parent = self.mainRow)
        self.colorNum = cmds.intField(parent = self.mainRow, minValue = 0, maxValue = 31)
        cmds.button("Run", parent = self.mainRow, command = lambda a: self.setColors())

    def show(self):
        cmds.showWindow(ColorToCurveUI.mainWindow)

    def setColors(self):
        makeRandom = cmds.checkBox(self.isRandom, q = True, value = True)
        num = cmds.intField(self.colorNum, q = True, value = True)
        ctc.SetColor(num, makeRandom)
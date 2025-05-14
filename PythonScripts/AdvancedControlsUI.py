#Maya python script for advanced control curve creation and editing

import maya.cmds as cmds
import math

# ---------------------------------------
# Common Curve Shapes and Creation Methods
# ---------------------------------------
class BaseShape(object):
    """
    Base class for all curve shapes. Subclasses must implement create(name).
    """
    def create(self, name):
        raise NotImplementedError("Must implement create in subclass.")

class CircleShape(BaseShape):
    def create(self, name):
        curve, _ = cmds.circle(name=name, normal=(0,1,0))
        return curve

class SquareShape(BaseShape):
    def create(self, name):
        pts = [(-1,0,-1), (1,0,-1), (1,0,1), (-1,0,1), (-1,0,-1)]
        return cmds.curve(name=name, p=pts, degree=1)

class ArrowShape(BaseShape):
    def create(self, name):
        pts = [(0,0,1),(0.5,0,0),(0.2,0,0),(0.2,0,-1),(-0.2,0,-1),(-0.2,0,0),(-0.5,0,0),(0,0,1)]
        return cmds.curve(name=name, p=pts, degree=1)

class DiamondShape(BaseShape):
    def create(self, name):
        pts = [(0,0,1),(1,0,0),(0,0,-1),(-1,0,0),(0,0,1)]
        return cmds.curve(name=name, p=pts, degree=1)

class PlusShape(BaseShape):
    def create(self, name):
        w = 0.2
        l = 1.0
        pts = [(-w,-l,0), (w,-l,0), (w,-w,0), (l,-w,0), (l,w,0), (w,w,0),
               (w,l,0), (-w,l,0), (-w,w,0), (-l,w,0), (-l,-w,0), (-w,-w,0),
               (-w,-l,0)]
        return cmds.curve(name=name, p=pts, degree=1)

class GearShape(BaseShape):
    def create(self, name):
        # A simple cog with paired teeth (two points per outer/inner alternation)
        teeth = 16
        r_outer = 1.0
        r_inner = 0.7
        pts = []
        total = teeth * 2
        for i in range(total + 1):
            angle = (math.pi * 2) * (i / float(total))
            group = i // 2
            r = r_outer if (group % 2 == 0) else r_inner
            x = r * math.cos(angle)
            z = r * math.sin(angle)
            pts.append((x, 0, z))
        return cmds.curve(name=name, p=pts, degree=1)

class StarburstShape(BaseShape):
    def create(self, name):
        spikes = 8; r_spike = 1.0; r_base = 0.6
        pts = []
        for i in range(spikes*2+1):
            angle = (math.pi*2)*(i/float(spikes*2))
            r = r_spike if i%2==0 else r_base
            pts.append((r*math.cos(angle),0,r*math.sin(angle)))
        return cmds.curve(name=name, p=pts, degree=1)

# -------------------------------------------------
# Control Manager with Color Support
# -------------------------------------------------
class ControlManager(object):
    def __init__(self):
        self.shapes = {
            'Circle': CircleShape(), 'Square': SquareShape(), 'Arrow': ArrowShape(),
            'Diamond': DiamondShape(), 'Plus': PlusShape(), 'Gear': GearShape(),
            'Starburst': StarburstShape(),
        }

    def create_control(self, shape_name, ctrl_name, target=None, color=None):
        shape = self.shapes.get(shape_name)
        if not shape:
            cmds.error("Shape '%s' not found." % shape_name)
        ctrl = shape.create(ctrl_name)
        if target:
            cmds.matchTransform(ctrl, target, pos=True, rot=True, scl=False)
        cmds.makeIdentity(ctrl, apply=True, t=1, r=1, s=1)
        if color is not None:
            self._apply_color(ctrl, color)
        return ctrl

    def _apply_color(self, ctrl, color):
        shapes = cmds.listRelatives(ctrl, shapes=True, fullPath=True) or []
        for shp in shapes:
            cmds.setAttr(f"{shp}.overrideEnabled", 1)
            cmds.setAttr(f"{shp}.overrideColor", color)

    def create_controls_for_selection(self, shape_name, prefix, suffix, replace_str, with_str, color=None):
        sel = cmds.ls(selection=True, type='transform', long=True)
        if not sel:
            cmds.warning("No objects selected.")
            return
        for obj in sel:
            base = obj.split('|')[-1]
            if replace_str:
                base = base.replace(replace_str, with_str)
            name = prefix + base + suffix
            grp = cmds.group(empty=True, name=name+'_Grp')
            cmds.matchTransform(grp, obj, pos=True, rot=True, scl=False)
            ctrl = self.create_control(shape_name, name, target=obj, color=color)
            cmds.parent(ctrl, grp)
            cmds.makeIdentity(ctrl, apply=True, t=1, r=1, s=1)
            cmds.select(clear=True)

    def create_controls_by_number(self, shape_name, number, color=None):
        for i in range(1, number+1):
            name = f"{shape_name}{i}"
            grp = cmds.group(empty=True, name=name+'_Grp')
            ctrl = self.create_control(shape_name, name, color=color)
            cmds.parent(ctrl, grp)
            cmds.makeIdentity(ctrl, apply=True, t=1, r=1, s=1)
            cmds.select(clear=True)

    def replace_controls(self, shape_name, prefix, suffix, replace_str, with_str, color=None):
        sel = cmds.ls(selection=True, type='transform', long=True)
        if not sel:
            cmds.warning("No objects selected for replacement.")
            return
        for obj in sel:
            if cmds.nodeType(obj) == 'joint': continue
            parent = cmds.listRelatives(obj, parent=True, fullPath=True)
            children = cmds.listRelatives(obj, children=True, type='transform', fullPath=True) or []
            short_old = obj.split('|')[-1]; temp_name = short_old+'_tmp'
            new_ctrl = self.create_control(shape_name, temp_name, color=color)
            cmds.matchTransform(new_ctrl, obj, pos=True, rot=True, scl=False)
            if parent: cmds.parent(new_ctrl, parent[0])
            for child in children: cmds.parent(child, new_ctrl)
            cmds.delete(obj); cmds.rename(new_ctrl, short_old)
            if color is not None: self._apply_color(short_old, color)

# -----------------------------
# UI Definition with Color Picker
# -----------------------------
class ControlUI(object):
    WINDOW = "controlReplaceWindow"

    def __init__(self):
        self.ctrl_mgr = ControlManager()
        if cmds.window(ControlUI.WINDOW, exists=True):
            cmds.deleteUI(ControlUI.WINDOW)
        self.build()

    def build(self):
        self.win = cmds.window(ControlUI.WINDOW, title="Curve Control Creator/Replacer", widthHeight=(340,300))
        cmds.columnLayout(adjustableColumn=True)

        # Shape dropdown
        cmds.text(label="Shape:")
        self.shape_menu = cmds.optionMenu()
        for name in self.ctrl_mgr.shapes.keys(): cmds.menuItem(label=name)

        # Naming inputs
        cmds.separator(height=10)
        cmds.text(label="Naming:")
        cmds.rowLayout(numberOfColumns=4, columnWidth4=(60,60,60,60))
        cmds.text(label="Replace"); self.replace_field = cmds.textField(text="_Jnt")
        cmds.text(label="With");    self.with_field    = cmds.textField(text="_Ctrl")
        cmds.setParent('..')
        cmds.rowLayout(numberOfColumns=4, columnWidth4=(60,60,60,60))
        cmds.text(label="Prefix");  self.prefix_field = cmds.textField()
        cmds.text(label="Suffix");  self.suffix_field = cmds.textField()
        cmds.setParent('..')

        # Color Settings with Picker
        cmds.separator(height=10)
        cmds.text(label="Color Index (0-31):")
        self.color_slider = cmds.colorIndexSliderGrp(label='Pick Color:', min=0, max=31, value=17)
        cmds.button(label="Change Color", command=self.on_change_color)

        # Create/Replace buttons
        cmds.separator(height=10)
        cmds.rowLayout(numberOfColumns=3, columnWidth3=(150,60,60))
        cmds.button(label="Create Controls", command=self.on_create)
        self.number_field = cmds.intField(value=1)
        cmds.button(label="Replace Controls", command=self.on_replace)
        cmds.setParent('..')

        cmds.showWindow(self.win)

    def _get_color_index(self):
        picked = cmds.colorIndexSliderGrp(self.color_slider, query=True, value=True)
        return max(0, picked - 1)

    def on_change_color(self, *args):
        color = self._get_color_index()
        sel = cmds.ls(selection=True, type='transform', long=True)
        if not sel:
            cmds.warning("No objects selected to change color.")
            return
        for obj in sel:
            shapes = cmds.listRelatives(obj, shapes=True, fullPath=True) or []
            for shp in shapes:
                cmds.setAttr(f"{shp}.overrideEnabled", 1)
                cmds.setAttr(f"{shp}.overrideColor", color)

    def on_create(self, *args):
        shape       = cmds.optionMenu(self.shape_menu, query=True, value=True)
        replace_str = cmds.textField(self.replace_field, query=True, text=True)
        with_str    = cmds.textField(self.with_field, query=True, text=True)
        prefix      = cmds.textField(self.prefix_field, query=True, text=True)
        suffix      = cmds.textField(self.suffix_field, query=True, text=True)
        color       = self._get_color_index()
        sel         = cmds.ls(selection=True, type='transform', long=True)
        if sel:
            self.ctrl_mgr.create_controls_for_selection(shape, prefix, suffix, replace_str, with_str, color)
        else:
            num = cmds.intField(self.number_field, query=True, value=True)
            self.ctrl_mgr.create_controls_by_number(shape, num, color)

    def on_replace(self, *args):
        shape       = cmds.optionMenu(self.shape_menu, query=True, value=True)
        replace_str = cmds.textField(self.replace_field, query=True, text=True)
        with_str    = cmds.textField(self.with_field, query=True, text=True)
        prefix      = cmds.textField(self.prefix_field, query=True, text=True)
        suffix      = cmds.textField(self.suffix_field, query=True, text=True)
        color       = self._get_color_index()
        self.ctrl_mgr.replace_controls(shape, prefix, suffix, replace_str, with_str, color)

# Run the UI
if __name__ == '__main__':
    ControlUI()
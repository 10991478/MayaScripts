import maya.cmds as cmds

WINDOW = "shapeBuilderUI"


def build_ui():
    if cmds.window(WINDOW, exists=True):
        cmds.deleteUI(WINDOW)
    cmds.window(WINDOW, title="BaseShape Class Builder", widthHeight=(450,350))
    cmds.columnLayout(adjustableColumn=True, rowSpacing=8, columnAlign="left")

    cmds.text(label="Class Name:")
    class_field = cmds.textField("bsClassName", text="MyShape")

    cmds.rowLayout(numberOfColumns=2, columnWidth2=(200,200), adjustableColumn=2)
    smooth_cb = cmds.checkBox("bsSmooth", label="Smooth (degree=3)")
    closed_cb = cmds.checkBox("bsClosed", label="Closed Loop")
    cmds.setParent('..')

    cmds.button(label="Generate Class",
                command=lambda *args: generate_class(class_field, smooth_cb, closed_cb))
    cmds.separator(height=10)

    cmds.text(label="Generated Class:")
    cmds.scrollField("bsOutput", editable=False, wordWrap=True, height=200)

    cmds.showWindow(WINDOW)


def generate_class(class_field, smooth_cb, closed_cb):
    # Read UI values
    cls_name = cmds.textField(class_field, query=True, text=True).strip() or "NewShape"
    degree   = 3 if cmds.checkBox(smooth_cb, query=True, value=True) else 1
    closed   = cmds.checkBox(closed_cb, query=True, value=True)

    # Identify selected curve transform
    sel = cmds.ls(selection=True, long=True) or []
    curve = None
    for obj in sel:
        if cmds.nodeType(obj) in ("nurbsCurve", "nurbsSurface"):
            curve = cmds.listRelatives(obj, parent=True, fullPath=True)[0]
            break
        if cmds.nodeType(obj) == "transform":
            shapes = cmds.listRelatives(obj, shapes=True, fullPath=True) or []
            if shapes and cmds.nodeType(shapes[0]) == "nurbsCurve":
                curve = obj
                break
    if not curve:
        cmds.warning("Please select a NURBS curve or its transform.")
        return

    # Gather world-space CV positions
    shp = cmds.listRelatives(curve, shapes=True, fullPath=True)[0]
    num_cvs = cmds.getAttr(f"{shp}.controlPoints", size=True)
    pts = []
    for i in range(num_cvs - 1):
        x, y, z = cmds.xform(f"{shp}.cv[{i}]", q=True, ws=True, translation=True)
        pts.append((x, y, z))
    # If closed loop and last pt repeats first, drop duplicate
    if pts[len(pts)-1] == pts[len(pts)-2] == pts[len(pts)-3]:
        pts = pts[:-1]
        pts = pts[:-1]

    pts_lines = [f"        ({x:.4f}, {y:.4f}, {z:.4f})," for x, y, z in pts]

    # Assemble class definition
    lines = [
        f"class {cls_name}(BaseShape):",
        f"    \"\"\"Auto-generated from curve '{curve}'.\"\"\"\n",
        f"    def create(self, name):",
        f"        # CV positions (world-space)",
        f"        pts = ["
    ] + pts_lines + [
        f"        ]",
        f"        # create open curve",
        f"        crv = cmds.curve(name=name, p=pts, degree={degree})"
    ]

    if closed:
        lines += [
            f"        # close it into a periodic curve",
            f"        crv = cmds.closeCurve(crv, ch=False, replaceOriginal=True)"
        ]

    lines.append(f"        return crv")

    result = "\n".join(lines)
    cmds.scrollField("bsOutput", edit=True, text=result)


# Run the UI
if __name__ == "__main__":
    build_ui()

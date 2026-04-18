#Script for setting up the special render passes for Work Day short film

import maya.cmds as cmds

WINDOW_NAME = "specialPassSetupUI"

PASS_MATERIALS = {
    "SmallNoise": "ExtraRenderPasses:SmallNoiseMat",
    "BigNoise": "ExtraRenderPasses:BigNoiseMat",
    "FacingRatio": "ExtraRenderPasses:FacingRatioMat",
    "Curvature": "ExtraRenderPasses:CurvatureMat",
}

SKELLY_ALPHA_BLACK = "ExtraRenderPasses:FlatBlackMat"
SKELLY_ALPHA_WHITE = "ExtraRenderPasses:FlatWhiteMat"
SKELLY_ALPHA_OBJECT = "Skeleton:Skeleton_Asset"


# ----------------------------
# helpers
# ----------------------------

def _set_attr_if_exists(node_attr, value, attr_type=None):
    """Set an attribute only if it exists."""
    node, attr = node_attr.split(".", 1)
    if not cmds.objExists(node):
        return False
    if not cmds.attributeQuery(attr, node=node, exists=True):
        return False
    try:
        if attr_type is None:
            cmds.setAttr(node_attr, value)
        else:
            cmds.setAttr(node_attr, value, type=attr_type)
        return True
    except Exception:
        return False


def _ensure_arnold_loaded():
    """Load Arnold if possible."""
    try:
        if not cmds.pluginInfo("mtoa", q=True, loaded=True):
            cmds.loadPlugin("mtoa")
    except Exception:
        pass


def _set_render_version(version_name):
    """
    Try to populate Maya's version-related render setting if it exists.
    Different Maya installs/projects can expose slightly different attr names,
    so this tries a few common possibilities.
    """
    candidates = [
        "defaultRenderGlobals.versionName",
        "defaultRenderGlobals.version",
        "defaultRenderGlobals.renderVersion",
        "defaultRenderGlobals.fileVersion",
    ]

    for attr in candidates:
        _set_attr_if_exists(attr, version_name, attr_type="string")


def _get_material_shading_group(material):
    """Return the shadingEngine connected to a material, or create one if needed."""
    if not cmds.objExists(material):
        return None

    sgs = cmds.listConnections(material, type="shadingEngine") or []
    for sg in sgs:
        if sg != "initialShadingGroup":
            return sg

    # Create a shading group if none is connected.
    safe_name = material.split(":")[-1] + "_SG"
    sg = cmds.sets(renderable=True, noSurfaceShader=True, empty=True, name=safe_name)

    # Connect material.outColor -> shadingEngine.surfaceShader if possible
    try:
        if cmds.attributeQuery("outColor", node=material, exists=True):
            cmds.connectAttr(material + ".outColor", sg + ".surfaceShader", force=True)
    except Exception:
        pass

    return sg


def _get_all_renderable_mesh_transforms():
    """Return unique transforms that own non-intermediate mesh shapes."""
    shapes = cmds.ls(type="mesh", long=True, noIntermediate=True) or []
    transforms = []
    seen = set()

    for shape in shapes:
        parents = cmds.listRelatives(shape, parent=True, fullPath=True) or []
        for tr in parents:
            if tr not in seen:
                seen.add(tr)
                transforms.append(tr)

    return transforms


def _assign_material_to_nodes(nodes, material):
    """Assign a material to a list of transforms."""
    sg = _get_material_shading_group(material)
    if not sg:
        cmds.warning('Material not found: "{}"'.format(material))
        return

    if not nodes:
        cmds.warning("No mesh transforms found in scene.")
        return

    try:
        cmds.sets(nodes, e=True, forceElement=sg)
    except Exception as e:
        cmds.warning('Could not assign "{}": {}'.format(material, e))


def _assign_material_to_object(obj_name, material):
    """Assign a material to an object and all its mesh shapes."""
    if not cmds.objExists(obj_name):
        cmds.warning('Object not found: "{}"'.format(obj_name))
        return

    sg = _get_material_shading_group(material)
    if not sg:
        cmds.warning('Material not found: "{}"'.format(material))
        return

    targets = []

    # If the object is a transform, use the transform.
    if cmds.nodeType(obj_name) == "transform":
        targets.append(obj_name)

    # Also include any mesh shapes under it.
    shapes = cmds.listRelatives(obj_name, shapes=True, fullPath=True) or []
    for s in shapes:
        if cmds.nodeType(s) == "mesh":
            parents = cmds.listRelatives(s, parent=True, fullPath=True) or []
            targets.extend(parents or [s])

    targets = list(dict.fromkeys(targets))  # preserve order, remove duplicates

    if not targets:
        cmds.warning('No assignable mesh found under "{}".'.format(obj_name))
        return

    try:
        cmds.sets(targets, e=True, forceElement=sg)
    except Exception as e:
        cmds.warning('Could not assign "{}" to "{}": {}'.format(material, obj_name, e))


# ----------------------------
# setup actions
# ----------------------------

def setup_general_render_settings(*_):
    _ensure_arnold_loaded()

    # File name prefix
    _set_attr_if_exists("defaultRenderGlobals.imageFilePrefix",
                        "<Scene>/<Version>/<Scene>_<Version>",
                        attr_type="string")

    # Frame / animation extension settings
    _set_attr_if_exists("defaultRenderGlobals.animation", 1)
    _set_attr_if_exists("defaultRenderGlobals.putFrameBeforeExt", 1)
    _set_attr_if_exists("defaultRenderGlobals.extensionPadding", 4)

    # Image size: HD_1080
    _set_attr_if_exists("defaultResolution.width", 1920)
    _set_attr_if_exists("defaultResolution.height", 1080)
    _set_attr_if_exists("defaultResolution.pixelAspect", 1.0)
    _set_attr_if_exists("defaultResolution.deviceAspectRatio", 1920.0 / 1080.0)

    # Arnold output format
    if cmds.objExists("defaultArnoldDriver"):
        _set_attr_if_exists("defaultArnoldDriver.ai_translator", "exr", attr_type="string")

    cmds.inViewMessage(amg="General render settings applied.", pos="topCenter", fade=True)


def setup_pass(pass_name, material_name, *_):
    # Keep the version in sync with the pass name
    _set_render_version(pass_name)

    # Assign the requested material to all meshes
    meshes = _get_all_renderable_mesh_transforms()
    _assign_material_to_nodes(meshes, material_name)

    cmds.inViewMessage(
        amg='Pass "{}" applied.'.format(pass_name),
        pos="topCenter",
        fade=True
    )


def setup_skelly_alpha(*_):
    _set_render_version("SkellyAlpha")

    # All meshes black...
    meshes = _get_all_renderable_mesh_transforms()
    _assign_material_to_nodes(meshes, SKELLY_ALPHA_BLACK)

    # ...except the skeleton object, which is white.
    _assign_material_to_object(SKELLY_ALPHA_OBJECT, SKELLY_ALPHA_WHITE)

    cmds.inViewMessage(amg='Pass "SkellyAlpha" applied.', pos="topCenter", fade=True)


# ----------------------------
# UI
# ----------------------------

def show_special_pass_setup_ui():
    if cmds.window(WINDOW_NAME, exists=True):
        cmds.deleteUI(WINDOW_NAME)

    cmds.window(
        WINDOW_NAME,
        title="Special Pass Setup",
        sizeable=True,
        widthHeight=(380, 320)
    )

    cmds.columnLayout(adjustableColumn=True, rowSpacing=8, columnAlign="center")

    cmds.text(label="Render setup tools", align="center", height=24)

    cmds.button(
        label="General Render Settings Setup",
        height=35,
        command=setup_general_render_settings
    )

    cmds.separator(height=10, style="in")

    cmds.button(
        label="SmallNoise",
        height=30,
        command=lambda *_: setup_pass("SmallNoise", PASS_MATERIALS["SmallNoise"])
    )
    cmds.button(
        label="BigNoise",
        height=30,
        command=lambda *_: setup_pass("BigNoise", PASS_MATERIALS["BigNoise"])
    )
    cmds.button(
        label="FacingRatio",
        height=30,
        command=lambda *_: setup_pass("FacingRatio", PASS_MATERIALS["FacingRatio"])
    )
    cmds.button(
        label="Curvature",
        height=30,
        command=lambda *_: setup_pass("Curvature", PASS_MATERIALS["Curvature"])
    )
    cmds.button(
        label="SkellyAlpha",
        height=30,
        command=setup_skelly_alpha
    )

    cmds.separator(height=10, style="none")
    cmds.text(label="SkellyAlpha uses FlatBlackMat + FlatWhiteMat.", align="center")

    cmds.showWindow(WINDOW_NAME)


show_special_pass_setup_ui()
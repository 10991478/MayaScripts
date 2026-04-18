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
    try:
        if not cmds.pluginInfo("mtoa", q=True, loaded=True):
            cmds.loadPlugin("mtoa")
    except Exception:
        pass


def _set_render_version(version_name):
    candidates = [
        "defaultRenderGlobals.versionName",
        "defaultRenderGlobals.version",
        "defaultRenderGlobals.renderVersion",
        "defaultRenderGlobals.fileVersion",
    ]

    for attr in candidates:
        _set_attr_if_exists(attr, version_name, attr_type="string")


def _get_material_shading_group(material):
    if not cmds.objExists(material):
        return None

    sgs = cmds.listConnections(material, type="shadingEngine") or []
    for sg in sgs:
        if sg != "initialShadingGroup":
            return sg

    safe_name = material.split(":")[-1] + "_SG"
    sg = cmds.sets(renderable=True, noSurfaceShader=True, empty=True, name=safe_name)

    try:
        if cmds.attributeQuery("outColor", node=material, exists=True):
            cmds.connectAttr(material + ".outColor", sg + ".surfaceShader", force=True)
    except Exception:
        pass

    return sg


def _get_all_renderable_mesh_transforms():
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
    if not cmds.objExists(obj_name):
        cmds.warning('Object not found: "{}"'.format(obj_name))
        return

    sg = _get_material_shading_group(material)
    if not sg:
        cmds.warning('Material not found: "{}"'.format(material))
        return

    targets = []

    if cmds.nodeType(obj_name) == "transform":
        targets.append(obj_name)

    shapes = cmds.listRelatives(obj_name, shapes=True, fullPath=True) or []
    for s in shapes:
        if cmds.nodeType(s) == "mesh":
            parents = cmds.listRelatives(s, parent=True, fullPath=True) or []
            targets.extend(parents or [s])

    targets = list(dict.fromkeys(targets))

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

    _set_attr_if_exists(
        "defaultRenderGlobals.imageFilePrefix",
        "<Scene>/<Version>/<Scene>_<Version>",
        attr_type="string"
    )

    _set_attr_if_exists("defaultRenderGlobals.animation", 1)
    _set_attr_if_exists("defaultRenderGlobals.putFrameBeforeExt", 1)
    _set_attr_if_exists("defaultRenderGlobals.extensionPadding", 4)

    _set_attr_if_exists("defaultResolution.width", 1920)
    _set_attr_if_exists("defaultResolution.height", 1080)
    _set_attr_if_exists("defaultResolution.pixelAspect", 1.0)
    _set_attr_if_exists("defaultResolution.deviceAspectRatio", 1920.0 / 1080.0)

    if cmds.objExists("defaultArnoldDriver"):
        _set_attr_if_exists("defaultArnoldDriver.ai_translator", "exr", attr_type="string")

    # Frame rate: 12 fps
    # Maya often uses time unit names like "12fps" here.
    try:
        cmds.currentUnit(time="12fps")
    except Exception:
        cmds.warning("Could not set timeline frame rate to 12 fps.")

    cmds.inViewMessage(amg="General render settings applied.", pos="topCenter", fade=True)


def set_frame_range_from_timeline(*_):
    """
    Sets the render range to match the current playback range shown in the Time Slider.
    """
    try:
        start = cmds.playbackOptions(q=True, minTime=True)
        end = cmds.playbackOptions(q=True, maxTime=True)

        _set_attr_if_exists("defaultRenderGlobals.startFrame", start)
        _set_attr_if_exists("defaultRenderGlobals.endFrame", end)

        cmds.inViewMessage(
            amg="Render frame range set to {} - {}.".format(start, end),
            pos="topCenter",
            fade=True
        )
    except Exception as e:
        cmds.warning("Could not set frame range from Time Slider: {}".format(e))

def set_render_camera_from_view(*_):
    """
    Sets the renderable camera to the camera currently active in the focused model panel.
    Makes sure only that camera is renderable.
    """
    panel = cmds.getPanel(withFocus=True)

    if not panel or not cmds.getPanel(typeOf=panel) == "modelPanel":
        cmds.warning("Focus a viewport first, then press Set Render Camera.")
        return

    try:
        cam = cmds.modelEditor(panel, q=True, camera=True)
    except Exception as e:
        cmds.warning("Could not query active camera: {}".format(e))
        return

    if not cam or not cmds.objExists(cam):
        cmds.warning("No valid camera found in the active viewport.")
        return

    # modelEditor can return either the transform or the shape; normalize to both.
    cam_shape = cam
    cam_transform = cam

    if cmds.nodeType(cam) == "camera":
        parents = cmds.listRelatives(cam, parent=True, fullPath=True) or []
        cam_shape = cam
        cam_transform = parents[0] if parents else None
    else:
        shapes = cmds.listRelatives(cam, shapes=True, fullPath=True, type="camera") or []
        if shapes:
            cam_shape = shapes[0]
        cam_transform = cam

    # Turn off renderable on all cameras first
    for shape in cmds.ls(type="camera", long=True) or []:
        try:
            cmds.setAttr(shape + ".renderable", 0)
        except Exception:
            pass

    # Turn on only the active one
    target_shape = cam_shape if cmds.nodeType(cam_shape) == "camera" else None
    if not target_shape and cam_transform:
        shapes = cmds.listRelatives(cam_transform, shapes=True, fullPath=True, type="camera") or []
        target_shape = shapes[0] if shapes else None

    if not target_shape or not cmds.objExists(target_shape):
        cmds.warning("Could not resolve the render camera shape.")
        return

    try:
        cmds.setAttr(target_shape + ".renderable", 1)
        cmds.inViewMessage(
            amg='Render camera set to "{}".'.format(target_shape),
            pos="topCenter",
            fade=True
        )
    except Exception as e:
        cmds.warning("Could not set renderable camera: {}".format(e))


def setup_pass(pass_name, material_name, *_):
    _set_render_version(pass_name)

    meshes = _get_all_renderable_mesh_transforms()
    _assign_material_to_nodes(meshes, material_name)

    cmds.inViewMessage(
        amg='Pass "{}" applied.'.format(pass_name),
        pos="topCenter",
        fade=True
    )


def setup_skelly_alpha(*_):
    _set_render_version("SkellyAlpha")

    meshes = _get_all_renderable_mesh_transforms()
    _assign_material_to_nodes(meshes, SKELLY_ALPHA_BLACK)

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

    cmds.button(
        label="Set Frame Range",
        height=30,
        command=set_frame_range_from_timeline
    )

    cmds.button(
        label="Set Render Camera",
        height=30,
        command=set_render_camera_from_view
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
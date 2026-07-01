#Singularizes skin weights for each different shell (NOT UNDOABLE)

import maya.cmds as cmds
import maya.api.OpenMaya as om
import maya.api.OpenMayaAnim as oma

WINDOW_NAME = "SingularizeSkinWeightsWindow"

# -------------------------------------------------------
# Shell Detection
# -------------------------------------------------------

def get_vertex_shells_from_selected_faces():
    """
    Returns a list of vertex arrays, one array per connected shell
    contained within the current face selection.
    """

    original_faces = cmds.ls(sl=True, fl=True)

    if not original_faces:
        cmds.error("Please select some faces.")

    mesh = original_faces[0].split(".")[0]

    remaining_faces = set(original_faces)
    vertex_shells = []

    while remaining_faces:

        # Pick one remaining face
        seed_face = next(iter(remaining_faces))
        face_index = int(seed_face.split("[")[-1][:-1])

        # Select the shell containing this face
        cmds.select(clear=True)
        cmds.polySelect(mesh, extendToShell=face_index)

        shell_faces = cmds.ls(sl=True, fl=True)

        # Only keep faces that were originally selected
        shell_faces = [
            f for f in shell_faces
            if f in remaining_faces
        ]

        if not shell_faces:
            remaining_faces.remove(seed_face)
            continue

        # Convert shell to vertices
        verts = cmds.polyListComponentConversion(
            shell_faces,
            fromFace=True,
            toVertex=True
        )

        verts = cmds.ls(verts, fl=True)

        vertex_shells.append(verts)

        # Remove processed faces
        remaining_faces.difference_update(shell_faces)

    # Restore original selection
    cmds.select(original_faces, r=True)

    return vertex_shells


# -------------------------------------------------------
# Utilities
# -------------------------------------------------------

def getDagPath(node):
    sel = om.MSelectionList()
    sel.add(node)
    return sel.getDagPath(0)


def getDependNode(node):
    sel = om.MSelectionList()
    sel.add(node)
    return sel.getDependNode(0)


def getSkinCluster(mesh):

    history = cmds.listHistory(mesh, pruneDagObjects=True) or []

    skins = cmds.ls(history, type="skinCluster")

    if not skins:
        return None

    return skins[0]


# -------------------------------------------------------
# Main
# -------------------------------------------------------

def singularizeSkinWeights(*args):

    originalSelection = cmds.ls(sl=True, fl=True)

    if not originalSelection:
        cmds.warning("Please select some mesh faces.")
        return

    cmds.undoInfo(openChunk=True)

    try:

        faces = originalSelection
        mesh = faces[0].split(".")[0]

        skinCluster = getSkinCluster(mesh)

        if not skinCluster:
            cmds.warning("No skinCluster found.")
            return

        # NEW: Build vertex shell arrays
        vertex_shells = get_vertex_shells_from_selected_faces()

        meshDag = getDagPath(mesh)
        fnSkin = oma.MFnSkinCluster(getDependNode(skinCluster))
        influencePaths = fnSkin.influenceObjects()

        for verts in vertex_shells:

            if not verts:
                continue

            vertexIDs = [
                int(v.split("[")[-1][:-1])
                for v in verts
            ]

            fnComponent = om.MFnSingleIndexedComponent()
            component = fnComponent.create(
                om.MFn.kMeshVertComponent
            )
            fnComponent.addElements(vertexIDs)

            weights, influenceCount = fnSkin.getWeights(
                meshDag,
                component
            )

            influenceTotals = [0.0] * influenceCount

            idx = 0

            for v in range(len(vertexIDs)):
                for inf in range(influenceCount):
                    influenceTotals[inf] += weights[idx]
                    idx += 1

            dominantInfluence = max(
                range(influenceCount),
                key=lambda i: influenceTotals[i]
            )

            dominantJoint = influencePaths[
                dominantInfluence
            ].partialPathName()

            print(
                "Shell -> Dominant Joint:",
                dominantJoint
            )

            newWeights = om.MDoubleArray()

            for v in range(len(vertexIDs)):
                for inf in range(influenceCount):
                    newWeights.append(
                        1.0 if inf == dominantInfluence else 0.0
                    )

            influenceIndices = om.MIntArray(
                range(influenceCount)
            )

            cmds.dgeval(mesh)

            fnSkin.setWeights(
                meshDag,
                component,
                influenceIndices,
                newWeights,
                True,
                returnOldWeights=True
            )

        cmds.refresh()

        cmds.select(originalSelection, r=True)

        cmds.inViewMessage(
            amg="Singularized <hl>%d</hl> shell(s)." %
            len(vertex_shells),
            pos="midCenter",
            fade=True
        )

    finally:

        cmds.undoInfo(closeChunk=True)

# -------------------------------------------------------
# UI
# -------------------------------------------------------

def createUI():

    if cmds.window(WINDOW_NAME, exists=True):
        cmds.deleteUI(WINDOW_NAME)

    cmds.window(
        WINDOW_NAME,
        title="Singularize Skin Weights",
        sizeable=True,
        widthHeight=(320, 90)
    )

    cmds.columnLayout(adj=True)

    cmds.button(
        label="Singularize Skin Weights",
        height=50,
        command=singularizeSkinWeights
    )

    cmds.showWindow()


createUI()
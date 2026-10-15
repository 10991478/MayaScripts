#Helps to place PV control for spring solver systems

import maya.cmds as cmds
import math

WINDOW_NAME = "SpringSolverPVLocatorWindow"

AXIS_MAP = {
    "+X": (1, 0, 0), "-X": (-1, 0, 0),
    "+Y": (0, 1, 0), "-Y": (0, -1, 0),
    "+Z": (0, 0, 1), "-Z": (0, 0, -1)
}

AXIS_ABS = {
    "+X": (1, 0, 0), "-X": (1, 0, 0),
    "+Y": (0, 1, 0), "-Y": (0, 1, 0),
    "+Z": (0, 0, 1), "-Z": (0, 0, 1)
}


# --------------------------------------------------
# Vector helpers
# --------------------------------------------------

def vec_sub(a, b):
    return [a[i] - b[i] for i in range(3)]


def vec_add(a, b):
    return [a[i] + b[i] for i in range(3)]


def vec_mul(a, s):
    return [a[i] * s for i in range(3)]


def vec_dot(a, b):
    return sum(a[i] * b[i] for i in range(3))


def vec_length(a):
    return math.sqrt(vec_dot(a, a))


def vec_normalize(a):
    length = vec_length(a)
    if length < 1e-12:
        return [0.0, 0.0, 0.0]
    return [a[i] / length for i in range(3)]


def vec_cross(a, b):
    return [
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0]
    ]


def get_world_position(obj):
    return cmds.xform(obj, query=True, worldSpace=True, translation=True)


# --------------------------------------------------
# Warnings
# --------------------------------------------------

def show_warning(message):
    cmds.warning(message)
    cmds.confirmDialog(
        title="Spring Solver PV Locator",
        message=message,
        button=["OK"],
        defaultButton="OK"
    )


# --------------------------------------------------
# IK handle / spring solver validation
# --------------------------------------------------

def get_spring_solver_data(handle):
    if not cmds.objExists(handle):
        raise RuntimeError("The selected IK handle does not exist.")

    if cmds.nodeType(handle) != "ikHandle":
        raise RuntimeError(
            "Please select an IK handle in the Outliner."
        )

    # Query the solver type.
    solver_type = cmds.ikHandle(
        handle, query=True, solver=True
    )

    if not solver_type or "spring" not in solver_type.lower():
        raise RuntimeError(
            "The selected IK handle does not use an IK Spring Solver."
        )

    # Retrieve the start joint.
    start_joint = cmds.ikHandle(
        handle, query=True, startJoint=True
    )

    # Retrieve the end effector and find its parent joint.
    end_effector = cmds.ikHandle(
        handle, query=True, endEffector=True
    )

    if isinstance(end_effector, (list, tuple)):
        end_effector = end_effector[0] if end_effector else None

    end_joint = None

    if end_effector and cmds.objExists(end_effector):
        parents = cmds.listRelatives(
            end_effector, parent=True, type="joint"
        ) or []

        if parents:
            end_joint = parents[0]

    if not start_joint or not end_joint:
        raise RuntimeError(
            "Could not identify both the start and end joints."
        )

    # Read the spring solver's pole vector values.
    # Maya versions/scenes may expose these differently.
    pole_vector = None

    # First try the compound attribute on the IK handle.
    for node in [handle]:
        if cmds.attributeQuery(
            "poleVector", node=node, exists=True
        ):
            try:
                value = cmds.getAttr(node + ".poleVector")
                if value:
                    if (
                        isinstance(value, (list, tuple))
                        and len(value) == 1
                        and isinstance(value[0], (list, tuple))
                    ):
                        value = value[0]

                    if len(value) >= 3:
                        pole_vector = [
                            float(value[0]),
                            float(value[1]),
                            float(value[2])
                        ]
                        break
            except Exception:
                pass

        # Try separate X/Y/Z attributes.
        if all(
            cmds.attributeQuery(
                "poleVector" + axis, node=node, exists=True
            )
            for axis in "XYZ"
        ):
            pole_vector = [
                cmds.getAttr(node + ".poleVector" + axis)
                for axis in "XYZ"
            ]
            break

    if pole_vector is None:
        raise RuntimeError(
            "Could not read the pole vector values from the IK handle. "
            "Please verify which node owns the pole vector attributes "
            "in your Maya version."
        )

    return start_joint, end_joint, pole_vector


# --------------------------------------------------
# Temporary joint utilities
# --------------------------------------------------

def create_temp_joint(name, position):
    joint = cmds.createNode("joint", name=name)

    cmds.setAttr(joint + ".translate", 0, 0, 0, type="double3")
    cmds.setAttr(joint + ".rotate", 0, 0, 0, type="double3")
    cmds.setAttr(joint + ".jointOrient", 0, 0, 0, type="double3")

    cmds.xform(joint, worldSpace=True, translation=position)

    cmds.setAttr(joint + ".rotate", 0, 0, 0, type="double3")
    cmds.setAttr(joint + ".jointOrient", 0, 0, 0, type="double3")

    return joint


# --------------------------------------------------
# Orient the temporary three-joint chain
# Based on OrientJoints_Improved.py
# --------------------------------------------------

def orient_temp_chain(joints, primary_choice, secondary_choice):
    j1, j2, j3 = joints

    p1 = get_world_position(j1)
    p2 = get_world_position(j2)
    p3 = get_world_position(j3)

    plane_normal = vec_cross(
        vec_sub(p2, p1),
        vec_sub(p3, p1)
    )

    normal_length = vec_length(plane_normal)

    if normal_length < 1e-6:
        raise RuntimeError(
            "The temporary joints are collinear or too close together. "
            "A stable orientation cannot be calculated."
        )

    plane_normal = vec_normalize(plane_normal)

    if primary_choice[1] == secondary_choice[1]:
        raise RuntimeError(
            "Primary and secondary axes must be different axes."
        )

    aim_vector = AXIS_MAP[primary_choice]
    up_vector = AXIS_ABS[secondary_choice]

    secondary_sign = (
        -1.0 if secondary_choice.startswith("-") else 1.0
    )

    world_up_vector = vec_mul(plane_normal, secondary_sign)

    # Store the intended temporary hierarchy.
    original_parents = [
        (cmds.listRelatives(j, parent=True) or [None])[0]
        for j in joints
    ]

    temp_nodes = []

    try:
        # Unparent each joint, preserving its world position.
        for joint in joints:
            parent = cmds.listRelatives(joint, parent=True)
            if parent:
                cmds.parent(joint, world=True)

        # Clear existing joint orientation and rotation.
        for joint in joints:
            cmds.setAttr(
                joint + ".jointOrient", 0, 0, 0, type="double3"
            )
            cmds.setAttr(
                joint + ".rotate", 0, 0, 0, type="double3"
            )

        # Aim targets.
        loc_j2 = cmds.spaceLocator(
            name="__tmp_PV_aim_j2__"
        )[0]
        loc_j3 = cmds.spaceLocator(
            name="__tmp_PV_aim_j3__"
        )[0]

        temp_nodes.extend([loc_j2, loc_j3])

        cmds.xform(loc_j2, worldSpace=True, translation=p2)
        cmds.xform(loc_j3, worldSpace=True, translation=p3)

        direction = vec_normalize(vec_sub(p3, p2))

        if vec_length(direction) < 1e-6:
            direction = [1.0, 0.0, 0.0]

        distance = vec_length(vec_sub(p3, p2))
        if distance < 1e-6:
            distance = 1.0

        offset_position = vec_add(
            p3, vec_mul(direction, distance)
        )

        loc_offset = cmds.spaceLocator(
            name="__tmp_PV_aim_offset__"
        )[0]

        temp_nodes.append(loc_offset)

        cmds.xform(
            loc_offset,
            worldSpace=True,
            translation=offset_position
        )

        # Orient the base joint toward the middle joint.
        constraint = cmds.aimConstraint(
            loc_j2, j1,
            aimVector=aim_vector,
            upVector=up_vector,
            worldUpType="vector",
            worldUpVector=world_up_vector,
            maintainOffset=False
        )

        rotation = cmds.getAttr(j1 + ".rotate")[0]
        cmds.delete(constraint)

        cmds.setAttr(
            j1 + ".jointOrient",
            rotation[0], rotation[1], rotation[2],
            type="double3"
        )
        cmds.setAttr(j1 + ".rotate", 0, 0, 0, type="double3")

        # Orient the middle joint toward the end joint.
        constraint = cmds.aimConstraint(
            loc_j3, j2,
            aimVector=aim_vector,
            upVector=up_vector,
            worldUpType="vector",
            worldUpVector=world_up_vector,
            maintainOffset=False
        )

        rotation = cmds.getAttr(j2 + ".rotate")[0]
        cmds.delete(constraint)

        cmds.setAttr(
            j2 + ".jointOrient",
            rotation[0], rotation[1], rotation[2],
            type="double3"
        )
        cmds.setAttr(j2 + ".rotate", 0, 0, 0, type="double3")

        # Orient the end joint along the final chain direction.
        constraint = cmds.aimConstraint(
            loc_offset, j3,
            aimVector=aim_vector,
            upVector=up_vector,
            worldUpType="vector",
            worldUpVector=world_up_vector,
            maintainOffset=False
        )

        rotation = cmds.getAttr(j3 + ".rotate")[0]
        cmds.delete(constraint)

        cmds.setAttr(
            j3 + ".jointOrient",
            rotation[0], rotation[1], rotation[2],
            type="double3"
        )
        cmds.setAttr(j3 + ".rotate", 0, 0, 0, type="double3")

        # Restore the temporary hierarchy.
        for joint, parent in zip(joints, original_parents):
            if parent and cmds.objExists(parent):
                cmds.parent(joint, parent)

    finally:
        for node in temp_nodes:
            if cmds.objExists(node):
                cmds.delete(node)


# --------------------------------------------------
# Main process
# --------------------------------------------------

def create_pv_locator(primary_choice, secondary_choice):
    selection = cmds.ls(selection=True, long=True) or []

    if len(selection) != 1:
        show_warning(
            "Select exactly one IK handle in the Outliner."
        )
        return

    handle = selection[0]

    # Validate before creating anything.
    try:
        start_joint, end_joint, pole_vector = (
            get_spring_solver_data(handle)
        )
    except Exception as error:
        show_warning(str(error))
        return

    if primary_choice[1] == secondary_choice[1]:
        show_warning(
            "Primary and secondary axes must be different."
        )
        return

    base_position = get_world_position(start_joint)
    end_position = get_world_position(end_joint)

    temp_joints = []
    locator_group = None
    undo_open = False

    try:
        cmds.undoInfo(openChunk=True)
        undo_open = True

        # 1. Create the base joint at the start joint position.
        base = create_temp_joint(
            "__tmp_PV_base_Jnt__", base_position
        )
        temp_joints.append(base)

        # 2. Create the pole vector joint as a child of the base.
        pv_joint = cmds.createNode(
            "joint", name="__tmp_PV_middle_Jnt__"
        )
        temp_joints.append(pv_joint)

        cmds.parent(pv_joint, base)

        cmds.setAttr(
            pv_joint + ".translate",
            pole_vector[0], pole_vector[1], pole_vector[2],
            type="double3"
        )
        cmds.setAttr(
            pv_joint + ".rotate", 0, 0, 0, type="double3"
        )
        cmds.setAttr(
            pv_joint + ".jointOrient", 0, 0, 0, type="double3"
        )

        # 3. Create the end joint at the end joint position.
        end = create_temp_joint(
            "__tmp_PV_end_Jnt__", end_position
        )
        temp_joints.append(end)

        # Parent the end joint under the pole vector joint,
        # preserving its world-space position.
        cmds.parent(end, pv_joint)

        # Ensure the chain is ready for orientation.
        for joint in temp_joints:
            cmds.setAttr(
                joint + ".rotate", 0, 0, 0, type="double3"
            )

        # 4. Orient the temporary chain.
        orient_temp_chain(
            [base, pv_joint, end],
            primary_choice,
            secondary_choice
        )

        # 5. Create the locator and its group.
        # The group will inherit the middle joint's world transform.
        locator_group = cmds.createNode(
            "transform", name="Temp_PV_Loc_Grp"
        )

        locator = cmds.spaceLocator(
            name="Temp_PV_Loc"
        )[0]

        cmds.parent(locator, locator_group)

        # Match the group's complete world-space transform
        # to the oriented middle joint.
        world_matrix = cmds.xform(
            pv_joint, query=True, worldSpace=True, matrix=True
        )

        cmds.xform(
            locator_group,
            worldSpace=True,
            matrix=world_matrix
        )

        # Keep the locator itself centered in the group.
        cmds.setAttr(
            locator + ".translate", 0, 0, 0, type="double3"
        )
        cmds.setAttr(
            locator + ".rotate", 0, 0, 0, type="double3"
        )

    except Exception as error:
        import traceback

        error_details = traceback.format_exc()
        print("\n=== Spring Solver PV Locator Error ===")
        print(error_details)

        if locator_group and cmds.objExists(locator_group):
            try:
                cmds.delete(locator_group)
            except Exception:
                pass

        show_warning(
            "Could not create the pole vector locator.\n\n"
            "Check the Maya Script Editor for the exact failing line."
        )

    finally:
        # Remove the temporary chain.
        for joint in reversed(temp_joints):
            if cmds.objExists(joint):
                try:
                    cmds.delete(joint)
                except Exception:
                    pass

        if undo_open:
            cmds.undoInfo(closeChunk=True)

    if locator_group and cmds.objExists(locator_group):
        cmds.select(locator_group, replace=True)

        cmds.inViewMessage(
            amg=(
                "Created <hl>Temp_PV_Loc_Grp</hl> "
                "from the selected spring solver."
            ),
            position="topCenter",
            fade=True
        )


# --------------------------------------------------
# UI
# --------------------------------------------------

def show_pv_locator_ui():
    if cmds.window(WINDOW_NAME, exists=True):
        cmds.deleteUI(WINDOW_NAME)

    window = cmds.window(
        WINDOW_NAME,
        title="Spring Solver Pole Vector Locator",
        sizeable=True,
        widthHeight=(440, 205)
    )

    cmds.columnLayout(
        adjustableColumn=True,
        rowSpacing=8,
        columnAttach=("both", 8)
    )

    cmds.text(
        label=(
            "Select one IK handle using an IK Spring Solver "
            "in the Outliner."
        ),
        align="center",
        wordWrap=True
    )

    cmds.separator(height=5, style="in")

    cmds.rowLayout(
        numberOfColumns=2,
        columnWidth2=(220, 190),
        adjustableColumn=2
    )

    cmds.text(label="Primary axis (aim down chain):")
    primary_menu = cmds.optionMenu(
        "springPVPrimaryMenu"
    )

    for axis in ["+X", "-X", "+Y", "-Y", "+Z", "-Z"]:
        cmds.menuItem(label=axis)

    cmds.setParent("..")

    cmds.rowLayout(
        numberOfColumns=2,
        columnWidth2=(220, 190),
        adjustableColumn=2
    )

    cmds.text(label="Secondary axis (joint plane):")
    secondary_menu = cmds.optionMenu(
        "springPVSecondaryMenu"
    )

    for axis in ["+X", "-X", "+Y", "-Y", "+Z", "-Z"]:
        cmds.menuItem(label=axis)

    cmds.optionMenu(
        secondary_menu, edit=True, value="+Z"
    )

    cmds.setParent("..")

    cmds.separator(height=5, style="in")

    cmds.button(
        label="Create Pole Vector Locator",
        height=40,
        command=lambda *_: create_pv_locator(
            cmds.optionMenu(
                primary_menu, query=True, value=True
            ),
            cmds.optionMenu(
                secondary_menu, query=True, value=True
            )
        )
    )

    cmds.button(
        label="Close",
        height=28,
        command=lambda *_: cmds.deleteUI(window)
    )

    cmds.showWindow(window)


show_pv_locator_ui()

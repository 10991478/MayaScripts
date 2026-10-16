# Maya rig control selector with JSON configuration saving/loading.
# Stage 1: save and restore a rig window, including its sets and groups.

import os
import re
import json
from functools import partial

from PySide2 import QtWidgets, QtCore, QtGui
from shiboken2 import wrapInstance
import maya.OpenMayaUI as omui
import maya.cmds as cmds
import maya.mel as mel


CONFIG_FOLDER_NAME = "RigControlConfigs"


def get_maya_main_window():
    ptr = omui.MQtUtil.mainWindow()
    return wrapInstance(int(ptr), QtWidgets.QWidget)


def get_config_directory():
    """Return the persistent configuration folder inside Maya's user scripts folder."""
    path = os.path.join(cmds.internalVar(userScriptDir=True), CONFIG_FOLDER_NAME)
    if not os.path.isdir(path):
        os.makedirs(path)
    return path


def safe_filename(name):
    name = re.sub(r'[<>:"/\\\\|?*]', "_", name.strip())
    name = re.sub(r"\s+", "_", name)
    return name or "RigControls"


class RigControlSelector(QtWidgets.QDialog):
    def __init__(self, parent=None):
        if parent is None:
            parent = get_maya_main_window()
        super(RigControlSelector, self).__init__(parent)
        self.setWindowFlags(self.windowFlags() | QtCore.Qt.WindowMinimizeButtonHint)
        self.setWindowTitle("Rig Control UI Creator")
        self.setMinimumWidth(440)
        self.setLayout(QtWidgets.QVBoxLayout())
        self.req_prefix = self.req_infix = self.req_suffix = None
        self.exc_prefix = self.exc_infix = self.exc_suffix = None
        self.rig_field = None
        self.build_ui()

    def build_ui(self):
        self.layout().addWidget(
            self._make_filter_group("Required Text", default_suffix="_Ctrl", req=True)
        )
        self.layout().addWidget(
            self._make_filter_group("Excluded Text", default_suffix="", req=False)
        )

        rig_group = QtWidgets.QGroupBox("Rig Selection")
        rig_layout = QtWidgets.QHBoxLayout(rig_group)
        self.rig_field = QtWidgets.QLineEdit()
        rig_layout.addWidget(self.rig_field)
        grab_btn = QtWidgets.QPushButton("Grab Selected Rigs")
        grab_btn.clicked.connect(self.grab_selected)
        rig_layout.addWidget(grab_btn)
        self.layout().addWidget(rig_group)

        generate_btn = QtWidgets.QPushButton("Create Control UIs")
        generate_btn.clicked.connect(self.generate_uis)
        self.layout().addWidget(generate_btn)

        load_btn = QtWidgets.QPushButton("Load Saved Configuration")
        load_btn.clicked.connect(self.load_configuration_dialog)
        self.layout().addWidget(load_btn)

    def _make_filter_group(self, title, default_suffix, req):
        group = QtWidgets.QGroupBox(title)
        layout = QtWidgets.QFormLayout(group)
        prefix = QtWidgets.QLineEdit()
        infix = QtWidgets.QLineEdit()
        suffix = QtWidgets.QLineEdit()
        suffix.setText(default_suffix)
        layout.addRow("Prefixes (comma-separated)", prefix)
        layout.addRow("Infixes (comma-separated)", infix)
        layout.addRow("Suffixes (comma-separated)", suffix)
        if req:
            self.req_prefix, self.req_infix, self.req_suffix = prefix, infix, suffix
        else:
            self.exc_prefix, self.exc_infix, self.exc_suffix = prefix, infix, suffix
        return group

    def grab_selected(self):
        selected = cmds.ls(selection=True, long=True) or []
        if selected:
            self.rig_field.setText(", ".join(selected))

    def _get_filters(self, prefix_field, infix_field, suffix_field):
        return {
            "prefixes": [x.strip() for x in prefix_field.text().split(",") if x.strip()],
            "infixes": [x.strip() for x in infix_field.text().split(",") if x.strip()],
            "suffixes": [x.strip() for x in suffix_field.text().split(",") if x.strip()],
        }

    def generate_uis(self):
        roots = [r.strip() for r in self.rig_field.text().split(",") if r.strip()]
        reqs = self._get_filters(self.req_prefix, self.req_infix, self.req_suffix)
        excs = self._get_filters(self.exc_prefix, self.exc_infix, self.exc_suffix)
        if not roots:
            cmds.warning("Enter a rig root or use Grab Selected Rigs.")
            return
        for root in roots:
            if cmds.objExists(root):
                RigUI(root, reqs, excs)
            else:
                cmds.warning("Rig root does not exist: {}".format(root))

    def load_configuration_dialog(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Load Rig Control Configuration",
            get_config_directory(),
            "Rig Control Configurations (*.json)"
        )
        if path:
            load_saved_configuration(path)


def matches(name, reqs, excs):
    def any_match(text, patterns, mode):
        if not patterns:
            return True
        for pattern in patterns:
            if mode == "prefix" and text.startswith(pattern):
                return True
            if mode == "infix" and pattern in text:
                return True
            if mode == "suffix" and text.endswith(pattern):
                return True
        return False

    def any_excl(text, patterns, mode):
        for pattern in patterns:
            if mode == "prefix" and text.startswith(pattern):
                return True
            if mode == "infix" and pattern in text:
                return True
            if mode == "suffix" and text.endswith(pattern):
                return True
        return False

    if not (
        any_match(name, reqs["prefixes"], "prefix")
        and any_match(name, reqs["infixes"], "infix")
        and any_match(name, reqs["suffixes"], "suffix")
    ):
        return False

    if (
        any_excl(name, excs["prefixes"], "prefix")
        or any_excl(name, excs["infixes"], "infix")
        or any_excl(name, excs["suffixes"], "suffix")
    ):
        return False
    return True


class RigUI(QtWidgets.QDialog):
    def __init__(self, root, reqs, excs, parent=None):
        if parent is None:
            parent = get_maya_main_window()
        super(RigUI, self).__init__(parent)
        self.setWindowFlags(
            self.windowFlags()
            | QtCore.Qt.WindowMinimizeButtonHint
            | QtCore.Qt.WindowMaximizeButtonHint
        )
        self.setWindowTitle("Controls: {}".format(root))
        self.setLayout(QtWidgets.QVBoxLayout())
        self.resize(420, 560)

        self.root = root
        self.reqs = reqs
        self.excs = excs
        self.checks = []
        self.row_widgets = []
        self.selection_sets = {}
        self.groups = {}
        self.set_colors = {}
        self.group_colors = {}
        self.set_text_colors = {}
        self.group_text_colors = {}

        selection_mode_row = QtWidgets.QHBoxLayout()
        selection_mode_row.addWidget(QtWidgets.QLabel("Selection Mode:"))
        self.selection_mode_combo = QtWidgets.QComboBox()
        self.selection_mode_combo.addItems([
            "Add to Selection",
            "Set as Selection",
            "Remove from Selection",
            "Toggle Independently",
            "Toggle Together",
        ])
        self.selection_mode_combo.setToolTip(
            "Choose how control, set, and group buttons affect Maya's current selection."
        )
        selection_mode_row.addWidget(self.selection_mode_combo, 1)
        self.layout().addLayout(selection_mode_row)

        root_row = QtWidgets.QHBoxLayout()
        self.root_label = QtWidgets.QLabel("Rig Root: {}".format(self.root))
        self.root_label.setToolTip(self.root)
        root_row.addWidget(self.root_label, 1)
        reassign_root_btn = QtWidgets.QPushButton("Use Selected Object as Rig Root")
        reassign_root_btn.setToolTip(
            "Select the new rig root in Maya, then click to rebuild this selector for that rig."
        )
        reassign_root_btn.clicked.connect(self.reassign_rig_root)
        root_row.addWidget(reassign_root_btn)
        self.layout().addLayout(root_row)

        self.tabs = QtWidgets.QTabWidget()
        self.tabs.addTab(self._make_controls_tab(), "Controls")
        self.tabs.addTab(self._make_sets_tab(), "Sets")
        self.tabs.addTab(self._make_groups_tab(), "Groups")
        self.layout().addWidget(self.tabs)

        save_row = QtWidgets.QHBoxLayout()

        save_btn = QtWidgets.QPushButton("Save Configuration")
        save_btn.setToolTip("Save this rig window, including its current sets and groups.")
        save_btn.clicked.connect(self.save_configuration)
        save_row.addWidget(save_btn)

        shelf_btn = QtWidgets.QPushButton("Save to Shelf")
        shelf_btn.setToolTip(
            "Save this configuration and create or update a Maya shelf button for it."
        )
        shelf_btn.clicked.connect(self.save_configuration_to_shelf)
        save_row.addWidget(shelf_btn)

        self.layout().addLayout(save_row)
        self.show()

    def _canonical_root(self, root):
        """Return a full DAG path when the root exists, otherwise retain its saved path."""
        found = cmds.ls(root, long=True) or []
        return found[0] if found else root

    def _map_control_to_root(self, item, old_root, new_root, descendants):
        """Map a saved control by relative DAG path, then by unique leaf name."""
        old_parts = [part for part in old_root.split("|") if part]
        item_parts = [part for part in item.split("|") if part]
        new_root = self._canonical_root(new_root)

        if old_parts and len(item_parts) > len(old_parts) and item_parts[:len(old_parts)] == old_parts:
            relative_parts = item_parts[len(old_parts):]
            candidate = new_root + "|" + "|".join(relative_parts)
            if cmds.objExists(candidate):
                return (cmds.ls(candidate, long=True) or [candidate])[0]

        leaf = item.split("|")[-1]
        matches_by_leaf = [node for node in descendants if node.split("|")[-1] == leaf]
        if len(matches_by_leaf) == 1:
            return matches_by_leaf[0]
        return item

    def reassign_rig_root(self):
        selected = cmds.ls(selection=True, long=True) or []
        if not selected:
            cmds.warning("Select the new rig root in Maya before using this button.")
            return

        new_root = selected[0]
        node_type = cmds.nodeType(new_root)
        if node_type not in ("transform", "joint"):
            parents = cmds.listRelatives(new_root, parent=True, fullPath=True) or []
            if not parents:
                cmds.warning("The selected object is not a usable transform or joint rig root.")
                return
            new_root = parents[0]

        new_root = self._canonical_root(new_root)
        if new_root == self._canonical_root(self.root):
            cmds.warning("The selected object is already this selector's rig root.")
            return

        old_root = self.root
        descendants = cmds.listRelatives(new_root, allDescendents=True, fullPath=True) or []
        descendants = sorted(set(descendants))

        def remap_collection(collection):
            remapped = {}
            for name, items in collection.items():
                remapped[name] = [
                    self._map_control_to_root(item, old_root, new_root, descendants)
                    for item in items
                ]
            return remapped

        self.selection_sets = remap_collection(self.selection_sets)
        self.groups = remap_collection(self.groups)
        self.root = new_root

        old_controls_tab = self.tabs.widget(0)
        self.tabs.removeTab(0)
        old_controls_tab.setParent(None)
        old_controls_tab.deleteLater()
        self.tabs.insertTab(0, self._make_controls_tab(), "Controls")

        self._clear_layout(self.sets_layout)
        for name, items in self.selection_sets.items():
            self._create_set_button(name, items)
        self._clear_layout(self.groups_layout)
        for name, items in self.groups.items():
            self._create_group_widget(name, items)

        self.root_label.setText("Rig Root: {}".format(self.root))
        self.root_label.setToolTip(self.root)
        self.setWindowTitle("Controls: {}".format(self.root))
        cmds.warning(
            "Rig root updated. Review saved sets and groups; controls that could not be matched "
            "will remain unresolved until their names or hierarchy match."
        )

    def _clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()
            elif item.layout() is not None:
                self._clear_layout(item.layout())

    def _apply_button_color(self, button, color=None, text_color=None):
        rules = []
        if color:
            rules.append("background-color: {};".format(color))
        if text_color:
            rules.append("color: {};".format(text_color))
        if rules:
            button.setStyleSheet(
                "QPushButton { %s } QPushButton:hover { border: 1px solid #ffffff; }"
                % " ".join(rules)
            )

    def choose_item_text_color(self, item_type, name):
        colors = self.set_text_colors if item_type == "set" else self.group_text_colors
        current = QtGui.QColor(colors.get(name, ""))
        if not current.isValid():
            current = QtGui.QColor(255, 255, 255)
        color = QtWidgets.QColorDialog.getColor(
            current, self, "Choose {} Button Text Color".format(item_type.title())
        )
        if not color.isValid():
            return
        colors[name] = color.name()
        self._refresh_saved_tabs()

    def _create_set_button(self, name, items):
        row = QtWidgets.QWidget()
        row_layout = QtWidgets.QHBoxLayout(row)
        row_layout.setContentsMargins(2, 2, 2, 2)

        select_btn = QtWidgets.QPushButton(name)
        select_btn.clicked.connect(partial(self.select_items, list(items)))
        self._apply_button_color(
            select_btn, self.set_colors.get(name), self.set_text_colors.get(name)
        )
        row_layout.addWidget(select_btn, 1)

        color_btn = QtWidgets.QPushButton("Color")
        color_btn.clicked.connect(partial(self.choose_item_color, "set", name))
        row_layout.addWidget(color_btn)
        text_color_btn = QtWidgets.QPushButton("Text Color")
        text_color_btn.clicked.connect(partial(self.choose_item_text_color, "set", name))
        row_layout.addWidget(text_color_btn)
        rename_btn = QtWidgets.QPushButton("Rename")
        rename_btn.clicked.connect(partial(self.rename_saved_item, "set", name))
        row_layout.addWidget(rename_btn)
        delete_btn = QtWidgets.QPushButton("Delete")
        delete_btn.clicked.connect(partial(self.delete_saved_item, "set", name))
        row_layout.addWidget(delete_btn)
        self.sets_layout.addWidget(row)

    def _create_group_widget(self, name, items):
        row = QtWidgets.QWidget()
        row_layout = QtWidgets.QHBoxLayout(row)
        row_layout.setContentsMargins(2, 2, 2, 2)

        group_btn = QtWidgets.QPushButton(name)
        group_btn.clicked.connect(partial(self.open_group_popup, name))
        self._apply_button_color(
            group_btn, self.group_colors.get(name), self.group_text_colors.get(name)
        )
        row_layout.addWidget(group_btn, 1)

        color_btn = QtWidgets.QPushButton("Color")
        color_btn.clicked.connect(partial(self.choose_item_color, "group", name))
        row_layout.addWidget(color_btn)
        text_color_btn = QtWidgets.QPushButton("Text Color")
        text_color_btn.clicked.connect(partial(self.choose_item_text_color, "group", name))
        row_layout.addWidget(text_color_btn)
        rename_btn = QtWidgets.QPushButton("Rename")
        rename_btn.clicked.connect(partial(self.rename_saved_item, "group", name))
        row_layout.addWidget(rename_btn)
        delete_btn = QtWidgets.QPushButton("Delete")
        delete_btn.clicked.connect(partial(self.delete_saved_item, "group", name))
        row_layout.addWidget(delete_btn)
        self.groups_layout.addWidget(row)

    def choose_item_color(self, item_type, name):
        colors = self.set_colors if item_type == "set" else self.group_colors
        current = QtGui.QColor(colors.get(name, ""))
        if not current.isValid():
            current = QtGui.QColor(90, 110, 145)
        color = QtWidgets.QColorDialog.getColor(current, self, "Choose {} Button Color".format(item_type.title()))
        if not color.isValid():
            return
        colors[name] = color.name()
        self._refresh_saved_tabs()

    def open_group_popup(self, name):
        items = self.groups.get(name, [])
        color = self.group_colors.get(name, "")
        popup = QtWidgets.QDialog(self, QtCore.Qt.Tool)
        popup.setWindowTitle("{} | {}".format(self.root.split("|")[-1], name))
        popup.setMinimumSize(240, 300)
        outer = QtWidgets.QVBoxLayout(popup)
        heading = QtWidgets.QLabel("{} | {}".format(self.root.split("|")[-1], name))
        heading.setStyleSheet("font-weight: bold; padding: 5px;")
        outer.addWidget(heading)
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        container = QtWidgets.QWidget()
        list_layout = QtWidgets.QVBoxLayout(container)
        list_layout.setAlignment(QtCore.Qt.AlignTop)
        for full_name in items:
            button = QtWidgets.QPushButton(full_name.split("|")[-1])
            button.setToolTip(full_name)
            button.clicked.connect(partial(self.select_items, [full_name]))
            self._apply_button_color(button, None, self.group_text_colors.get(name))
            list_layout.addWidget(button)
        scroll.setWidget(container)
        outer.addWidget(scroll)
        if color:
            popup.setStyleSheet(
                "QDialog { border: 3px solid %s; }" % color
            )
        popup.show()
        self._group_popups = getattr(self, "_group_popups", [])
        self._group_popups.append(popup)

    def _make_controls_tab(self):
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(widget)

        search_row = QtWidgets.QHBoxLayout()
        self.search_field = QtWidgets.QLineEdit()
        self.search_field.setPlaceholderText("Search control names...")
        search_row.addWidget(self.search_field)
        search_btn = QtWidgets.QPushButton("Search")
        search_btn.clicked.connect(self.apply_search)
        search_row.addWidget(search_btn)
        clear_search_btn = QtWidgets.QPushButton("Clear")
        clear_search_btn.clicked.connect(self.clear_search)
        search_row.addWidget(clear_search_btn)
        self.include_all_cb = QtWidgets.QCheckBox("Include All Tags")
        search_row.addWidget(self.include_all_cb)
        self.case_sensitive_cb = QtWidgets.QCheckBox("Case-Sensitive")
        self.case_sensitive_cb.setChecked(True)
        search_row.addWidget(self.case_sensitive_cb)
        clear_checks_btn = QtWidgets.QPushButton("Clear Checks")
        clear_checks_btn.clicked.connect(self.clear_checks)
        search_row.addWidget(clear_checks_btn)
        check_all_btn = QtWidgets.QPushButton("Check All Shown")
        check_all_btn.clicked.connect(self.check_all_shown)
        search_row.addWidget(check_all_btn)
        show_checked_btn = QtWidgets.QPushButton("Show All Checked")
        show_checked_btn.setToolTip("Hide unchecked controls and show every checked control.")
        show_checked_btn.clicked.connect(self.show_all_checked)
        search_row.addWidget(show_checked_btn)
        layout.addLayout(search_row)

        creation_row = QtWidgets.QHBoxLayout()
        create_checked_btn = QtWidgets.QPushButton("Create Set/Group from Checked Controls")
        create_checked_btn.clicked.connect(self.open_create_from_checked_dialog)
        creation_row.addWidget(create_checked_btn)
        create_selection_btn = QtWidgets.QPushButton("Create Set/Group from Selection")
        create_selection_btn.setToolTip(
            "Create a set and/or group from selected Maya objects that are valid controls in this rig."
        )
        create_selection_btn.clicked.connect(self.open_create_from_selection_dialog)
        creation_row.addWidget(create_selection_btn)
        layout.addLayout(creation_row)

        self.scroll = QtWidgets.QScrollArea()
        self.cont = QtWidgets.QWidget()
        self.form = QtWidgets.QVBoxLayout(self.cont)
        self.form.setAlignment(QtCore.Qt.AlignTop)
        self.scroll.setWidget(self.cont)
        self.scroll.setWidgetResizable(True)
        layout.addWidget(self.scroll)

        all_children = cmds.listRelatives(self.root, allDescendents=True, fullPath=True) or []
        self.all_controls = sorted(
            [c for c in all_children if matches(c.split("|")[-1], self.reqs, self.excs)]
        )
        self.build_control_list(self.all_controls)
        return widget

    def build_control_list(self, names):
        for row_widget, _ in self.row_widgets:
            row_widget.setParent(None)
            row_widget.deleteLater()
        self.checks = []
        self.row_widgets = []
        for name in names:
            row = QtWidgets.QWidget()
            row_layout = QtWidgets.QHBoxLayout(row)
            row_layout.setContentsMargins(2, 2, 2, 2)
            checkbox = QtWidgets.QCheckBox()
            button = QtWidgets.QPushButton(name.split("|")[-1])
            button.setToolTip(name)
            button.clicked.connect(partial(self.select_items, [name]))
            row_layout.addWidget(checkbox)
            row_layout.addWidget(button)
            self.form.addWidget(row)
            self.checks.append((checkbox, name))
            self.row_widgets.append((row, name))

    def check_all_shown(self):
        for (checkbox, _), (row_widget, _) in zip(self.checks, self.row_widgets):
            if not row_widget.isHidden():
                checkbox.setChecked(True)

    def show_all_checked(self):
        for checkbox, control in self.checks:
            row_widget = next((row for row, name in self.row_widgets if name == control), None)
            if row_widget is not None:
                row_widget.setVisible(checkbox.isChecked())

    def _selected_valid_controls(self):
        """Return selected transforms that exactly match controls shown by this rig UI."""
        selected = cmds.ls(selection=True, long=True, objectsOnly=True) or []
        valid_controls = set(self.all_controls)
        accepted = []
        for item in selected:
            if not cmds.objExists(item):
                continue
            if cmds.nodeType(item) not in ("transform", "joint"):
                parents = cmds.listRelatives(item, parent=True, fullPath=True) or []
                if not parents:
                    continue
                item = parents[0]
            item = (cmds.ls(item, long=True) or [item])[0]
            if item in valid_controls and item not in accepted:
                accepted.append(item)
        return accepted

    def open_create_from_selection_dialog(self):
        selected = self._selected_valid_controls()
        if not selected:
            QtWidgets.QMessageBox.warning(
                self, "No Valid Controls Selected",
                "Select at least one control that belongs to this rig and is listed in this selector."
            )
            return
        self._open_create_item_dialog(selected, "Create Set/Group from Selection", "valid control(s) selected; other objects will be ignored.")

    def open_create_from_checked_dialog(self):
        checked = [control for checkbox, control in self.checks if checkbox.isChecked()]
        if not checked:
            QtWidgets.QMessageBox.warning(
                self, "No Controls Checked", "Check at least one control in the Controls tab first."
            )
            return
        self._open_create_item_dialog(checked, "Create Set/Group from Checked Controls", "checked control(s) will be included.")

    def _open_create_item_dialog(self, items, title, description):
        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle(title)
        dialog.setWindowModality(QtCore.Qt.WindowModal)
        dialog.setMinimumWidth(320)
        form = QtWidgets.QVBoxLayout(dialog)
        name_field = QtWidgets.QLineEdit()
        name_field.setPlaceholderText("Set/group name")
        form.addWidget(QtWidgets.QLabel("Name:"))
        form.addWidget(name_field)
        set_cb = QtWidgets.QCheckBox("Create Set")
        group_cb = QtWidgets.QCheckBox("Create Group")
        set_cb.setChecked(True)
        form.addWidget(set_cb)
        form.addWidget(group_cb)
        form.addWidget(QtWidgets.QLabel("{} {}; other objects outside this rig are excluded.".format(len(items), description)))
        buttons = QtWidgets.QHBoxLayout()
        create_btn = QtWidgets.QPushButton("Create")
        cancel_btn = QtWidgets.QPushButton("Cancel")
        buttons.addWidget(create_btn)
        buttons.addWidget(cancel_btn)
        form.addLayout(buttons)
        create_btn.clicked.connect(lambda: self._finish_create_items(dialog, name_field.text(), set_cb.isChecked(), group_cb.isChecked(), items))
        cancel_btn.clicked.connect(dialog.reject)
        dialog.exec_()

    def _finish_create_items(self, dialog, raw_name, create_set, create_group, items):
        name = raw_name.strip()
        if not name:
            QtWidgets.QMessageBox.warning(dialog, "Name Required", "Enter a name for the set/group.")
            return
        if not create_set and not create_group:
            QtWidgets.QMessageBox.warning(dialog, "Choose an Item Type", "Select Create Set, Create Group, or both.")
            return

        # Name conflicts are checked independently for each item type.
        set_name = self._resolve_creation_name(name, "set") if create_set else None
        if create_set and set_name is None:
            return
        group_name = name
        if create_group:
            # If both are created together, the same name is explicitly permitted.
            group_name = self._resolve_creation_name(name, "group")
            if group_name is None:
                return
        if create_set:
            self.selection_sets[set_name] = list(items)
        if create_group:
            self.groups[group_name] = list(items)
        self._refresh_saved_tabs()
        dialog.accept()

    def _resolve_creation_name(self, name, item_type):
        collection = self.selection_sets if item_type == "set" else self.groups
        if name not in collection:
            return name
        answer = QtWidgets.QMessageBox.question(
            self,
            "Replace Existing {}?".format(item_type.title()),
            "A {} named '{}' already exists. Replace it?".format(item_type, name),
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No,
        )
        if answer == QtWidgets.QMessageBox.Yes:
            return name
        index = 1
        while "{}{}".format(name, index) in collection:
            index += 1
        return "{}{}".format(name, index)

    def _refresh_saved_tabs(self):
        self._clear_layout(self.sets_layout)
        for name, items in self.selection_sets.items():
            self._create_set_button(name, items)
        self._clear_layout(self.groups_layout)
        for name, items in self.groups.items():
            self._create_group_widget(name, items)

    def delete_saved_item(self, item_type, name):
        collection = self.selection_sets if item_type == "set" else self.groups
        colors = self.set_colors if item_type == "set" else self.group_colors
        text_colors = self.set_text_colors if item_type == "set" else self.group_text_colors
        if name not in collection:
            return
        answer = QtWidgets.QMessageBox.question(
            self, "Delete {}?".format(item_type.title()),
            "Delete '{}' permanently from this selector?".format(name),
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No,
        )
        if answer == QtWidgets.QMessageBox.Yes:
            del collection[name]
            colors.pop(name, None)
            text_colors.pop(name, None)
            self._refresh_saved_tabs()

    def rename_saved_item(self, item_type, old_name):
        collection = self.selection_sets if item_type == "set" else self.groups
        colors = self.set_colors if item_type == "set" else self.group_colors
        text_colors = self.set_text_colors if item_type == "set" else self.group_text_colors
        if old_name not in collection:
            return
        new_name, accepted = QtWidgets.QInputDialog.getText(
            self, "Rename {}".format(item_type.title()), "New name:", text=old_name
        )
        new_name = new_name.strip()
        if not accepted or not new_name or new_name == old_name:
            return
        if new_name in collection:
            answer = QtWidgets.QMessageBox.question(
                self, "Replace Existing {}?".format(item_type.title()),
                "A {} named '{}' already exists. Replace it?".format(item_type, new_name),
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                QtWidgets.QMessageBox.No,
            )
            if answer == QtWidgets.QMessageBox.Yes:
                collection.pop(new_name, None)
                colors.pop(new_name, None)
                text_colors.pop(new_name, None)
            else:
                base = new_name
                index = 1
                while "{}{}".format(base, index) in collection:
                    index += 1
                new_name = "{}{}".format(base, index)
        items = collection.pop(old_name)
        collection[new_name] = items
        if old_name in colors:
            colors[new_name] = colors.pop(old_name)
        if old_name in text_colors:
            text_colors[new_name] = text_colors.pop(old_name)
        self._refresh_saved_tabs()

    def create_set(self):
        items = [control for checkbox, control in self.checks if checkbox.isChecked()]
        name = getattr(self, "new_set_name", None)
        name = name.text().strip() if name else ""
        if name and items:
            resolved = self._resolve_creation_name(name, "set")
            if resolved is not None:
                self.selection_sets[resolved] = list(items)
                self._refresh_saved_tabs()

    def create_group(self):
        items = [control for checkbox, control in self.checks if checkbox.isChecked()]
        name = getattr(self, "new_set_name", None)
        name = name.text().strip() if name else ""
        if name and items:
            resolved = self._resolve_creation_name(name, "group")
            if resolved is not None:
                self.groups[resolved] = list(items)
                self._refresh_saved_tabs()

    def add_saved_set(self, name, items):
        self.selection_sets[name] = list(items)
        self._create_set_button(name, items)

    def select_items(self, items):
        """Apply the current selection mode to the requested controls."""
        requested = []
        missing = []
        for item in items:
            if not cmds.objExists(item):
                missing.append(item)
                continue
            resolved = (cmds.ls(item, long=True) or [item])[0]
            if resolved not in requested:
                requested.append(resolved)

        if missing:
            cmds.warning("Some saved controls could not be found: {}".format(", ".join(missing)))
        if not requested:
            return

        mode = self.selection_mode_combo.currentText()
        current = cmds.ls(selection=True, long=True, objectsOnly=True) or []
        current_set = set(current)

        if mode == "Add to Selection":
            cmds.select(requested, add=True)
        elif mode == "Set as Selection":
            cmds.select(requested, replace=True)
        elif mode == "Remove from Selection":
            remaining = [item for item in current if item not in requested]
            if remaining:
                cmds.select(remaining, replace=True)
            else:
                cmds.select(clear=True)
        elif mode == "Toggle Independently":
            result = list(current)
            for item in requested:
                if item in current_set:
                    result = [selected for selected in result if selected != item]
                    current_set.discard(item)
                else:
                    result.append(item)
                    current_set.add(item)
            if result:
                cmds.select(result, replace=True)
            else:
                cmds.select(clear=True)
        elif mode == "Toggle Together":
            if any(item not in current_set for item in requested):
                cmds.select(requested, add=True)
            else:
                remaining = [item for item in current if item not in set(requested)]
                if remaining:
                    cmds.select(remaining, replace=True)
                else:
                    cmds.select(clear=True)

    def _make_sets_tab(self):
        widget = QtWidgets.QWidget()
        scroll = QtWidgets.QScrollArea()
        container = QtWidgets.QWidget()
        self.sets_layout = QtWidgets.QVBoxLayout(container)
        self.sets_layout.setAlignment(QtCore.Qt.AlignTop)
        scroll.setWidget(container)
        scroll.setWidgetResizable(True)
        layout = QtWidgets.QVBoxLayout(widget)
        layout.addWidget(scroll)
        return widget

    def _make_groups_tab(self):
        widget = QtWidgets.QWidget()
        scroll = QtWidgets.QScrollArea()
        container = QtWidgets.QWidget()
        self.groups_layout = QtWidgets.QVBoxLayout(container)
        self.groups_layout.setAlignment(QtCore.Qt.AlignTop)
        scroll.setWidget(container)
        scroll.setWidgetResizable(True)
        layout = QtWidgets.QVBoxLayout(widget)
        layout.addWidget(scroll)
        return widget

    def create_group(self):
        name = getattr(self, "new_set_name", None)
        name = name.text().strip() if name else ""
        items = [control for checkbox, control in self.checks if checkbox.isChecked()]
        if not name or not items:
            return
        resolved_name = self._resolve_creation_name(name)
        if resolved_name is None:
            return
        self.groups[resolved_name] = list(items)
        self._refresh_saved_tabs()

    def add_saved_group(self, name, items):
        self.groups[name] = list(items)
        self._create_group_widget(name, items)

    def apply_search(self):
        terms = [term.strip() for term in self.search_field.text().split(",") if term.strip()]
        case_sensitive = self.case_sensitive_cb.isChecked()
        include_all = self.include_all_cb.isChecked()
        if not terms:
            for row_widget, _ in self.row_widgets:
                row_widget.setVisible(True)
            return
        if not case_sensitive:
            terms = [term.lower() for term in terms]
        for row_widget, full_name in self.row_widgets:
            base = full_name.split("|")[-1]
            test = base if case_sensitive else base.lower()
            show = (
                all(term in test for term in terms)
                if include_all
                else any(term in test for term in terms)
            )
            row_widget.setVisible(show)

    def clear_search(self):
        self.search_field.clear()
        for row_widget, _ in self.row_widgets:
            row_widget.setVisible(True)

    def clear_checks(self):
        for checkbox, _ in self.checks:
            checkbox.setChecked(False)

    def _configuration_data(self, name):
        return {
            "format_version": 1,
            "configuration_name": name.strip(),
            "root": self.root,
            "required_filters": self.reqs,
            "excluded_filters": self.excs,
            "sets": self.selection_sets,
            "groups": self.groups,
            "set_colors": self.set_colors,
            "group_colors": self.group_colors,
            "set_text_colors": self.set_text_colors,
            "group_text_colors": self.group_text_colors,
        }

    def _write_configuration(self, name, ask_overwrite=True):
        name = name.strip()
        if not name:
            return None

        path = os.path.join(get_config_directory(), safe_filename(name) + ".json")
        if os.path.exists(path) and ask_overwrite:
            answer = QtWidgets.QMessageBox.question(
                self,
                "Overwrite Configuration?",
                "A configuration with this name already exists. Replace it?",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                QtWidgets.QMessageBox.No,
            )
            if answer != QtWidgets.QMessageBox.Yes:
                return None

        try:
            with open(path, "w", encoding="utf-8") as config_file:
                json.dump(
                    self._configuration_data(name),
                    config_file,
                    indent=4,
                    ensure_ascii=False,
                )
            return path
        except Exception as exc:
            cmds.warning("Could not save configuration: {}".format(exc))
            QtWidgets.QMessageBox.critical(self, "Save Failed", str(exc))
            return None

    def save_configuration(self):
        suggested_name = safe_filename(self.root.split("|")[-1])
        name, accepted = QtWidgets.QInputDialog.getText(
            self, "Save Rig Control Configuration", "Configuration name:", text=suggested_name
        )
        if not accepted or not name.strip():
            return None

        path = self._write_configuration(name)
        if path:
            QtWidgets.QMessageBox.information(
                self, "Configuration Saved", "Saved configuration to:\n{}".format(path)
            )
        return path

    def save_configuration_to_shelf(self):
        suggested_name = safe_filename(self.root.split("|")[-1])
        name, accepted = QtWidgets.QInputDialog.getText(
            self,
            "Save Configuration to Shelf",
            "Configuration name for the saved file and shelf button:",
            text=suggested_name,
        )
        if not accepted or not name.strip():
            return

        path = self._write_configuration(name)
        if not path:
            return

        try:
            create_or_update_shelf_button(name.strip(), path)
        except Exception as exc:
            cmds.warning("Configuration was saved, but shelf button creation failed: {}".format(exc))
            QtWidgets.QMessageBox.critical(
                self,
                "Shelf Button Failed",
                "The configuration was saved here:\n{}\n\n"
                "But Maya could not create the shelf button:\n{}".format(path, exc),
            )
            return

        QtWidgets.QMessageBox.information(
            self,
            "Configuration Saved to Shelf",
            "Saved configuration:\n{}\n\n"
            "A shelf button was created or updated on the currently selected Maya shelf.".format(path),
        )



def create_or_update_shelf_button(configuration_name, config_path):
    """
    Create a shelf button that loads this configuration without opening the creator UI.
    If a button for the same configuration already exists on the current shelf, update it.
    """
    config_path = os.path.normpath(os.path.abspath(config_path))
    annotation = "RigControlsSelectorConfig:{}".format(config_path)

    # Maya's global shelf tab layout and currently selected shelf.
    shelf_top_level = mel.eval('$tmp = $gShelfTopLevel')
    if not shelf_top_level or not cmds.tabLayout(shelf_top_level, exists=True):
        raise RuntimeError("Could not find Maya's shelf tab layout.")

    current_shelf = cmds.tabLayout(shelf_top_level, query=True, selectTab=True)
    if not current_shelf or not cmds.shelfLayout(current_shelf, exists=True):
        raise RuntimeError("Could not determine the currently selected shelf.")

    # Keep one button per configuration on the current shelf.
    for child in (cmds.shelfLayout(current_shelf, query=True, childArray=True) or []):
        if not cmds.control(child, exists=True):
            continue
        try:
            child_annotation = cmds.shelfButton(child, query=True, annotation=True)
        except Exception:
            continue
        if child_annotation == annotation:
            cmds.shelfButton(
                child,
                edit=True,
                label=configuration_name,
                annotation=annotation,
                image1="commandButton.png",
                sourceType="python",
                command=_shelf_command(config_path),
            )
            return child

    return cmds.shelfButton(
        parent=current_shelf,
        label=configuration_name,
        annotation=annotation,
        image1="commandButton.png",
        sourceType="python",
        command=_shelf_command(config_path),
    )


def _shelf_command(config_path):
    """Return the Python command stored in a Maya shelf button."""
    escaped_path = config_path.replace("\\", "\\\\").replace("'", "\\'")
    return (
        "import os, sys, importlib\n"
        "import maya.cmds as cmds\n"
        "script_dir = cmds.internalVar(userScriptDir=True)\n"
        "if script_dir not in sys.path:\n"
        "    sys.path.insert(0, script_dir)\n"
        "import RigControlsSelector\n"
        "importlib.reload(RigControlsSelector)\n"
        "RigControlsSelector.load_saved_configuration(r'{}')".format(escaped_path)
    )

def load_saved_configuration(path):
    try:
        with open(path, "r", encoding="utf-8") as config_file:
            data = json.load(config_file)
    except Exception as exc:
        QtWidgets.QMessageBox.critical(
            get_maya_main_window(), "Could Not Load Configuration",
            "Could not read the configuration file:\n{}".format(exc)
        )
        return None

    root = data.get("root", "")
    if not root or not cmds.objExists(root):
        selected = cmds.ls(selection=True, long=True) or []
        if not selected:
            QtWidgets.QMessageBox.warning(
                get_maya_main_window(),
                "Rig Root Not Found",
                "The saved rig root could not be found in the current Maya scene:\n{}\n\n"
                "Select the root transform or joint of the replacement rig, then click the shelf "
                "button again.".format(root)
            )
            return None

        answer = QtWidgets.QMessageBox.question(
            get_maya_main_window(),
            "Use Selected Rig Root?",
            "The saved rig root could not be found:\n{}\n\n"
            "Use the currently selected object as the replacement rig root?".format(root),
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.Yes,
        )
        if answer != QtWidgets.QMessageBox.Yes:
            return None
        root = selected[0]
        if cmds.nodeType(root) not in ("transform", "joint"):
            parents = cmds.listRelatives(root, parent=True, fullPath=True) or []
            if not parents:
                QtWidgets.QMessageBox.warning(
                    get_maya_main_window(), "Invalid Rig Root",
                    "The selected object is not a transform or joint and has no transform parent."
                )
                return None
            root = parents[0]

    ui = RigUI(
        root,
        data.get("required_filters", {"prefixes": [], "infixes": [], "suffixes": ["_Ctrl"]}),
        data.get("excluded_filters", {"prefixes": [], "infixes": [], "suffixes": []}),
    )
    saved_root = data.get("root", "")
    loaded_root = ui.root
    root_was_replaced = bool(saved_root and loaded_root != saved_root and not cmds.objExists(saved_root))
    descendants = cmds.listRelatives(loaded_root, allDescendents=True, fullPath=True) or []
    descendants = sorted(set(descendants))

    ui.set_colors = dict(data.get("set_colors", {}))
    ui.group_colors = dict(data.get("group_colors", {}))
    ui.set_text_colors = dict(data.get("set_text_colors", {}))
    ui.group_text_colors = dict(data.get("group_text_colors", {}))
    for name, items in data.get("sets", {}).items():
        if root_was_replaced:
            items = [ui._map_control_to_root(item, saved_root, loaded_root, descendants) for item in items]
        ui.add_saved_set(name, items)
    for name, items in data.get("groups", {}).items():
        if root_was_replaced:
            items = [ui._map_control_to_root(item, saved_root, loaded_root, descendants) for item in items]
        ui.add_saved_group(name, items)
    ui._refresh_saved_tabs()
    return ui


def show_rig_selector_ui():
    for widget in QtWidgets.QApplication.allWidgets():
        if isinstance(widget, RigControlSelector):
            widget.close()
    ui = RigControlSelector()
    ui.show()
    return ui


if __name__ == "__main__":
    show_rig_selector_ui()

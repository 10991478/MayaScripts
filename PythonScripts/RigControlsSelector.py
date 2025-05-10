# Maya rig control selector script with "Check All Shown" and maximize on Functional UI

from PySide2 import QtWidgets, QtCore
from shiboken2 import wrapInstance
import maya.OpenMayaUI as omui
import maya.cmds as cmds
from functools import partial


def get_maya_main_window():
    ptr = omui.MQtUtil.mainWindow()
    return wrapInstance(int(ptr), QtWidgets.QWidget)

class RigControlSelector(QtWidgets.QDialog):
    def __init__(self, parent=get_maya_main_window()):
        super(RigControlSelector, self).__init__(parent)
        self.setWindowFlags(self.windowFlags() | QtCore.Qt.WindowMinimizeButtonHint)
        self.setWindowTitle("Rig Control UI Creator")
        self.setMinimumWidth(400)
        self.setLayout(QtWidgets.QVBoxLayout())
        self.req_prefix = self.req_infix = self.req_suffix = None
        self.exc_prefix = self.exc_infix = self.exc_suffix = None
        self.rig_field = None
        self.build_ui()

    def build_ui(self):
        # Required / Excluded filters
        self.layout().addWidget(self._make_filter_group("Required Text", default_suffix="_Ctrl", req=True))
        self.layout().addWidget(self._make_filter_group("Excluded Text", default_suffix="", req=False))
        # Rig selection
        rig_group = QtWidgets.QGroupBox("Rig Selection")
        rig_l = QtWidgets.QHBoxLayout(rig_group)
        self.rig_field = QtWidgets.QLineEdit()
        rig_l.addWidget(self.rig_field)
        btn = QtWidgets.QPushButton("Grab Selected Rigs")
        btn.clicked.connect(self.grab_selected)
        rig_l.addWidget(btn)
        self.layout().addWidget(rig_group)
        # Generate button
        gen_btn = QtWidgets.QPushButton("Create Control UIs")
        gen_btn.clicked.connect(self.generate_uis)
        self.layout().addWidget(gen_btn)

    def _make_filter_group(self, title, default_suffix, req):
        grp = QtWidgets.QGroupBox(title)
        l = QtWidgets.QFormLayout(grp)
        prefix = QtWidgets.QLineEdit()
        infix = QtWidgets.QLineEdit()
        suffix = QtWidgets.QLineEdit()
        suffix.setText(default_suffix)
        l.addRow("Prefixes (comma-separated)", prefix)
        l.addRow("Infixes (comma-separated)", infix)
        l.addRow("Suffixes (comma-separated)", suffix)
        if req:
            self.req_prefix, self.req_infix, self.req_suffix = prefix, infix, suffix
        else:
            self.exc_prefix, self.exc_infix, self.exc_suffix = prefix, infix, suffix
        return grp

    def grab_selected(self):
        sels = cmds.ls(selection=True)
        if sels:
            self.rig_field.setText(", ".join(sels))

    def generate_uis(self):
        roots = [r.strip() for r in self.rig_field.text().split(",") if r.strip()]
        reqs = {
            'prefixes': [x.strip() for x in self.req_prefix.text().split(',') if x.strip()],
            'infixes': [x.strip() for x in self.req_infix.text().split(',') if x.strip()],
            'suffixes': [x.strip() for x in self.req_suffix.text().split(',') if x.strip()]
        }
        excs = {
            'prefixes': [x.strip() for x in self.exc_prefix.text().split(',') if x.strip()],
            'infixes': [x.strip() for x in self.exc_infix.text().split(',') if x.strip()],
            'suffixes': [x.strip() for x in self.exc_suffix.text().split(',') if x.strip()]
        }
        for root in roots:
            if cmds.objExists(root):
                RigUI(root, reqs, excs)


def matches(name, reqs, excs):
    def any_match(text, patterns, mode):
        if not patterns:
            return True
        for p in patterns:
            if mode=='prefix' and text.startswith(p):
                return True
            if mode=='infix' and p in text:
                return True
            if mode=='suffix' and text.endswith(p):
                return True
        return False
    def any_excl(text, patterns, mode):
        for p in patterns:
            if mode=='prefix' and text.startswith(p):
                return True
            if mode=='infix' and p in text:
                return True
            if mode=='suffix' and text.endswith(p):
                return True
        return False
    if not (any_match(name, reqs['prefixes'], 'prefix') and
            any_match(name, reqs['infixes'], 'infix') and
            any_match(name, reqs['suffixes'], 'suffix')):
        return False
    if (any_excl(name, excs['prefixes'], 'prefix') or
        any_excl(name, excs['infixes'], 'infix') or
        any_excl(name, excs['suffixes'], 'suffix')):
        return False
    return True

class RigUI(QtWidgets.QDialog):
    def __init__(self, root, reqs, excs, parent=get_maya_main_window()):
        super(RigUI, self).__init__(parent)
        # allow minimize + maximize
        self.setWindowFlags(self.windowFlags() | QtCore.Qt.WindowMinimizeButtonHint | QtCore.Qt.WindowMaximizeButtonHint)
        self.setWindowTitle(f"Controls: {root}")
        self.setLayout(QtWidgets.QVBoxLayout())
        self.resize(300, 520)

        self.root = root
        self.reqs = reqs
        self.excs = excs
        self.checks = []
        self.row_widgets = []
        self.selection_sets = {}
        self.groups = {}

        tabs = QtWidgets.QTabWidget()
        tabs.addTab(self._make_controls_tab(), "Controls")
        tabs.addTab(self._make_sets_tab(), "Sets")
        tabs.addTab(self._make_groups_tab(), "Groups")
        self.layout().addWidget(tabs)
        self.show()

    def _make_controls_tab(self):
        w = QtWidgets.QWidget()
        l = QtWidgets.QVBoxLayout(w)

        # Search & control row
        search_row = QtWidgets.QHBoxLayout()
        self.search_field = QtWidgets.QLineEdit()
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
        # new button: check all shown
        check_all_btn = QtWidgets.QPushButton("Check All Shown")
        check_all_btn.clicked.connect(self.check_all_shown)
        search_row.addWidget(check_all_btn)
        l.addLayout(search_row)

        # Set + Group creation row
        row = QtWidgets.QHBoxLayout()
        self.new_set_name = QtWidgets.QLineEdit()
        row.addWidget(self.new_set_name)
        btn_set = QtWidgets.QPushButton("Create Set from Checked")
        btn_set.clicked.connect(self.create_set)
        row.addWidget(btn_set)
        btn_group = QtWidgets.QPushButton("Create Group from Checked")
        btn_group.clicked.connect(self.create_group)
        row.addWidget(btn_group)
        l.addLayout(row)

        # Scroll area for controls
        self.scroll = QtWidgets.QScrollArea()
        self.cont = QtWidgets.QWidget()
        self.form = QtWidgets.QVBoxLayout(self.cont)
        self.scroll.setWidget(self.cont)
        self.scroll.setWidgetResizable(True)
        l.addWidget(self.scroll)

        all_children = cmds.listRelatives(self.root, allDescendents=True, fullPath=True) or []
        self.all_controls = sorted([c for c in all_children if matches(c.split('|')[-1], self.reqs, self.excs)])
        self.build_control_list(self.all_controls)
        return w

    def build_control_list(self, names):
        for row_w, _ in self.row_widgets:
            row_w.setParent(None)
        self.checks = []
        self.row_widgets = []
        for name in names:
            row = QtWidgets.QWidget()
            hl = QtWidgets.QHBoxLayout(row)
            chk = QtWidgets.QCheckBox()
            btn = QtWidgets.QPushButton(name.split('|')[-1])
            btn.clicked.connect(partial(cmds.select, name, add=True))
            hl.addWidget(chk)
            hl.addWidget(btn)
            self.form.addWidget(row)
            self.checks.append((chk, name))
            self.row_widgets.append((row, name))

    def check_all_shown(self):
        # check every checkbox whose row is visible
        for (chk, name), (row_w, _) in zip(self.checks, self.row_widgets):
            if row_w.isVisible():
                chk.setChecked(True)

    def create_set(self):
        name = self.new_set_name.text().strip()
        if not name:
            return
        items = [n for chk,n in self.checks if chk.isChecked()]
        if not items:
            return
        self.selection_sets[name] = items
        btn = QtWidgets.QPushButton(name)
        btn.clicked.connect(partial(cmds.select, items, add=True))
        self.sets_layout.addWidget(btn)

    def _make_sets_tab(self):
        w = QtWidgets.QWidget()
        scroll = QtWidgets.QScrollArea()
        container = QtWidgets.QWidget()
        self.sets_layout = QtWidgets.QVBoxLayout(container)
        scroll.setWidget(container)
        scroll.setWidgetResizable(True)
        layout = QtWidgets.QVBoxLayout(w)
        layout.addWidget(scroll)
        return w

    def _make_groups_tab(self):
        w = QtWidgets.QWidget()
        scroll = QtWidgets.QScrollArea()
        container = QtWidgets.QWidget()
        self.groups_layout = QtWidgets.QVBoxLayout(container)
        scroll.setWidget(container)
        scroll.setWidgetResizable(True)
        layout = QtWidgets.QVBoxLayout(w)
        layout.addWidget(scroll)
        return w

    def create_group(self):
        name = self.new_set_name.text().strip()
        if not name:
            return
        items = [n for chk,n in self.checks if chk.isChecked()]
        if not items:
            return
        self.groups[name] = items
        box = QtWidgets.QGroupBox(name)
        box.setCheckable(True)
        box.setChecked(True)
        v = QtWidgets.QVBoxLayout(box)
        for full in items:
            btn = QtWidgets.QPushButton(full.split('|')[-1])
            btn.clicked.connect(partial(cmds.select, full, add=True))
            v.addWidget(btn)
        def toggle_children(on):
            for i in range(v.count()):
                v.itemAt(i).widget().setVisible(on)
        box.toggled.connect(toggle_children)
        self.groups_layout.addWidget(box)

    def apply_search(self):
        terms = [t.strip() for t in self.search_field.text().split(',') if t.strip()]
        case = self.case_sensitive_cb.isChecked()
        include_all = self.include_all_cb.isChecked()
        if not terms:
            for row_w, _ in self.row_widgets:
                row_w.setVisible(True)
            return
        if not case:
            terms = [t.lower() for t in terms]
        for row_w, full in self.row_widgets:
            base = full.split('|')[-1]
            test = base if case else base.lower()
            show = all(term in test for term in terms) if include_all else any(term in test for term in terms)
            row_w.setVisible(show)

    def clear_search(self):
        self.search_field.clear()
        for row_w, _ in self.row_widgets:
            row_w.setVisible(True)

    def clear_checks(self):
        for chk, _ in self.checks:
            chk.setChecked(False)

# launch

def show_rig_selector_ui():
    try:
        for w in QtWidgets.QApplication.allWidgets():
            if isinstance(w, RigControlSelector):
                w.close()
    except:
        pass
    ui = RigControlSelector()
    ui.show()

show_rig_selector_ui()

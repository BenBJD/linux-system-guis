"""User interface for Linux user & group management."""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from linux_gui_core.widgets.preview_banner import LivePreviewBanner
from linux_gui_core.widgets.safety_dialog import SafetyExecutionDialog
from linux_gui_core.widgets.tooltips import format_tooltip
from usermgmt_gui.backend import UserInfo, UserManagementBackend
from usermgmt_gui.strings import tr


COMMON_SECURITY_GROUPS = [
    ("wheel", "Full administrative privileges via sudo/su (RHEL/Fedora/Arch convention).", "Critical / Root Privilege", "wheel"),
    ("sudo", "Full administrative privileges via sudo command (Debian/Ubuntu convention).", "Critical / Root Privilege", "sudo"),
    ("docker", "Read/write access to Docker daemon Unix socket. Root-equivalent privileges!", "Critical / Root Equivalent", "docker"),
    ("dialout", "Direct access to serial communication ports (/dev/ttyUSB*, /dev/ttyACM*). Essential for Arduino, 3D printers.", "Safe / Hardware Access", "dialout"),
    ("audio", "Direct access to audio hardware (/dev/snd/*).", "Safe", "audio"),
    ("video", "Direct access to video capture cards, webcams, and GPU devices (/dev/video*, /dev/dri/*).", "Safe", "video"),
    ("plugdev", "Allows mounting and unmounting removable USB storage devices without root.", "Safe", "plugdev"),
    ("input", "Direct access to kernel input event nodes (/dev/input/*). Needed for input remappers.", "Caution / Keylogging Risk", "input"),
    ("kvm", "Access to kernel virtualization acceleration devices (/dev/kvm).", "Safe / Virtualization", "kvm"),
]


class CreateUserDialog(QDialog):
    """Interactive modal dialog to configure and preview a new user account creation."""

    def __init__(self, available_groups: list[str], parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle(tr("dlg_create_user_title"))
        self.resize(640, 500)
        self.available_groups = available_groups
        self.selected_groups: set[str] = set()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        # 1. Top live preview banner
        self.preview_banner = LivePreviewBanner(
            title=tr("dlg_create_preview_title"),
            subtitle=tr("dlg_create_preview_subtitle"),
        )
        layout.addWidget(self.preview_banner)

        # Form fields
        form_group = QGroupBox(tr("group_account_details"))
        form_grid = QGridLayout(form_group)
        form_grid.setSpacing(6)

        # Username
        form_grid.addWidget(QLabel(tr("lbl_username")), 0, 0)
        self.txt_username = QLineEdit()
        self.txt_username.setPlaceholderText(tr("placeholder_username"))
        self.txt_username.setToolTip(format_tooltip(
            tr("tooltip_username_title"),
            tr("tooltip_username_syntax"),
            tr("tooltip_username_desc"),
            tr("tooltip_username_impact"),
            tr("tooltip_username_example"),
        ))
        self.txt_username.textChanged.connect(self._update_preview)
        form_grid.addWidget(self.txt_username, 0, 1)

        # Full Name / GECOS
        form_grid.addWidget(QLabel(tr("lbl_gecos")), 0, 2)
        self.txt_gecos = QLineEdit()
        self.txt_gecos.setPlaceholderText(tr("placeholder_gecos"))
        self.txt_gecos.setToolTip(format_tooltip(
            tr("tooltip_gecos_title"),
            tr("tooltip_gecos_syntax"),
            tr("tooltip_gecos_desc"),
            tr("tooltip_gecos_impact"),
            tr("tooltip_gecos_example"),
        ))
        self.txt_gecos.textChanged.connect(self._update_preview)
        form_grid.addWidget(self.txt_gecos, 0, 3)

        # Login Shell
        form_grid.addWidget(QLabel(tr("lbl_shell")), 1, 0)
        self.cmb_shell = QComboBox()
        self.cmb_shell.setEditable(True)
        self.cmb_shell.addItems([
            "/bin/bash",
            "/usr/bin/zsh",
            "/usr/bin/fish",
            "/bin/sh",
            "/usr/bin/nologin",
            "/usr/sbin/nologin",
        ])
        self.cmb_shell.setToolTip(format_tooltip(
            tr("tooltip_shell_title"),
            tr("tooltip_shell_syntax"),
            tr("tooltip_shell_desc"),
        ))
        self.cmb_shell.currentTextChanged.connect(self._update_preview)
        form_grid.addWidget(self.cmb_shell, 1, 1)

        # Create home directory checkbox
        self.chk_home = QCheckBox(tr("chk_home"))
        self.chk_home.setChecked(True)
        self.chk_home.setToolTip(format_tooltip(
            tr("tooltip_home_title"),
            tr("tooltip_home_syntax"),
            tr("tooltip_home_desc"),
            tr("tooltip_home_impact"),
        ))
        self.chk_home.toggled.connect(self._update_preview)
        form_grid.addWidget(self.chk_home, 1, 2, 1, 2)

        layout.addWidget(form_group)

        # Initial Groups
        grp_box = QGroupBox(tr("group_initial_groups"))
        grp_grid = QGridLayout(grp_box)
        grp_grid.setSpacing(6)

        self.group_checkboxes: dict[str, QCheckBox] = {}
        for idx, (g_name, desc, impact, example) in enumerate(COMMON_SECURITY_GROUPS):
            if g_name in self.available_groups or g_name in ("wheel", "sudo", "docker"):
                chk = QCheckBox(g_name)
                chk.setToolTip(format_tooltip(tr("tooltip_group_prefix", group=g_name), tr("tooltip_group_syntax", group=g_name), desc, impact, example))
                chk.toggled.connect(self._update_preview)
                self.group_checkboxes[g_name] = chk
                row = len(self.group_checkboxes) // 4
                col = len(self.group_checkboxes) % 4
                grp_grid.addWidget(chk, row, col)

        layout.addWidget(grp_box)

        # Dialog Buttons
        btn_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btn_box.button(QDialogButtonBox.StandardButton.Ok).setText(tr("btn_create_account"))
        btn_box.button(QDialogButtonBox.StandardButton.Ok).setObjectName("primaryBtn")
        btn_box.accepted.connect(self._validate_and_accept)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

        self._update_preview()

    def _update_preview(self) -> None:
        uname = self.txt_username.text().strip().lower() or "<username>"
        shell = self.cmb_shell.currentText().strip()
        gecos = self.txt_gecos.text().strip()
        create_home = self.chk_home.isChecked()
        groups = [name for name, chk in self.group_checkboxes.items() if chk.isChecked()]

        cmd = UserManagementBackend.build_add_user_cmd(
            username=uname,
            shell=shell,
            groups=groups,
            gecos=gecos,
            create_home=create_home,
        )
        self.preview_banner.set_text(cmd)

    def _validate_and_accept(self) -> None:
        uname = self.txt_username.text().strip().lower()
        if not uname:
            QMessageBox.warning(self, tr("title_invalid_username"), tr("msg_empty_username"))
            self.txt_username.setFocus()
            return

        import re
        if not re.match(r"^[a-z_][a-z0-9_-]*$", uname):
            QMessageBox.warning(
                self,
                tr("title_invalid_username"),
                tr("msg_invalid_username_regex"),
            )
            self.txt_username.setFocus()
            return

        self.accept()

    def get_command_string(self) -> str:
        return self.preview_banner.get_text()

    def get_username(self) -> str:
        return self.txt_username.text().strip().lower()


class UserMgmtMainWindow(QMainWindow):
    """Main window for inspecting and managing Linux users and groups."""

    SECURITY_GROUPS = COMMON_SECURITY_GROUPS

    def __init__(self):
        super().__init__()
        self.setWindowTitle(tr("window_title"))
        self.resize(1280, 720)
        self.setMinimumSize(920, 620)

        self.users: list[UserInfo] = []
        self.all_system_groups: list[str] = []
        self.active_user: UserInfo | None = None
        self._is_updating_ui: bool = False
        self.selected_group_set: set[str] = set()

        self._init_ui()
        self.reload_users()

    def _init_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)

        # 1. Top Live Preview Banner
        self.preview_banner = LivePreviewBanner(
            title=tr("preview_title"),
            subtitle=tr("preview_subtitle"),
        )
        layout.addWidget(self.preview_banner)

        # 2. Filter & Options Bar
        filter_bar = QHBoxLayout()
        filter_bar.setSpacing(8)
        filter_bar.addWidget(QLabel(tr("lbl_filter_accounts")))
        self.txt_filter = QLineEdit()
        self.txt_filter.setPlaceholderText(tr("placeholder_filter_accounts"))
        self.txt_filter.textChanged.connect(self._filter_users)
        filter_bar.addWidget(self.txt_filter)

        self.chk_show_system = QCheckBox(tr("chk_show_system"))
        self.chk_show_system.setToolTip(tr("tooltip_show_system"))
        self.chk_show_system.toggled.connect(self.reload_users)
        filter_bar.addWidget(self.chk_show_system)

        filter_bar.addStretch()

        btn_refresh = QPushButton(tr("btn_refresh"))
        btn_refresh.clicked.connect(self.reload_users)
        filter_bar.addWidget(btn_refresh)

        layout.addLayout(filter_bar)

        # 3. Main Splitter: Users Table vs User Details & Group Checkboxes
        splitter = QSplitter(Qt.Orientation.Vertical)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels([
            tr("col_username"),
            tr("col_uid"),
            tr("col_gecos"),
            tr("col_shell"),
            tr("col_home"),
            tr("col_groups"),
        ])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        self.table.setColumnWidth(0, 150)
        self.table.setColumnWidth(1, 70)
        self.table.setColumnWidth(3, 150)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.itemSelectionChanged.connect(self._on_user_selected)
        splitter.addWidget(self.table)

        # Bottom Form Container with ScrollArea
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)

        form_widget = QWidget()
        form_layout = QVBoxLayout(form_widget)
        form_layout.setContentsMargins(4, 4, 4, 4)
        form_layout.setSpacing(8)

        # User details fields
        details_group = QGroupBox(tr("group_user_profile"))
        details_grid = QGridLayout(details_group)
        details_grid.setSpacing(6)

        details_grid.addWidget(QLabel(tr("lbl_username")), 0, 0)
        self.lbl_uname = QLabel("-")
        self.lbl_uname.setStyleSheet("font-weight: bold; color: #6899e6; font-size: 13px;")
        details_grid.addWidget(self.lbl_uname, 0, 1)

        details_grid.addWidget(QLabel(tr("lbl_shell")), 0, 2)
        self.cmb_shell = QComboBox()
        self.cmb_shell.setEditable(True)
        self.cmb_shell.addItems([
            "/bin/bash",
            "/usr/bin/zsh",
            "/usr/bin/fish",
            "/bin/sh",
            "/usr/bin/nologin",
            "/usr/sbin/nologin",
            "/bin/false",
        ])
        self.cmb_shell.setToolTip(format_tooltip(
            tr("tooltip_user_shell_title"),
            tr("tooltip_user_shell_syntax"),
            tr("tooltip_user_shell_desc"),
            tr("tooltip_user_shell_impact"),
            tr("tooltip_user_shell_example"),
        ))
        self.cmb_shell.currentTextChanged.connect(self._on_form_modified)
        details_grid.addWidget(self.cmb_shell, 0, 3)

        form_layout.addWidget(details_group)

        # Curated Common Groups Box
        curated_box = QGroupBox(tr("group_common_groups"))
        curated_grid = QGridLayout(curated_box)
        curated_grid.setSpacing(8)

        self.curated_checkboxes: dict[str, QCheckBox] = {}
        for idx, (grp_name, desc, sec_impact, example) in enumerate(self.SECURITY_GROUPS):
            chk = QCheckBox(grp_name)
            chk.setToolTip(format_tooltip(tr("tooltip_group_prefix", group=grp_name), tr("tooltip_member_of", group=grp_name), desc, sec_impact, example))
            chk.toggled.connect(lambda checked, g=grp_name: self._on_curated_group_toggled(g, checked))
            self.curated_checkboxes[grp_name] = chk
            row = idx // 4
            col = idx % 4
            curated_grid.addWidget(chk, row, col)

        form_layout.addWidget(curated_box)

        # All System Groups Search & Toggle Area
        all_groups_box = QGroupBox(tr("group_all_groups"))
        all_groups_layout = QVBoxLayout(all_groups_box)
        all_groups_layout.setSpacing(6)

        search_bar = QHBoxLayout()
        search_bar.addWidget(QLabel(tr("lbl_search_groups")))
        self.txt_group_search = QLineEdit()
        self.txt_group_search.setPlaceholderText(tr("placeholder_search_groups"))
        self.txt_group_search.textChanged.connect(self._filter_all_groups_list)
        search_bar.addWidget(self.txt_group_search)
        all_groups_layout.addLayout(search_bar)

        self.list_all_groups = QListWidget()
        self.list_all_groups.setFixedHeight(120)
        self.list_all_groups.itemChanged.connect(self._on_list_group_item_changed)
        all_groups_layout.addWidget(self.list_all_groups)

        form_layout.addWidget(all_groups_box)

        scroll.setWidget(form_widget)
        splitter.addWidget(scroll)
        layout.addWidget(splitter)

        # Bottom Action Bar
        action_bar = QHBoxLayout()
        action_bar.setSpacing(8)
        btn_add = QPushButton(tr("btn_create_new_user"))
        btn_add.clicked.connect(self._create_new_user)
        action_bar.addWidget(btn_add)

        btn_del = QPushButton(tr("btn_delete_user"))
        btn_del.clicked.connect(self._delete_selected_user)
        action_bar.addWidget(btn_del)

        action_bar.addStretch()

        self.btn_apply = QPushButton(tr("btn_apply_groups"))
        self.btn_apply.setObjectName("primaryBtn")
        self.btn_apply.clicked.connect(self._apply_group_changes)
        action_bar.addWidget(self.btn_apply)

        layout.addLayout(action_bar)

    def reload_users(self) -> None:
        include_sys = self.chk_show_system.isChecked()
        self.users = UserManagementBackend.list_users(include_system=include_sys)
        self.all_system_groups = UserManagementBackend.list_all_groups()
        self._populate_table()

    def _populate_table(self) -> None:
        self._is_updating_ui = True
        self.table.setRowCount(0)
        row = 0
        for u in self.users:
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(u.username))
            self.table.setItem(row, 1, QTableWidgetItem(str(u.uid)))
            self.table.setItem(row, 2, QTableWidgetItem(u.gecos))
            self.table.setItem(row, 3, QTableWidgetItem(u.shell))
            self.table.setItem(row, 4, QTableWidgetItem(u.home))
            self.table.setItem(row, 5, QTableWidgetItem(", ".join(u.groups)))
            self.table.item(row, 0).setData(Qt.ItemDataRole.UserRole, u)
            row += 1

        self._is_updating_ui = False
        if self.table.rowCount() > 0:
            self.table.selectRow(0)

    def _filter_users(self, text: str) -> None:
        needle = text.lower()
        for row in range(self.table.rowCount()):
            u_item = self.table.item(row, 0)
            uid_item = self.table.item(row, 1)
            matches = (u_item and needle in u_item.text().lower()) or (uid_item and needle in uid_item.text())
            self.table.setRowHidden(row, not matches)

    def _on_user_selected(self) -> None:
        if self._is_updating_ui:
            return
        selected = self.table.selectedItems()
        if not selected:
            return
        row = selected[0].row()
        user: UserInfo = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        self.active_user = user
        self.selected_group_set = set(user.groups)

        self._is_updating_ui = True
        self.lbl_uname.setText(f"{user.username} (UID {user.uid})")
        self.cmb_shell.setCurrentText(user.shell)

        # Update curated checkboxes
        for g_name, chk in self.curated_checkboxes.items():
            chk.setChecked(g_name in self.selected_group_set)

        # Update all groups list
        self._populate_all_groups_list()

        self._is_updating_ui = False
        self._update_preview()

    def _populate_all_groups_list(self) -> None:
        self.list_all_groups.clear()
        for g in self.all_system_groups:
            item = QListWidgetItem(g)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            is_checked = g in self.selected_group_set
            item.setCheckState(Qt.CheckState.Checked if is_checked else Qt.CheckState.Unchecked)
            self.list_all_groups.addItem(item)

    def _filter_all_groups_list(self, text: str) -> None:
        needle = text.lower()
        for i in range(self.list_all_groups.count()):
            item = self.list_all_groups.item(i)
            item.setHidden(needle not in item.text().lower())

    def _on_curated_group_toggled(self, group_name: str, checked: bool) -> None:
        if self._is_updating_ui:
            return
        if checked:
            self.selected_group_set.add(group_name)
        else:
            self.selected_group_set.discard(group_name)

        self._is_updating_ui = True
        for i in range(self.list_all_groups.count()):
            item = self.list_all_groups.item(i)
            if item.text() == group_name:
                item.setCheckState(Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked)
                break
        self._is_updating_ui = False
        self._update_preview()

    def _on_list_group_item_changed(self, item: QListWidgetItem) -> None:
        if self._is_updating_ui:
            return
        g_name = item.text()
        checked = item.checkState() == Qt.CheckState.Checked
        if checked:
            self.selected_group_set.add(g_name)
        else:
            self.selected_group_set.discard(g_name)

        if g_name in self.curated_checkboxes:
            self._is_updating_ui = True
            self.curated_checkboxes[g_name].setChecked(checked)
            self._is_updating_ui = False

        self._update_preview()

    def _on_form_modified(self) -> None:
        if self._is_updating_ui or not self.active_user:
            return
        self._update_preview()

    def _update_preview(self) -> None:
        if not self.active_user:
            return
        sorted_groups = sorted(list(self.selected_group_set))
        cmd = UserManagementBackend.build_modify_groups_cmd(self.active_user.username, sorted_groups)
        self.preview_banner.set_text(cmd)

    def _create_new_user(self) -> None:
        dlg = CreateUserDialog(self.all_system_groups, self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return

        cmd = dlg.get_command_string()
        clean_uname = dlg.get_username()
        self.preview_banner.set_text(cmd)

        safety_dlg = SafetyExecutionDialog(
            title=tr("dialog_confirm_create_title"),
            target_path_or_command=cmd,
            safety_notes=[
                tr("note_create_account", username=clean_uname),
                tr("note_elevate_useradd"),
            ],
            parent=self,
        )
        if safety_dlg.exec() == SafetyExecutionDialog.DialogCode.Accepted:
            res = UserManagementBackend.execute_command_string(cmd)
            if res.success:
                QMessageBox.information(
                    self,
                    tr("title_user_created"),
                    tr("msg_user_created_success", username=clean_uname, command=cmd),
                )
                self.reload_users()
            else:
                QMessageBox.critical(self, tr("title_creation_failed"), tr("msg_creation_failed", error=res.stderr or res.stdout))

    def _delete_selected_user(self) -> None:
        if not self.active_user:
            return
        cmd = UserManagementBackend.build_del_user_cmd(self.active_user.username, remove_home=True)
        dlg = SafetyExecutionDialog(
            title=tr("dialog_delete_title", username=self.active_user.username),
            target_path_or_command=cmd,
            safety_notes=[
                tr("note_delete_account", username=self.active_user.username),
                tr("note_action_irreversible"),
            ],
            parent=self,
        )
        if dlg.exec() == SafetyExecutionDialog.DialogCode.Accepted:
            res = UserManagementBackend.execute_command_string(cmd)
            if res.success:
                QMessageBox.information(self, tr("title_deleted"), tr("msg_deleted_success", username=self.active_user.username))
                self.reload_users()
            else:
                QMessageBox.critical(self, tr("title_delete_failed"), tr("msg_delete_failed", error=res.stderr))

    def _apply_group_changes(self) -> None:
        if not self.active_user:
            return
        sorted_groups = sorted(list(self.selected_group_set))
        cmd = UserManagementBackend.build_modify_groups_cmd(self.active_user.username, sorted_groups)

        dlg = SafetyExecutionDialog(
            title=tr("dialog_apply_groups_title"),
            target_path_or_command=cmd,
            safety_notes=[
                tr("note_modify_user_groups", username=self.active_user.username),
                tr("note_total_groups", count=len(sorted_groups)),
                tr("note_relogin_required"),
            ],
            parent=self,
        )
        if dlg.exec() == SafetyExecutionDialog.DialogCode.Accepted:
            res = UserManagementBackend.execute_command_string(cmd)
            if res.success:
                QMessageBox.information(self, tr("title_success"), tr("msg_groups_updated", command=cmd))
                self.reload_users()
            else:
                QMessageBox.critical(self, tr("title_update_failed"), tr("msg_update_failed", error=res.stderr))

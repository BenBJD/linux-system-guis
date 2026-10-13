"""User interface for Sudoers Configuration manager with visudo validation and sudoers.d support."""

import json
import os
import shlex
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from linux_gui_core.runner.executor import SafeExecutor
from linux_gui_core.runner.package_manager import PackageManagerInspector, PackageOwnership
from linux_gui_core.widgets.package_badge import PackageOwnershipBadge
from linux_gui_core.widgets.preview_banner import LivePreviewBanner
from linux_gui_core.widgets.safety_dialog import SafetyExecutionDialog, generate_diff
from linux_gui_core.widgets.tooltips import format_tooltip
from sudoers_gui.parser import SudoersParser, SudoersRule
from sudoers_gui.strings import tr


class SudoersMainWindow(QMainWindow):
    """Main application window for inspecting and modifying sudoers privileges."""

    DEFAULT_DIR = "/etc/sudoers.d"

    COMMON_COMMAND_PRESETS = [
        ("ALL", "All administrative commands on the system"),
        ("/usr/bin/systemctl restart *, /usr/bin/systemctl status *", "Service management (restart & status only)"),
        ("/usr/bin/pacman -Syu", "System package upgrades (Arch Linux)"),
        ("/usr/bin/apt update, /usr/bin/apt upgrade", "Package updates (Debian/Ubuntu)"),
        ("/usr/bin/reboot, /usr/bin/poweroff", "System reboot and shutdown"),
    ]

    def __init__(self, target_dir: str = DEFAULT_DIR):
        super().__init__()
        self.target_dir = target_dir
        self.setWindowTitle(tr("window_title"))
        self.resize(1280, 720)
        self.setMinimumSize(960, 680)

        self.current_file_path: str = ""
        self.rules: list[SudoersRule] = []
        self.original_raw: str = ""
        self.current_ownership = PackageOwnership(is_managed=False)
        self._cached_contents: dict[str, str] = {}
        self._is_updating_ui: bool = False
        self._is_read_restricted: bool = False

        self._init_ui()
        self._load_sudoers_files()

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
        self.preview_banner.diffRequested.connect(self._inspect_diff)
        layout.addWidget(self.preview_banner)

        # 2. File Selection Bar
        file_bar = QHBoxLayout()
        file_bar.addWidget(QLabel(tr("lbl_sudoers_file")))
        self.cmb_files = QComboBox()
        self.cmb_files.setMinimumWidth(280)
        self.cmb_files.currentIndexChanged.connect(self._on_file_selected)
        file_bar.addWidget(self.cmb_files)

        self.package_badge = PackageOwnershipBadge()
        file_bar.addWidget(self.package_badge)

        self.btn_unlock_read = QPushButton(tr("btn_unlock_read"))
        self.btn_unlock_read.setToolTip(format_tooltip(
            tr("tooltip_unlock_read_title"),
            tr("tooltip_unlock_read_cmd"),
            tr("tooltip_unlock_read_desc"),
            tr("tooltip_unlock_read_safety"),
        ))
        self.btn_unlock_read.setVisible(False)
        self.btn_unlock_read.clicked.connect(self._read_all_with_root)
        file_bar.addWidget(self.btn_unlock_read)

        btn_refresh_all = QPushButton(tr("btn_refresh_all"))
        btn_refresh_all.setToolTip(tr("tooltip_refresh_all"))
        btn_refresh_all.clicked.connect(self._read_all_with_root)
        file_bar.addWidget(btn_refresh_all)

        btn_new_file = QPushButton(tr("btn_new_file"))
        btn_new_file.setToolTip(tr("tooltip_new_file"))
        btn_new_file.clicked.connect(self._create_new_dropin_file)
        file_bar.addWidget(btn_new_file)

        self.btn_delete_file = QPushButton(tr("btn_delete_file"))
        self.btn_delete_file.setToolTip(tr("tooltip_delete_file"))
        self.btn_delete_file.clicked.connect(self._delete_dropin_file)
        self.btn_delete_file.setEnabled(False)
        file_bar.addWidget(self.btn_delete_file)

        file_bar.addStretch()

        btn_validate_syntax = QPushButton(tr("btn_validate_syntax"))
        btn_validate_syntax.setToolTip(format_tooltip(
            tr("tooltip_validate_syntax_title"),
            tr("tooltip_validate_syntax_cmd"),
            tr("tooltip_validate_syntax_desc"),
            tr("tooltip_validate_syntax_safety"),
        ))
        btn_validate_syntax.clicked.connect(self._validate_current_syntax)
        file_bar.addWidget(btn_validate_syntax)

        layout.addLayout(file_bar)

        # 3. Main Tab Widget: Visual Rule Builder vs Raw File Editor
        self.tabs = QTabWidget()

        # Tab 1: Visual Rule Builder
        builder_widget = QWidget()
        builder_layout = QVBoxLayout(builder_widget)
        builder_layout.setContentsMargins(0, 6, 0, 0)
        builder_layout.setSpacing(6)

        splitter = QSplitter(Qt.Orientation.Vertical)

        # Rules Table
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels([
            tr("col_entity"),
            tr("col_hosts"),
            tr("col_runas"),
            tr("col_password_req"),
            tr("col_commands"),
        ])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self.table.setColumnWidth(0, 200)
        self.table.setColumnWidth(1, 120)
        self.table.setColumnWidth(2, 140)
        self.table.setColumnWidth(3, 160)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.itemSelectionChanged.connect(self._on_table_selection_changed)
        splitter.addWidget(self.table)

        # Bottom Form Container with ScrollArea
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)

        form_widget = QWidget()
        form_layout = QVBoxLayout(form_widget)
        form_layout.setContentsMargins(2, 4, 2, 4)
        form_layout.setSpacing(6)

        # Privilege Subject Box
        subject_group = QGroupBox(tr("group_privilege_subject"))
        subject_grid = QGridLayout(subject_group)
        subject_grid.setSpacing(6)

        self.rb_user = QRadioButton(tr("rb_user"))
        self.rb_group = QRadioButton(tr("rb_group"))
        self.rb_group.setChecked(True)
        self.rb_user.toggled.connect(self._on_rule_modified)
        self.rb_group.toggled.connect(self._on_rule_modified)
        subject_grid.addWidget(self.rb_user, 0, 0)
        subject_grid.addWidget(self.rb_group, 0, 1)

        subject_grid.addWidget(QLabel(tr("lbl_account_name")), 0, 2)
        self.txt_entity = QLineEdit("wheel")
        self.txt_entity.setPlaceholderText(tr("placeholder_entity"))
        self.txt_entity.setToolTip(format_tooltip(
            tr("tooltip_entity_title"),
            tr("tooltip_entity_syntax"),
            tr("tooltip_entity_desc"),
            tr("tooltip_entity_impact"),
            tr("tooltip_entity_example"),
        ))
        self.txt_entity.textChanged.connect(self._on_rule_modified)
        subject_grid.addWidget(self.txt_entity, 0, 3)

        form_layout.addWidget(subject_group)

        # Execution Scope Box
        scope_group = QGroupBox(tr("group_execution_scope"))
        scope_grid = QGridLayout(scope_group)
        scope_grid.setSpacing(6)

        scope_grid.addWidget(QLabel(tr("lbl_hosts")), 0, 0)
        self.txt_hosts = QLineEdit("ALL")
        self.txt_hosts.setToolTip(format_tooltip(
            tr("tooltip_hosts_title"),
            tr("tooltip_hosts_syntax"),
            tr("tooltip_hosts_desc"),
            tr("tooltip_hosts_impact"),
        ))
        self.txt_hosts.textChanged.connect(self._on_rule_modified)
        scope_grid.addWidget(self.txt_hosts, 0, 1)

        scope_grid.addWidget(QLabel(tr("lbl_runas_user")), 0, 2)
        self.txt_runas_user = QLineEdit("ALL")
        self.txt_runas_user.setToolTip(format_tooltip(
            tr("tooltip_runas_user_title"),
            tr("tooltip_runas_user_syntax"),
            tr("tooltip_runas_user_desc"),
            tr("tooltip_runas_user_impact"),
        ))
        self.txt_runas_user.textChanged.connect(self._on_rule_modified)
        scope_grid.addWidget(self.txt_runas_user, 0, 3)

        scope_grid.addWidget(QLabel(tr("lbl_runas_group")), 1, 2)
        self.txt_runas_group = QLineEdit("ALL")
        self.txt_runas_group.setToolTip(format_tooltip(
            tr("tooltip_runas_group_title"),
            tr("tooltip_runas_group_syntax"),
            tr("tooltip_runas_group_desc"),
        ))
        self.txt_runas_group.textChanged.connect(self._on_rule_modified)
        scope_grid.addWidget(self.txt_runas_group, 1, 3)

        form_layout.addWidget(scope_group)

        # Authentication & Commands Box
        auth_group = QGroupBox(tr("group_auth_commands"))
        auth_grid = QGridLayout(auth_group)
        auth_grid.setSpacing(6)

        self.chk_nopasswd = QCheckBox(tr("chk_nopasswd"))
        self.chk_nopasswd.setToolTip(format_tooltip(
            tr("tooltip_nopasswd_title"),
            tr("tooltip_nopasswd_syntax"),
            tr("tooltip_nopasswd_desc"),
            tr("tooltip_nopasswd_impact"),
            tr("tooltip_nopasswd_example"),
        ))
        self.chk_nopasswd.toggled.connect(self._on_rule_modified)
        auth_grid.addWidget(self.chk_nopasswd, 0, 0, 1, 2)

        auth_grid.addWidget(QLabel(tr("lbl_commands")), 1, 0)
        self.txt_commands = QLineEdit("ALL")
        self.txt_commands.setPlaceholderText(tr("placeholder_commands"))
        self.txt_commands.setToolTip(format_tooltip(
            tr("tooltip_commands_title"),
            tr("tooltip_commands_syntax"),
            tr("tooltip_commands_desc"),
            tr("tooltip_commands_impact"),
        ))
        self.txt_commands.textChanged.connect(self._on_rule_modified)
        auth_grid.addWidget(self.txt_commands, 1, 1, 1, 3)

        # Command presets bar
        preset_bar = QHBoxLayout()
        preset_bar.addWidget(QLabel(tr("lbl_presets")))
        self.cmb_presets = QComboBox()
        for cmd_val, desc in self.COMMON_COMMAND_PRESETS:
            self.cmb_presets.addItem(f"{cmd_val} ({desc})", cmd_val)
        btn_apply_preset = QPushButton(tr("btn_apply_preset"))
        btn_apply_preset.clicked.connect(self._apply_command_preset)
        preset_bar.addWidget(self.cmb_presets)
        preset_bar.addWidget(btn_apply_preset)
        preset_bar.addStretch()
        auth_grid.addLayout(preset_bar, 2, 0, 1, 4)

        form_layout.addWidget(auth_group)

        scroll.setWidget(form_widget)
        splitter.addWidget(scroll)
        builder_layout.addWidget(splitter)
        self.tabs.addTab(builder_widget, tr("tab_visual_builder"))

        # Tab 2: Raw Sudoers Text Editor
        raw_widget = QWidget()
        raw_layout = QVBoxLayout(raw_widget)
        raw_layout.setContentsMargins(6, 6, 6, 6)
        raw_layout.setSpacing(6)

        lbl_raw_help = QLabel(tr("lbl_raw_help"))
        lbl_raw_help.setStyleSheet("color: #9498a1; font-size: 11px;")
        raw_layout.addWidget(lbl_raw_help)

        self.raw_editor = QPlainTextEdit()
        font = QFont("Monospace")
        font.setStyleHint(QFont.StyleHint.Monospace)
        font.setPointSize(11)
        self.raw_editor.setFont(font)
        self.raw_editor.setStyleSheet(
            "QPlainTextEdit { background-color: #18191c; color: #e3e5e8; "
            "border: 1px solid #3a3d45; border-radius: 3px; padding: 6px; }"
        )
        self.raw_editor.textChanged.connect(self._on_raw_editor_text_changed)
        raw_layout.addWidget(self.raw_editor)

        self.tabs.addTab(raw_widget, tr("tab_raw_editor"))
        self.tabs.currentChanged.connect(self._on_tab_changed)
        layout.addWidget(self.tabs)

        # 4. Bottom Action Bar
        action_bar = QHBoxLayout()
        btn_add_rule = QPushButton(tr("btn_add_rule"))
        btn_add_rule.clicked.connect(self._add_new_rule)
        action_bar.addWidget(btn_add_rule)

        btn_del_rule = QPushButton(tr("btn_remove_rule"))
        btn_del_rule.clicked.connect(self._remove_selected_rule)
        action_bar.addWidget(btn_del_rule)

        action_bar.addStretch()

        btn_save = QPushButton(tr("btn_save_file"))
        btn_save.setObjectName("primaryBtn")
        btn_save.setToolTip(tr("tooltip_save_file"))
        btn_save.clicked.connect(self._save_sudoers_file)
        action_bar.addWidget(btn_save)

        layout.addLayout(action_bar)

    def _load_sudoers_files(self) -> None:
        self.cmb_files.blockSignals(True)
        self.cmb_files.clear()
        files = SudoersParser.list_sudoers_files(self.target_dir)
        for f in files:
            self.cmb_files.addItem(f)
        self.cmb_files.blockSignals(False)
        if self.cmb_files.count() > 0:
            self._on_file_selected()

    def _read_all_with_root(self) -> None:
        """Batch-read /etc/sudoers and all /etc/sudoers.d/ drop-in files in a SINGLE elevated prompt.

        Avoids repeated password dialogs when browsing multiple files.
        """
        script_code = (
            "import json, os\n"
            "data = {'files': {}}\n"
            "p = '/etc/sudoers'\n"
            "if os.path.exists(p):\n"
            "    try:\n"
            "        with open(p, 'r', encoding='utf-8', errors='replace') as f:\n"
            "            data['files'][p] = f.read()\n"
            "    except Exception as e:\n"
            "        data['files'][p] = f'# Error reading {p}: {e}'\n"
            "d = '/etc/sudoers.d'\n"
            "if os.path.isdir(d):\n"
            "    try:\n"
            "        for entry in sorted(os.listdir(d)):\n"
            "            if '.' not in entry and not entry.endswith('~') and not entry.startswith('.'):\n"
            "                full_p = os.path.join(d, entry)\n"
            "                if os.path.isfile(full_p):\n"
            "                    try:\n"
            "                        with open(full_p, 'r', encoding='utf-8', errors='replace') as f:\n"
            "                            data['files'][full_p] = f.read()\n"
            "                    except Exception as e:\n"
            "                        data['files'][full_p] = f'# Error reading {full_p}: {e}'\n"
            "    except Exception:\n"
            "        pass\n"
            "print('__SUDOERS_JSON_START__')\n"
            "print(json.dumps(data))\n"
            "print('__SUDOERS_JSON_END__')\n"
        )
        res = SafeExecutor.run_command(
            ["bash", "-c", f"python3 -c {shlex.quote(script_code)}"],
            elevated=True,
        )
        if res.success and "__SUDOERS_JSON_START__" in res.stdout:
            start = res.stdout.find("__SUDOERS_JSON_START__")
            end = res.stdout.find("__SUDOERS_JSON_END__")
            json_str = res.stdout[start + len("__SUDOERS_JSON_START__"):end].strip()
            try:
                payload = json.loads(json_str)
                files_dict = payload.get("files", {})
                for fpath, fcontent in files_dict.items():
                    self._cached_contents[fpath] = fcontent

                current = self.current_file_path or "/etc/sudoers"
                self.cmb_files.blockSignals(True)
                self.cmb_files.clear()
                file_list = sorted(self._cached_contents.keys())
                if "/etc/sudoers" in file_list:
                    file_list.remove("/etc/sudoers")
                    file_list.insert(0, "/etc/sudoers")
                for f in file_list:
                    self.cmb_files.addItem(f)
                if self.cmb_files.findText(current) != -1:
                    self.cmb_files.setCurrentText(current)
                elif self.cmb_files.count() > 0:
                    self.cmb_files.setCurrentIndex(0)
                self.cmb_files.blockSignals(False)

                self._is_read_restricted = False
                self.btn_unlock_read.setVisible(False)
                self._on_file_selected()
            except Exception as e:
                QMessageBox.critical(self, tr("title_parse_error"), tr("msg_parse_error", error=e))
        else:
            QMessageBox.warning(self, tr("title_read_failed"), tr("msg_read_failed", error=res.stderr or res.stdout))

    def _on_file_selected(self) -> None:
        path = self.cmb_files.currentText().strip()
        if not path:
            return
        self.current_file_path = path

        self.current_ownership = PackageManagerInspector.check_file_owner(path)
        self.package_badge.update_status(self.current_ownership, path)

        self.rules = []
        self._is_read_restricted = False
        self.btn_unlock_read.setVisible(False)

        # Update delete button: only drop-in files in target_dir can be deleted (never /etc/sudoers)
        is_dropin = (path != "/etc/sudoers" and path.startswith(self.target_dir))
        self.btn_delete_file.setEnabled(is_dropin)

        # 1. First check in-memory batch cache
        if path in self._cached_contents:
            self.original_raw = self._cached_contents[path]
            self.rules = [SudoersParser.parse_line(line) for line in self.original_raw.splitlines()]
            self._is_read_restricted = False
            self.btn_unlock_read.setVisible(False)
            self.preview_banner.set_subtitle(tr("preview_sub_mod"))
        else:
            try:
                with open(path, "r", encoding="utf-8") as f:
                    self.original_raw = f.read()
                    self._cached_contents[path] = self.original_raw
                    self.rules = [SudoersParser.parse_line(line) for line in self.original_raw.splitlines()]
                    self._is_read_restricted = False
                    self.btn_unlock_read.setVisible(False)
                    self.preview_banner.set_subtitle(tr("preview_sub_mod"))
            except PermissionError:
                self._is_read_restricted = True
                self.btn_unlock_read.setVisible(True)
                self.original_raw = (
                    f"# {path} is protected (read access restricted to root).\n"
                    "# Click 'Read as Root' above to scan /etc/sudoers and all /etc/sudoers.d/ files in one single prompt."
                )
                self.rules = [SudoersRule(raw_line=self.original_raw, is_comment=True)]
                self.preview_banner.set_text(tr("preview_text_root_req", path=path))
                self.preview_banner.set_subtitle(tr("preview_sub_root_req"))
            except FileNotFoundError:
                # Newly created drop-in file
                self.original_raw = ""
                self._cached_contents[path] = ""
                self.rules = [
                    SudoersRule(
                        is_group=True,
                        entity="wheel",
                        hosts="ALL",
                        runas_user="ALL",
                        runas_group="ALL",
                        nopasswd=False,
                        commands="ALL",
                    )
                ]
                self._is_read_restricted = False
                self.btn_unlock_read.setVisible(False)
                self.preview_banner.set_subtitle(tr("preview_sub_dropin"))

        self._populate_table()
        self._sync_raw_from_rules()

    def _populate_table(self) -> None:
        self._is_updating_ui = True
        self.table.setRowCount(0)
        row = 0
        for rule in self.rules:
            if rule.is_comment or not rule.to_line().strip():
                continue
            self.table.insertRow(row)
            ent_display = f"%{rule.entity}" if rule.is_group else rule.entity
            self.table.setItem(row, 0, QTableWidgetItem(ent_display))
            self.table.setItem(row, 1, QTableWidgetItem(rule.hosts))
            runas_str = f"({rule.runas_user}:{rule.runas_group})" if rule.runas_group else f"({rule.runas_user})"
            self.table.setItem(row, 2, QTableWidgetItem(runas_str))
            pass_str = tr("val_nopasswd") if rule.nopasswd else tr("val_password_prompt")
            self.table.setItem(row, 3, QTableWidgetItem(pass_str))
            self.table.setItem(row, 4, QTableWidgetItem(rule.commands))
            self.table.item(row, 0).setData(Qt.ItemDataRole.UserRole, rule)
            row += 1

        self._is_updating_ui = False
        if self.table.rowCount() > 0:
            self.table.selectRow(0)
        else:
            if self._is_read_restricted:
                self.preview_banner.set_text(tr("preview_text_root_req_view", path=self.current_file_path))
            else:
                self.preview_banner.set_text(tr("preview_text_no_rules"))

    def _on_table_selection_changed(self) -> None:
        if self._is_updating_ui:
            return
        selected = self.table.selectedItems()
        if not selected:
            return
        row = selected[0].row()
        rule: SudoersRule = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)

        self._is_updating_ui = True
        if rule.is_group:
            self.rb_group.setChecked(True)
        else:
            self.rb_user.setChecked(True)

        self.txt_entity.setText(rule.entity)
        self.txt_hosts.setText(rule.hosts)
        self.txt_runas_user.setText(rule.runas_user)
        self.txt_runas_group.setText(rule.runas_group)
        self.chk_nopasswd.setChecked(rule.nopasswd)
        self.txt_commands.setText(rule.commands)
        self._is_updating_ui = False

        self.preview_banner.set_text(rule.to_line())

    def _on_rule_modified(self) -> None:
        if self._is_updating_ui:
            return
        selected = self.table.selectedItems()
        if not selected:
            return
        row = selected[0].row()
        rule: SudoersRule = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)

        rule.is_group = self.rb_group.isChecked()
        rule.entity = self.txt_entity.text().strip().lstrip("%")
        rule.hosts = self.txt_hosts.text().strip() or "ALL"
        rule.runas_user = self.txt_runas_user.text().strip() or "ALL"
        rule.runas_group = self.txt_runas_group.text().strip()
        rule.nopasswd = self.chk_nopasswd.isChecked()
        rule.commands = self.txt_commands.text().strip() or "ALL"

        self._is_updating_ui = True
        ent_display = f"%{rule.entity}" if rule.is_group else rule.entity
        self.table.item(row, 0).setText(ent_display)
        self.table.item(row, 1).setText(rule.hosts)
        runas_str = f"({rule.runas_user}:{rule.runas_group})" if rule.runas_group else f"({rule.runas_user})"
        self.table.item(row, 2).setText(runas_str)
        pass_str = tr("val_nopasswd") if rule.nopasswd else tr("val_password_prompt")
        self.table.item(row, 3).setText(pass_str)
        self.table.item(row, 4).setText(rule.commands)
        self._is_updating_ui = False

        self.preview_banner.set_text(rule.to_line())
        self._sync_raw_from_rules()

    def _sync_raw_from_rules(self) -> None:
        if self._is_updating_ui:
            return
        self._is_updating_ui = True
        new_text = "\n".join(r.to_line() for r in self.rules)
        self.raw_editor.setPlainText(new_text)
        self._is_updating_ui = False

    def _on_raw_editor_text_changed(self) -> None:
        if self._is_updating_ui:
            return
        raw_text = self.raw_editor.toPlainText()
        self.preview_banner.set_text(tr("preview_text_raw_edit", path=self.current_file_path, lines=len(raw_text.splitlines())))

    def _on_tab_changed(self, idx: int) -> None:
        if not hasattr(self, "raw_editor"):
            return
        if idx == 0:
            # Switched back to builder: re-parse from raw editor
            raw_text = self.raw_editor.toPlainText()
            self.rules = [SudoersParser.parse_line(l) for l in raw_text.splitlines()]
            self._populate_table()
        else:
            # Switched to raw editor: sync latest rules
            self._sync_raw_from_rules()

    def _apply_command_preset(self) -> None:
        cmd_val = self.cmb_presets.currentData()
        if cmd_val:
            self.txt_commands.setText(cmd_val)

    def _add_new_rule(self) -> None:
        new_rule = SudoersRule(
            is_group=True,
            entity="wheel",
            hosts="ALL",
            runas_user="ALL",
            runas_group="ALL",
            nopasswd=False,
            commands="ALL",
        )
        self.rules.append(new_rule)
        self._populate_table()
        self.table.selectRow(self.table.rowCount() - 1)
        self._sync_raw_from_rules()

    def _remove_selected_rule(self) -> None:
        selected = self.table.selectedItems()
        if not selected:
            return
        row = selected[0].row()
        rule = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        confirm = QMessageBox.question(
            self,
            tr("title_confirm_removal"),
            tr("msg_confirm_removal", rule=rule.to_line()),
        )
        if confirm == QMessageBox.StandardButton.Yes:
            self.rules.remove(rule)
            self._populate_table()
            self._sync_raw_from_rules()

    def _create_new_dropin_file(self) -> None:
        filename, ok = QInputDialog.getText(
            self,
            tr("dialog_new_dropin_title"),
            tr("dialog_new_dropin_label"),
            text="99-custom-admin",
        )
        if not ok or not filename.strip():
            return
        filename = filename.strip()
        is_valid, err_msg = SudoersParser.is_valid_dropin_filename(filename)
        if not is_valid:
            QMessageBox.warning(self, tr("title_invalid_filename"), err_msg)
            return

        full_path = os.path.join(self.target_dir, filename)
        self._cached_contents[full_path] = ""
        if self.cmb_files.findText(full_path) == -1:
            self.cmb_files.addItem(full_path)
        self.cmb_files.setCurrentText(full_path)

    def _delete_dropin_file(self) -> None:
        path = self.current_file_path
        if not path or path == "/etc/sudoers":
            QMessageBox.warning(self, tr("title_action_prohibited"), tr("msg_cannot_delete_main"))
            return

        confirm = QMessageBox.question(
            self,
            tr("title_confirm_delete_dropin"),
            tr("msg_confirm_delete_dropin", path=path),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        res = SafeExecutor.run_command(["rm", "-f", path], elevated=True)
        if res.success:
            QMessageBox.information(self, tr("title_file_deleted"), tr("msg_dropin_deleted", path=path))
            self._cached_contents.pop(path, None)
            idx = self.cmb_files.findText(path)
            if idx != -1:
                self.cmb_files.removeItem(idx)
            self.cmb_files.setCurrentText("/etc/sudoers")
        else:
            QMessageBox.critical(self, tr("title_deletion_failed"), tr("msg_delete_failed", path=path, error=res.stderr or res.stdout))

    def _get_current_content_to_save(self) -> str:
        if self.tabs.currentIndex() == 1:
            return self.raw_editor.toPlainText().strip() + "\n"
        return "\n".join(r.to_line() for r in self.rules).strip() + "\n"

    def _validate_current_syntax(self) -> None:
        new_content = self._get_current_content_to_save()
        is_valid, msg = SudoersParser.validate_with_visudo(new_content)
        if is_valid:
            QMessageBox.information(
                self,
                tr("title_visudo_passed"),
                tr("msg_visudo_passed"),
            )
        else:
            QMessageBox.critical(
                self,
                tr("title_visudo_error"),
                tr("msg_visudo_error", msg=msg),
            )

    def _inspect_diff(self) -> None:
        new_content = self._get_current_content_to_save()
        diff = generate_diff(self.original_raw, new_content, os.path.basename(self.current_file_path))
        dlg = SafetyExecutionDialog(
            title=tr("dialog_diff_title"),
            target_path_or_command=self.current_file_path,
            diff_text=diff if diff.strip() else tr("diff_no_diff"),
            safety_notes=[
                tr("note_verify_visudo"),
                tr("note_lock_0440"),
            ],
            parent=self,
        )
        dlg.exec()

    def _save_sudoers_file(self) -> None:
        new_content = self._get_current_content_to_save()

        # 1. First safety check: visudo validation on tempfile
        is_valid, msg = SudoersParser.validate_with_visudo(new_content)
        if not is_valid:
            QMessageBox.critical(
                self,
                tr("title_refuse_save"),
                tr("msg_refuse_save", msg=msg),
            )
            return

        diff = generate_diff(self.original_raw, new_content, os.path.basename(self.current_file_path))
        notes = [
            tr("note_save_visudo"),
            tr("note_save_permissions"),
            tr("note_save_backup"),
        ]
        if self.current_file_path == "/etc/sudoers":
            notes.append(tr("note_primary_modified"))
        else:
            notes.append(tr("note_dropin_file", path=self.current_file_path))

        if self.current_ownership.is_managed:
            notes.insert(0, tr("note_pkg_managed", pkg=self.current_ownership.package_name))

        dlg = SafetyExecutionDialog(
            title=tr("dialog_apply_title"),
            target_path_or_command=self.current_file_path,
            diff_text=diff if diff.strip() else tr("diff_no_diff"),
            safety_notes=notes,
            parent=self,
        )
        if dlg.exec() == SafetyExecutionDialog.DialogCode.Accepted:
            import tempfile
            with tempfile.NamedTemporaryFile("w", delete=False) as tf:
                tf.write(new_content)
                temp_path = tf.name

            try:
                target = self.current_file_path
                script = (
                    f"mkdir -p $(dirname '{target}') && "
                    f"if [ -f '{target}' ]; then cp '{target}' '{target}.bak.$(date +%Y%m%d_%H%M%S)'; fi && "
                    f"cp '{temp_path}' '{target}' && "
                    f"chmod 0440 '{target}'"
                )
                res = SafeExecutor.run_command(["bash", "-c", script], elevated=True)
                if res.success:
                    QMessageBox.information(
                        self,
                        tr("title_success"),
                        tr("msg_saved_success", path=target),
                    )
                    self.original_raw = new_content
                    self._cached_contents[target] = new_content
                    self._on_file_selected()
                else:
                    QMessageBox.critical(self, tr("title_save_failed"), tr("msg_save_failed", error=res.stderr or res.stdout))
            finally:
                if os.path.exists(temp_path):
                    os.remove(temp_path)

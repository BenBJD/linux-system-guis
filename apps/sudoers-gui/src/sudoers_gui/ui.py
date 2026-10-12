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
        self.setWindowTitle("Sudoers Privilege Manager (visudo safe)")
        self.resize(1180, 820)
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
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # 1. Top Live Preview Banner
        self.preview_banner = LivePreviewBanner(
            title="Sudoers Config Syntax",
            subtitle="Modifying permissions below live updates this rule string. Note: Root permissions are required to inspect system rules.",
        )
        self.preview_banner.diffRequested.connect(self._inspect_diff)
        layout.addWidget(self.preview_banner)

        # 2. File Selection Bar
        file_bar = QHBoxLayout()
        file_bar.addWidget(QLabel("Sudoers File:"))
        self.cmb_files = QComboBox()
        self.cmb_files.setMinimumWidth(280)
        self.cmb_files.currentIndexChanged.connect(self._on_file_selected)
        file_bar.addWidget(self.cmb_files)

        self.package_badge = PackageOwnershipBadge()
        file_bar.addWidget(self.package_badge)

        self.btn_unlock_read = QPushButton("🔓 Read as Root")
        self.btn_unlock_read.setToolTip(format_tooltip(
            "Batch Read as Root",
            "pkexec python3",
            "Prompts for root privileges once to load /etc/sudoers, scan all /etc/sudoers.d/ drop-in files, and read their contents.",
            "Safe / Required for inspecting existing rules",
        ))
        self.btn_unlock_read.setVisible(False)
        self.btn_unlock_read.clicked.connect(self._read_all_with_root)
        file_bar.addWidget(self.btn_unlock_read)

        btn_refresh_all = QPushButton("🔄 Refresh (Root)")
        btn_refresh_all.setToolTip("Re-scan /etc/sudoers and all /etc/sudoers.d/ files to refresh contents.")
        btn_refresh_all.clicked.connect(self._read_all_with_root)
        file_bar.addWidget(btn_refresh_all)

        btn_new_file = QPushButton("📄 New Drop-in File")
        btn_new_file.setToolTip("Create a new rule file in /etc/sudoers.d/. Note: sudoers ignores files containing periods (.) or ending in ~.")
        btn_new_file.clicked.connect(self._create_new_dropin_file)
        file_bar.addWidget(btn_new_file)

        self.btn_delete_file = QPushButton("🗑️ Delete Drop-in")
        self.btn_delete_file.setToolTip("Permanently remove the currently selected drop-in file from /etc/sudoers.d/.")
        self.btn_delete_file.clicked.connect(self._delete_dropin_file)
        self.btn_delete_file.setEnabled(False)
        file_bar.addWidget(self.btn_delete_file)

        file_bar.addStretch()

        btn_validate_syntax = QPushButton("🧪 Validate with visudo")
        btn_validate_syntax.setToolTip(format_tooltip(
            "Syntax Validation",
            "visudo -c -f <file>",
            "Performs strict syntax and parsing validation using the system visudo compiler before applying any changes.",
            "Strongly Recommended",
        ))
        btn_validate_syntax.clicked.connect(self._validate_current_syntax)
        file_bar.addWidget(btn_validate_syntax)

        layout.addLayout(file_bar)

        # 3. Main Tab Widget: Visual Rule Builder vs Raw File Editor
        self.tabs = QTabWidget()

        # Tab 1: Visual Rule Builder
        builder_widget = QWidget()
        builder_layout = QVBoxLayout(builder_widget)
        builder_layout.setContentsMargins(0, 8, 0, 0)
        builder_layout.setSpacing(8)

        splitter = QSplitter(Qt.Orientation.Vertical)

        # Rules Table
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels([
            "Entity (User / Group)",
            "Target Hosts",
            "Run As Spec",
            "Password Required?",
            "Permitted Commands",
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
        form_layout.setContentsMargins(4, 6, 4, 6)
        form_layout.setSpacing(10)

        # Privilege Subject Box
        subject_group = QGroupBox("Privilege Subject (Who receives elevated access)")
        subject_grid = QGridLayout(subject_group)
        subject_grid.setSpacing(8)

        self.rb_user = QRadioButton("Individual User")
        self.rb_group = QRadioButton("Group (% prefix)")
        self.rb_group.setChecked(True)
        self.rb_user.toggled.connect(self._on_rule_modified)
        self.rb_group.toggled.connect(self._on_rule_modified)
        subject_grid.addWidget(self.rb_user, 0, 0)
        subject_grid.addWidget(self.rb_group, 0, 1)

        subject_grid.addWidget(QLabel("Account or Group Name:"), 0, 2)
        self.txt_entity = QLineEdit("wheel")
        self.txt_entity.setPlaceholderText("e.g. wheel, sudo, alice, deployer")
        self.txt_entity.setToolTip(format_tooltip(
            "Privilege Entity",
            "group or username",
            "The user account or system group granted sudo privileges.",
            "Required",
            "wheel (all administrators) or alice",
        ))
        self.txt_entity.textChanged.connect(self._on_rule_modified)
        subject_grid.addWidget(self.txt_entity, 0, 3)

        form_layout.addWidget(subject_group)

        # Execution Scope Box
        scope_group = QGroupBox("Execution Scope (Hosts && Run-As User)")
        scope_grid = QGridLayout(scope_group)
        scope_grid.setSpacing(8)

        scope_grid.addWidget(QLabel("Hosts:"), 0, 0)
        self.txt_hosts = QLineEdit("ALL")
        self.txt_hosts.setToolTip(format_tooltip(
            "Host Specification",
            "ALL",
            "List of network hostnames where this rule applies. Almost always 'ALL' on desktop Linux workstations.",
            "Standard: ALL",
        ))
        self.txt_hosts.textChanged.connect(self._on_rule_modified)
        scope_grid.addWidget(self.txt_hosts, 0, 1)

        scope_grid.addWidget(QLabel("Run As User:"), 0, 2)
        self.txt_runas_user = QLineEdit("ALL")
        self.txt_runas_user.setToolTip(format_tooltip(
            "Run-As Target User",
            "(ALL) or (root)",
            "The target user account that the command can be run as using sudo -u. Defaults to ALL.",
            "Standard: ALL",
        ))
        self.txt_runas_user.textChanged.connect(self._on_rule_modified)
        scope_grid.addWidget(self.txt_runas_user, 0, 3)

        scope_grid.addWidget(QLabel("Run As Group:"), 1, 2)
        self.txt_runas_group = QLineEdit("ALL")
        self.txt_runas_group.setToolTip(format_tooltip(
            "Run-As Target Group",
            "(:ALL)",
            "Optional target group specification for sudo -g. Can be left blank or ALL.",
        ))
        self.txt_runas_group.textChanged.connect(self._on_rule_modified)
        scope_grid.addWidget(self.txt_runas_group, 1, 3)

        form_layout.addWidget(scope_group)

        # Authentication & Commands Box
        auth_group = QGroupBox("Authentication Policy && Allowed Commands")
        auth_grid = QGridLayout(auth_group)
        auth_grid.setSpacing(8)

        self.chk_nopasswd = QCheckBox("NOPASSWD (Allow executing without asking for user's password)")
        self.chk_nopasswd.setToolTip(format_tooltip(
            "Passwordless Execution Tag",
            "NOPASSWD: ...",
            "Bypasses the sudo password prompt when this rule is invoked.<br><br><b>Security Warning:</b> Use with extreme caution. If this account is compromised, the attacker can execute root commands without needing the user password.",
            "Critical Security Impact",
            "NOPASSWD: /usr/bin/systemctl restart nginx",
        ))
        self.chk_nopasswd.toggled.connect(self._on_rule_modified)
        auth_grid.addWidget(self.chk_nopasswd, 0, 0, 1, 2)

        auth_grid.addWidget(QLabel("Permitted Commands:"), 1, 0)
        self.txt_commands = QLineEdit("ALL")
        self.txt_commands.setPlaceholderText("e.g. ALL or /usr/bin/systemctl restart nginx, /usr/bin/pacman -Syu")
        self.txt_commands.setToolTip(format_tooltip(
            "Permitted Commands",
            "ALL or /path/to/binary",
            "Absolute paths to permitted commands, separated by commas. Use 'ALL' for unrestricted root commands.",
            "Restricted paths recommended for specific tasks",
        ))
        self.txt_commands.textChanged.connect(self._on_rule_modified)
        auth_grid.addWidget(self.txt_commands, 1, 1, 1, 3)

        # Command presets bar
        preset_bar = QHBoxLayout()
        preset_bar.addWidget(QLabel("Insert Preset:"))
        self.cmb_presets = QComboBox()
        for cmd_val, desc in self.COMMON_COMMAND_PRESETS:
            self.cmb_presets.addItem(f"{cmd_val} ({desc})", cmd_val)
        btn_apply_preset = QPushButton("Insert Command")
        btn_apply_preset.clicked.connect(self._apply_command_preset)
        preset_bar.addWidget(self.cmb_presets)
        preset_bar.addWidget(btn_apply_preset)
        preset_bar.addStretch()
        auth_grid.addLayout(preset_bar, 2, 0, 1, 4)

        form_layout.addWidget(auth_group)

        scroll.setWidget(form_widget)
        splitter.addWidget(scroll)
        builder_layout.addWidget(splitter)
        self.tabs.addTab(builder_widget, "Visual Rule Builder")

        # Tab 2: Raw Sudoers Text Editor
        raw_widget = QWidget()
        raw_layout = QVBoxLayout(raw_widget)
        raw_layout.setContentsMargins(8, 8, 8, 8)
        raw_layout.setSpacing(6)

        lbl_raw_help = QLabel(
            "<b>Full File View / Editor:</b> Displays all rules, comments, and Defaults directives. "
            "You can edit the text directly here. All changes are validated with <code>visudo -c -f</code> prior to saving."
        )
        lbl_raw_help.setStyleSheet("color: #a6adc8; font-size: 12px;")
        raw_layout.addWidget(lbl_raw_help)

        self.raw_editor = QPlainTextEdit()
        font = QFont("Monospace")
        font.setStyleHint(QFont.StyleHint.Monospace)
        font.setPointSize(11)
        self.raw_editor.setFont(font)
        self.raw_editor.setStyleSheet(
            "QPlainTextEdit { background-color: #11111b; color: #cdd6f4; "
            "border: 1px solid #313244; border-radius: 6px; padding: 8px; }"
        )
        self.raw_editor.textChanged.connect(self._on_raw_editor_text_changed)
        raw_layout.addWidget(self.raw_editor)

        self.tabs.addTab(raw_widget, "📝 Raw File Editor / Comments")
        self.tabs.currentChanged.connect(self._on_tab_changed)
        layout.addWidget(self.tabs)

        # 4. Bottom Action Bar
        action_bar = QHBoxLayout()
        btn_add_rule = QPushButton("➕ Add New Rule")
        btn_add_rule.clicked.connect(self._add_new_rule)
        action_bar.addWidget(btn_add_rule)

        btn_del_rule = QPushButton("🗑️ Remove Selected Rule")
        btn_del_rule.clicked.connect(self._remove_selected_rule)
        action_bar.addWidget(btn_del_rule)

        action_bar.addStretch()

        btn_save = QPushButton("💾 Validate && Save File")
        btn_save.setObjectName("primaryBtn")
        btn_save.setToolTip("Validates syntax using visudo compiler, creates an automatic backup, and atomically writes with chmod 0440.")
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
                QMessageBox.critical(self, "Parse Error", f"Failed to parse sudoers data:\n{e}")
        else:
            QMessageBox.warning(self, "Read Failed", f"Could not read sudoers with root:\n{res.stderr or res.stdout}")

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
            self.preview_banner.set_subtitle(
                "Modifying the user, groups, and command permissions below dynamically updates this rule string."
            )
        else:
            try:
                with open(path, "r", encoding="utf-8") as f:
                    self.original_raw = f.read()
                    self._cached_contents[path] = self.original_raw
                    self.rules = [SudoersParser.parse_line(line) for line in self.original_raw.splitlines()]
                    self._is_read_restricted = False
                    self.btn_unlock_read.setVisible(False)
                    self.preview_banner.set_subtitle(
                        "Modifying the user, groups, and command permissions below dynamically updates this rule string."
                    )
            except PermissionError:
                self._is_read_restricted = True
                self.btn_unlock_read.setVisible(True)
                self.original_raw = (
                    f"# {path} is protected (read access restricted to root).\n"
                    "# Click 'Read as Root' above to scan /etc/sudoers and all /etc/sudoers.d/ files in one single prompt."
                )
                self.rules = [SudoersRule(raw_line=self.original_raw, is_comment=True)]
                self.preview_banner.set_text(
                    f"[ROOT REQUIRED] {path} is protected. Click 'Read as Root' to scan and load contents."
                )
                self.preview_banner.set_subtitle(
                    "⚠Root access is required to read system sudoers files. Click 'Read as Root' to scan /etc/sudoers and all .d files at once."
                )
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
                self.preview_banner.set_subtitle(
                    "New drop-in file (not yet created on disk). Configure permissions and click 'Validate && Save File' to apply."
                )

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
            pass_str = "NOPASSWD" if rule.nopasswd else "Password Prompt"
            self.table.setItem(row, 3, QTableWidgetItem(pass_str))
            self.table.setItem(row, 4, QTableWidgetItem(rule.commands))
            self.table.item(row, 0).setData(Qt.ItemDataRole.UserRole, rule)
            row += 1

        self._is_updating_ui = False
        if self.table.rowCount() > 0:
            self.table.selectRow(0)
        else:
            if self._is_read_restricted:
                self.preview_banner.set_text(
                    f"[ROOT REQUIRED] {self.current_file_path} is protected. Click 'Read as Root' to view rules and scan .d files."
                )
            else:
                self.preview_banner.set_text("# No active privilege rules configured in this file.")

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
        pass_str = "NOPASSWD" if rule.nopasswd else "Password Prompt"
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
        self.preview_banner.set_text(f"Editing raw file: {self.current_file_path} ({len(raw_text.splitlines())} lines)")

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
            "Confirm Removal",
            f"Are you sure you want to remove the sudoers privilege rule for:\n\n{rule.to_line()}?",
        )
        if confirm == QMessageBox.StandardButton.Yes:
            self.rules.remove(rule)
            self._populate_table()
            self._sync_raw_from_rules()

    def _create_new_dropin_file(self) -> None:
        filename, ok = QInputDialog.getText(
            self,
            "Create New Sudoers Drop-in File",
            "Enter filename for /etc/sudoers.d/:\n(e.g., 99-custom-admin, 10-developers)\n\nNote: Names must NOT contain '.' or end with '~'.",
            text="99-custom-admin",
        )
        if not ok or not filename.strip():
            return
        filename = filename.strip()
        is_valid, err_msg = SudoersParser.is_valid_dropin_filename(filename)
        if not is_valid:
            QMessageBox.warning(self, "Invalid Filename", err_msg)
            return

        full_path = os.path.join(self.target_dir, filename)
        self._cached_contents[full_path] = ""
        if self.cmb_files.findText(full_path) == -1:
            self.cmb_files.addItem(full_path)
        self.cmb_files.setCurrentText(full_path)

    def _delete_dropin_file(self) -> None:
        path = self.current_file_path
        if not path or path == "/etc/sudoers":
            QMessageBox.warning(self, "Action Prohibited", "The main /etc/sudoers file cannot be deleted.")
            return

        confirm = QMessageBox.question(
            self,
            "Confirm Drop-in File Deletion",
            f"Are you sure you want to permanently delete the sudoers drop-in file:\n\n{path}\n\nThis will remove all sudo privileges defined inside it.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        res = SafeExecutor.run_command(["rm", "-f", path], elevated=True)
        if res.success:
            QMessageBox.information(self, "File Deleted", f"Deleted drop-in file:\n{path}")
            self._cached_contents.pop(path, None)
            idx = self.cmb_files.findText(path)
            if idx != -1:
                self.cmb_files.removeItem(idx)
            self.cmb_files.setCurrentText("/etc/sudoers")
        else:
            QMessageBox.critical(self, "Deletion Failed", f"Could not delete {path}:\n{res.stderr or res.stdout}")

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
                "visudo Syntax Check Passed",
                f"visudo syntax validation succeeded!\n\nNo errors or syntax warnings were found in this configuration.",
            )
        else:
            QMessageBox.critical(
                self,
                "visudo Syntax Error Detected",
                f"visudo reported a syntax error:\n\n{msg}\n\nRule will NOT be saved until corrected to prevent root lockout.",
            )

    def _inspect_diff(self) -> None:
        new_content = self._get_current_content_to_save()
        diff = generate_diff(self.original_raw, new_content, os.path.basename(self.current_file_path))
        dlg = SafetyExecutionDialog(
            title="Inspect Sudoers Changes",
            target_path_or_command=self.current_file_path,
            diff_text=diff if diff.strip() else "# No differences detected",
            safety_notes=[
                "Syntax will be verified with 'visudo -c -f' before applying.",
                "Permissions will be locked strictly to 0440.",
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
                "Refusing to Save - visudo Error",
                f"visudo detected an invalid configuration:\n\n{msg}\n\nAborting save to prevent system lockout.",
            )
            return

        diff = generate_diff(self.original_raw, new_content, os.path.basename(self.current_file_path))
        notes = [
            "Syntax verified with 'visudo -c -f' (validation passed).",
            "File permissions will be set strictly to 0440 (required by sudo).",
            "Timestamped backup will be created before overwriting.",
        ]
        if self.current_file_path == "/etc/sudoers":
            notes.append("⚠Primary /etc/sudoers file is being modified.")
        else:
            notes.append(f"Drop-in rule file: {self.current_file_path}")

        if self.current_ownership.is_managed:
            notes.insert(0, f"CAUTION: Managed by package '{self.current_ownership.package_name}'.")

        dlg = SafetyExecutionDialog(
            title="Apply Sudoers Configuration",
            target_path_or_command=self.current_file_path,
            diff_text=diff if diff.strip() else "# No differences detected",
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
                        "Success",
                        f"Sudoers configuration successfully saved and validated with chmod 0440!\nPath: {target}",
                    )
                    self.original_raw = new_content
                    self._cached_contents[target] = new_content
                    self._on_file_selected()
                else:
                    QMessageBox.critical(self, "Save Failed", f"Failed:\n{res.stderr or res.stdout}")
            finally:
                if os.path.exists(temp_path):
                    os.remove(temp_path)

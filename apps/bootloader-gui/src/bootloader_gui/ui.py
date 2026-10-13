"""User interface for Bootloader and Kernel Boot Parameters manager."""

import os
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from linux_gui_core.runner.executor import SafeExecutor
from linux_gui_core.runner.package_manager import PackageManagerInspector, PackageOwnership
from linux_gui_core.widgets.package_badge import PackageOwnershipBadge
from linux_gui_core.widgets.preview_banner import LivePreviewBanner
from linux_gui_core.widgets.safety_dialog import SafetyExecutionDialog, generate_diff
from linux_gui_core.widgets.tooltips import format_tooltip
from bootloader_gui.backend import COMMON_KERNEL_ARGS, BootloaderBackend, BootloaderConfig
from bootloader_gui.strings import tr


class BootloaderMainWindow(QMainWindow):
    """Main window for editing kernel boot arguments, timeouts, and regenerating bootloaders."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle(tr("window_title"))
        self.resize(1280, 720)
        self.setMinimumSize(920, 600)

        self.active_type, self.detected_details = BootloaderBackend.detect_active_bootloader()
        self.config: BootloaderConfig = BootloaderConfig()
        self.package_ownership = PackageOwnership(is_managed=False)
        self._is_updating_ui: bool = False

        self._init_ui()
        self._load_config()

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

        # 2. Bootloader Selector & Architecture Bar
        bar = QHBoxLayout()
        bar.setSpacing(8)
        bar.addWidget(QLabel(tr("lbl_bootloader_arch")))
        self.rb_grub = QRadioButton(tr("rb_grub"))
        self.rb_grub.setChecked(self.active_type == "grub")
        self.rb_grub.toggled.connect(self._on_bootloader_type_toggled)
        bar.addWidget(self.rb_grub)

        self.rb_systemd_boot = QRadioButton(tr("rb_systemd_boot"))
        self.rb_systemd_boot.setChecked(self.active_type == "systemd-boot")
        self.rb_systemd_boot.toggled.connect(self._on_bootloader_type_toggled)
        bar.addWidget(self.rb_systemd_boot)

        bar.addSpacing(6)

        # Detection badge indicating active firmware loader
        self.lbl_detected = QLabel(tr("lbl_detected", details=self.detected_details))
        self.lbl_detected.setStyleSheet(
            "background-color: #222428; color: #57ab5a; font-weight: 600; font-size: 11px; "
            "padding: 2px 6px; border-radius: 3px; border: 1px solid #2d3036;"
        )
        bar.addWidget(self.lbl_detected)

        bar.addSpacing(6)
        self.package_badge = PackageOwnershipBadge()
        bar.addWidget(self.package_badge)

        self.btn_unlock_read = QPushButton(tr("btn_unlock_read"))
        self.btn_unlock_read.setToolTip(tr("tooltip_unlock_read"))
        self.btn_unlock_read.setVisible(False)
        self.btn_unlock_read.clicked.connect(self._read_esp_as_root)
        bar.addWidget(self.btn_unlock_read)

        bar.addStretch()

        btn_regen_only = QPushButton(tr("btn_regen_only"))
        btn_regen_only.setToolTip(tr("tooltip_regen_only"))
        btn_regen_only.clicked.connect(self._regenerate_only)
        bar.addWidget(btn_regen_only)

        layout.addLayout(bar)

        # 3. Main Scrollable Form Container
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)

        container = QWidget()
        form_layout = QVBoxLayout(container)
        form_layout.setContentsMargins(4, 4, 4, 4)
        form_layout.setSpacing(8)

        # Configuration Status & Path Box
        self.info_box = QGroupBox(tr("group_active_paths"))
        info_layout = QHBoxLayout(self.info_box)
        self.lbl_status_paths = QLabel()
        self.lbl_status_paths.setStyleSheet("color: #9498a1; font-size: 11px;")
        info_layout.addWidget(self.lbl_status_paths)
        form_layout.addWidget(self.info_box)

        # Menu & Timeout Box
        menu_box = QGroupBox(tr("group_boot_menu"))
        menu_grid = QGridLayout(menu_box)
        menu_grid.setSpacing(6)

        menu_grid.addWidget(QLabel(tr("lbl_timeout")), 0, 0)
        self.spn_timeout = QSpinBox()
        self.spn_timeout.setRange(0, 60)
        self.spn_timeout.setValue(5)
        self.spn_timeout.setToolTip(format_tooltip(
            tr("tooltip_timeout_title"),
            tr("tooltip_timeout_syntax"),
            tr("tooltip_timeout_desc"),
            tr("tooltip_timeout_impact"),
        ))
        self.spn_timeout.valueChanged.connect(self._on_values_changed)
        menu_grid.addWidget(self.spn_timeout, 0, 1)

        menu_grid.addWidget(QLabel(tr("lbl_default_entry")), 0, 2)
        self.txt_default = QLineEdit("0")
        self.txt_default.setToolTip(format_tooltip(
            tr("tooltip_default_title"),
            tr("tooltip_default_syntax"),
            tr("tooltip_default_desc"),
            tr("tooltip_default_impact"),
        ))
        self.txt_default.textChanged.connect(self._on_values_changed)
        menu_grid.addWidget(self.txt_default, 0, 3)

        form_layout.addWidget(menu_box)

        # Common Kernel Arguments Box
        args_box = QGroupBox(tr("group_common_args"))
        args_grid = QGridLayout(args_box)
        args_grid.setSpacing(8)

        self.arg_checkboxes: dict[str, QCheckBox] = {}
        for idx, (arg_key, desc, impact, example) in enumerate(COMMON_KERNEL_ARGS):
            chk = QCheckBox(arg_key)
            chk.setToolTip(format_tooltip(tr("tooltip_kernel_arg_prefix", arg=arg_key), arg_key, desc, impact, example))
            chk.toggled.connect(self._on_values_changed)
            self.arg_checkboxes[arg_key] = chk
            row = idx // 4
            col = idx % 4
            args_grid.addWidget(chk, row, col)

        form_layout.addWidget(args_box)

        # Custom Arguments Box
        custom_box = QGroupBox(tr("group_custom_args"))
        c_layout = QVBoxLayout(custom_box)
        c_layout.setSpacing(4)

        self.txt_custom_args = QLineEdit()
        self.txt_custom_args.setPlaceholderText(tr("placeholder_custom_args"))
        self.txt_custom_args.setToolTip(format_tooltip(
            tr("tooltip_extra_args_title"),
            tr("tooltip_extra_args_syntax"),
            tr("tooltip_extra_args_desc"),
        ))
        self.txt_custom_args.textChanged.connect(self._on_values_changed)
        c_layout.addWidget(self.txt_custom_args)

        form_layout.addWidget(custom_box)

        scroll.setWidget(container)
        layout.addWidget(scroll)

        # Bottom Action Bar
        action_bar = QHBoxLayout()
        action_bar.addStretch()

        btn_save = QPushButton(tr("btn_save"))
        btn_save.setObjectName("primaryBtn")
        btn_save.setToolTip(tr("tooltip_save"))
        btn_save.clicked.connect(self._save_and_regenerate)
        action_bar.addWidget(btn_save)

        layout.addLayout(action_bar)

    def _on_bootloader_type_toggled(self) -> None:
        self.active_type = "systemd-boot" if self.rb_systemd_boot.isChecked() else "grub"
        self._load_config()

    def _load_config(self) -> None:
        self._is_updating_ui = True
        if self.active_type == "grub":
            self.config = BootloaderBackend.load_grub_config("/etc/default/grub")
            self.btn_unlock_read.setVisible(False)
            self.lbl_status_paths.setText(
                tr(
                    "lbl_status_grub",
                    regen_cmd=BootloaderBackend.get_grub_regen_command(),
                )
            )
        else:
            self.config = BootloaderBackend.load_systemd_boot_config()
            self.btn_unlock_read.setVisible(self.config.is_protected)
            regen_cmd = BootloaderBackend.get_systemd_boot_regen_command()
            self.lbl_status_paths.setText(
                tr(
                    "lbl_status_systemd_boot",
                    esp=self.config.esp_path,
                    loader_conf=self.config.loader_conf_path,
                    cmdline=self.config.cmdline_file_path,
                    regen_cmd=regen_cmd,
                )
            )

        # Package badge
        self.package_ownership = PackageManagerInspector.check_file_owner(self.config.config_file_path)
        self.package_badge.update_status(self.package_ownership, self.config.config_file_path)

        self.spn_timeout.setValue(self.config.timeout)
        self.txt_default.setText(self.config.default_entry)

        param_set = set(self.config.kernel_params)
        for arg_key, chk in self.arg_checkboxes.items():
            chk.setChecked(arg_key in param_set)

        extra_args = [p for p in self.config.kernel_params if p not in self.arg_checkboxes]
        self.txt_custom_args.setText(" ".join(extra_args))

        self._is_updating_ui = False
        self._update_preview()

    def _read_esp_as_root(self) -> None:
        if not self.config.loader_conf_path:
            return
        res = SafeExecutor.run_command(["cat", self.config.loader_conf_path], elevated=True)
        if res.success:
            self.config.raw_content = res.stdout
            self.config.is_protected = False
            self.btn_unlock_read.setVisible(False)
            for line in res.stdout.splitlines():
                line = line.strip()
                parts = line.split(maxsplit=1)
                if len(parts) >= 2:
                    k, v = parts[0].lower(), parts[1].strip()
                    if k == "timeout":
                        try:
                            self.spn_timeout.setValue(int(v))
                        except ValueError:
                            pass
                    elif k == "default":
                        self.txt_default.setText(v)
            QMessageBox.information(self, tr("title_success"), tr("msg_esp_read_success", path=self.config.loader_conf_path))
            self._update_preview()
        else:
            QMessageBox.warning(self, tr("title_read_failed"), tr("msg_read_failed", path=self.config.loader_conf_path, error=res.stderr or res.stdout))

    def _on_values_changed(self) -> None:
        if self._is_updating_ui:
            return
        self.config.timeout = self.spn_timeout.value()
        self.config.default_entry = self.txt_default.text().strip()

        active_params = [k for k, chk in self.arg_checkboxes.items() if chk.isChecked()]
        custom_parts = self.txt_custom_args.text().strip().split()
        self.config.kernel_params = active_params + [c for c in custom_parts if c not in active_params]

        self._update_preview()

    def _update_preview(self) -> None:
        param_str = " ".join(self.config.kernel_params)
        if self.active_type == "grub":
            regen_cmd = BootloaderBackend.get_grub_regen_command()
            preview = f'GRUB_CMDLINE_LINUX_DEFAULT="{param_str}"  ➔  Regenerate: sudo {regen_cmd}'
            subtitle = tr("preview_sub_grub", cmd=regen_cmd)
        else:
            regen_cmd = BootloaderBackend.get_systemd_boot_regen_command()
            preview = f"options {param_str}  ➔  Regenerate: sudo {regen_cmd}"
            subtitle = tr("preview_sub_systemd_boot", cmd=regen_cmd)
        self.preview_banner.set_text(preview)
        self.preview_banner.set_subtitle(subtitle)

    def _inspect_diff(self) -> None:
        if self.active_type == "grub":
            new_content = BootloaderBackend.serialize_grub_config(self.config)
            diff = generate_diff(self.config.raw_content, new_content, "default/grub")
            regen_cmd = BootloaderBackend.get_grub_regen_command()
        else:
            loader_conf_text, cmdline_text = BootloaderBackend.serialize_systemd_boot_config(self.config)
            diff = (
                f"# --- /etc/kernel/cmdline ---\n+ {cmdline_text}\n\n"
                f"# --- {self.config.loader_conf_path} ---\n{loader_conf_text}"
            )
            regen_cmd = BootloaderBackend.get_systemd_boot_regen_command()

        dlg = SafetyExecutionDialog(
            title=tr("dialog_diff_title"),
            target_path_or_command=self.config.config_file_path,
            diff_text=diff if diff.strip() else tr("diff_no_diff"),
            safety_notes=[
                tr("note_backup_prior"),
                tr("note_regen_cmd", cmd=regen_cmd),
            ],
            parent=self,
        )
        dlg.exec()

    def _regenerate_only(self) -> None:
        cmd = BootloaderBackend.get_grub_regen_command() if self.active_type == "grub" else BootloaderBackend.get_systemd_boot_regen_command()
        dlg = SafetyExecutionDialog(
            title=tr("dialog_regen_title"),
            target_path_or_command=f"sudo {cmd}",
            diff_text=tr("diff_regen_only", cmd=cmd),
            safety_notes=[tr("note_regen_only")],
            parent=self,
        )
        if dlg.exec() == SafetyExecutionDialog.DialogCode.Accepted:
            res = BootloaderBackend.regenerate_bootloader(self.active_type)
            if res.success:
                QMessageBox.information(self, tr("title_success"), tr("msg_regen_success", output=res.stdout))
            else:
                QMessageBox.critical(self, tr("title_regen_error"), tr("msg_regen_failed", error=res.stderr or res.stdout))

    def _save_and_regenerate(self) -> None:
        if self.active_type == "grub":
            new_content = BootloaderBackend.serialize_grub_config(self.config)
            diff = generate_diff(self.config.raw_content, new_content, "default/grub")
            regen_cmd = BootloaderBackend.get_grub_regen_command()
            target_desc = f"write {self.config.config_file_path} && sudo {regen_cmd}"
            notes = [
                tr("note_grub_write", path=self.config.config_file_path),
                tr("note_grub_regen", cmd=regen_cmd),
                tr("note_backup_prior"),
            ]
        else:
            loader_conf_text, cmdline_text = BootloaderBackend.serialize_systemd_boot_config(self.config)
            diff = (
                f"# --- /etc/kernel/cmdline ---\n+ {cmdline_text}\n\n"
                f"# --- {self.config.loader_conf_path} ---\n{loader_conf_text}"
            )
            regen_cmd = BootloaderBackend.get_systemd_boot_regen_command()
            target_desc = f"write /etc/kernel/cmdline, {self.config.loader_conf_path} && sudo {regen_cmd}"
            notes = [
                tr("note_systemd_cmdline"),
                tr("note_systemd_loader", path=self.config.loader_conf_path),
                tr("note_systemd_regen", cmd=regen_cmd),
                tr("note_backup_prior"),
            ]

        if self.package_ownership.is_managed:
            notes.insert(0, tr("note_pkg_managed", pkg=self.package_ownership.package_name))

        dlg = SafetyExecutionDialog(
            title=tr("dialog_save_title"),
            target_path_or_command=target_desc,
            diff_text=diff if diff.strip() else tr("diff_no_diff"),
            safety_notes=notes,
            parent=self,
        )
        if dlg.exec() == SafetyExecutionDialog.DialogCode.Accepted:
            if self.active_type == "grub":
                write_res = SafeExecutor.safe_write_system_file(self.config.config_file_path, new_content)
                if not write_res.success:
                    QMessageBox.critical(self, tr("title_save_error"), tr("msg_save_failed", error=write_res.stderr))
                    return
            else:
                # Save /etc/kernel/cmdline
                cmdline_res = SafeExecutor.safe_write_system_file("/etc/kernel/cmdline", cmdline_text)
                if not cmdline_res.success:
                    QMessageBox.critical(self, tr("title_save_error"), tr("msg_cmdline_failed", error=cmdline_res.stderr))
                    return
                # Save loader.conf if available
                if self.config.loader_conf_path:
                    SafeExecutor.safe_write_system_file(self.config.loader_conf_path, loader_conf_text)

            regen_res = BootloaderBackend.regenerate_bootloader(self.active_type)
            if regen_res.success:
                QMessageBox.information(
                    self,
                    tr("title_bootloader_updated"),
                    tr("msg_bootloader_updated", output=regen_res.stdout),
                )
                self._load_config()
            else:
                QMessageBox.warning(
                    self,
                    tr("title_saved_warning"),
                    tr("msg_saved_warning", error=regen_res.stderr or regen_res.stdout),
                )

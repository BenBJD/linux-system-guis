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


class BootloaderMainWindow(QMainWindow):
    """Main window for editing kernel boot arguments, timeouts, and regenerating bootloaders."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Bootloader & Kernel Parameters (GRUB / systemd-boot)")
        self.resize(1200, 820)
        self.setMinimumSize(960, 680)

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
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # 1. Top Live Preview Banner
        self.preview_banner = LivePreviewBanner(
            title="Boot Parameter & Regeneration Command Preview",
            subtitle="Modifying kernel arguments below live updates the configuration line and update command.",
        )
        self.preview_banner.diffRequested.connect(self._inspect_diff)
        layout.addWidget(self.preview_banner)

        # 2. Bootloader Selector & Architecture Bar
        bar = QHBoxLayout()
        bar.addWidget(QLabel("Bootloader Architecture:"))
        self.rb_grub = QRadioButton("GRUB (/etc/default/grub)")
        self.rb_grub.setChecked(self.active_type == "grub")
        self.rb_grub.toggled.connect(self._on_bootloader_type_toggled)
        bar.addWidget(self.rb_grub)

        self.rb_systemd_boot = QRadioButton("systemd-boot (/efi & /etc/kernel/cmdline)")
        self.rb_systemd_boot.setChecked(self.active_type == "systemd-boot")
        self.rb_systemd_boot.toggled.connect(self._on_bootloader_type_toggled)
        bar.addWidget(self.rb_systemd_boot)

        bar.addSpacing(8)

        # Detection badge indicating active firmware loader
        self.lbl_detected = QLabel(f"Detected: {self.detected_details}")
        self.lbl_detected.setStyleSheet(
            "background-color: #313244; color: #a6e3a1; font-weight: bold; font-size: 11px; "
            "padding: 3px 8px; border-radius: 4px; border: 1px solid #45475a;"
        )
        bar.addWidget(self.lbl_detected)

        bar.addSpacing(6)
        self.package_badge = PackageOwnershipBadge()
        bar.addWidget(self.package_badge)

        self.btn_unlock_read = QPushButton("Read Protected ESP as Root")
        self.btn_unlock_read.setToolTip("Request root access to read /efi/loader/loader.conf directly.")
        self.btn_unlock_read.setVisible(False)
        self.btn_unlock_read.clicked.connect(self._read_esp_as_root)
        bar.addWidget(self.btn_unlock_read)

        bar.addStretch()

        btn_regen_only = QPushButton("Run Regeneration Only")
        btn_regen_only.setToolTip("Runs 'grub-mkconfig' or 'bootctl update' without modifying configuration files.")
        btn_regen_only.clicked.connect(self._regenerate_only)
        bar.addWidget(btn_regen_only)

        layout.addLayout(bar)

        # 3. Main Scrollable Form Container
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)

        container = QWidget()
        form_layout = QVBoxLayout(container)
        form_layout.setContentsMargins(4, 6, 4, 6)
        form_layout.setSpacing(12)

        # Configuration Status & Path Box
        self.info_box = QGroupBox("Active Bootloader Paths & Status")
        info_layout = QHBoxLayout(self.info_box)
        self.lbl_status_paths = QLabel()
        self.lbl_status_paths.setStyleSheet("color: #a6adc8; font-size: 12px;")
        info_layout.addWidget(self.lbl_status_paths)
        form_layout.addWidget(self.info_box)

        # Menu & Timeout Box
        menu_box = QGroupBox("Boot Menu & Timeout Settings")
        menu_grid = QGridLayout(menu_box)
        menu_grid.setSpacing(8)

        menu_grid.addWidget(QLabel("Boot Menu Timeout (Seconds):"), 0, 0)
        self.spn_timeout = QSpinBox()
        self.spn_timeout.setRange(0, 60)
        self.spn_timeout.setValue(5)
        self.spn_timeout.setToolTip(format_tooltip(
            "Boot Menu Delay",
            "timeout 5 or GRUB_TIMEOUT=5",
            "How long the boot menu countdown displays before automatically booting the default entry. Set to 0 to hide the menu.",
            "Safe",
        ))
        self.spn_timeout.valueChanged.connect(self._on_values_changed)
        menu_grid.addWidget(self.spn_timeout, 0, 1)

        menu_grid.addWidget(QLabel("Default Entry:"), 0, 2)
        self.txt_default = QLineEdit("0")
        self.txt_default.setToolTip(format_tooltip(
            "Default Boot Entry",
            "default <id> or @saved",
            "Identifier or index of the default OS to boot.<br><br><b>systemd-boot:</b> Typically filename or machine ID entry, or '@saved'.<br><b>GRUB:</b> Typically '0' or 'saved'.",
            "Safe",
        ))
        self.txt_default.textChanged.connect(self._on_values_changed)
        menu_grid.addWidget(self.txt_default, 0, 3)

        form_layout.addWidget(menu_box)

        # Common Kernel Arguments Box
        args_box = QGroupBox("Common Kernel Boot Arguments")
        args_grid = QGridLayout(args_box)
        args_grid.setSpacing(10)

        self.arg_checkboxes: dict[str, QCheckBox] = {}
        for idx, (arg_key, desc, impact, example) in enumerate(COMMON_KERNEL_ARGS):
            chk = QCheckBox(arg_key)
            chk.setToolTip(format_tooltip(f"Kernel Argument: {arg_key}", arg_key, desc, impact, example))
            chk.toggled.connect(self._on_values_changed)
            self.arg_checkboxes[arg_key] = chk
            row = idx // 4
            col = idx % 4
            args_grid.addWidget(chk, row, col)

        form_layout.addWidget(args_box)

        # Custom Arguments Box
        custom_box = QGroupBox("Custom Extra Kernel Parameters")
        c_layout = QVBoxLayout(custom_box)
        c_layout.setSpacing(6)

        self.txt_custom_args = QLineEdit()
        self.txt_custom_args.setPlaceholderText("e.g. amdgpu.ppfeaturemask=0xffffffff nvidia-drm.modeset=1 apparmor=1 security=apparmor")
        self.txt_custom_args.setToolTip(format_tooltip(
            "Extra Arguments",
            "Custom flags",
            "Space-separated custom kernel arguments appended to the boot command line.",
        ))
        self.txt_custom_args.textChanged.connect(self._on_values_changed)
        c_layout.addWidget(self.txt_custom_args)

        form_layout.addWidget(custom_box)

        scroll.setWidget(container)
        layout.addWidget(scroll)

        # Bottom Action Bar
        action_bar = QHBoxLayout()
        action_bar.addStretch()

        btn_save = QPushButton("💾 Save && Regenerate Bootloader")
        btn_save.setObjectName("primaryBtn")
        btn_save.setToolTip("Creates backup of configuration files, saves new parameters, and executes the bootloader regeneration command.")
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
                "<b>Config File:</b> <code>/etc/default/grub</code> &nbsp;|&nbsp; "
                "<b>Generated Output:</b> <code>/boot/grub/grub.cfg</code> &nbsp;|&nbsp; "
                f"<b>Regeneration:</b> <code>sudo {BootloaderBackend.get_grub_regen_command()}</code>"
            )
        else:
            self.config = BootloaderBackend.load_systemd_boot_config()
            self.btn_unlock_read.setVisible(self.config.is_protected)
            regen_cmd = BootloaderBackend.get_systemd_boot_regen_command()
            self.lbl_status_paths.setText(
                f"<b>ESP Mount:</b> <code>{self.config.esp_path}</code> &nbsp;|&nbsp; "
                f"<b>Loader Conf:</b> <code>{self.config.loader_conf_path}</code> &nbsp;|&nbsp; "
                f"<b>Cmdline File:</b> <code>{self.config.cmdline_file_path}</code> &nbsp;|&nbsp; "
                f"<b>Regeneration:</b> <code>sudo {regen_cmd}</code>"
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
            QMessageBox.information(self, "Success", f"Successfully read {self.config.loader_conf_path}.")
            self._update_preview()
        else:
            QMessageBox.warning(self, "Read Failed", f"Could not read {self.config.loader_conf_path}:\n{res.stderr or res.stdout}")

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
            subtitle = f"Modifying kernel arguments updates /etc/default/grub. Regenerate via: sudo {regen_cmd}"
        else:
            regen_cmd = BootloaderBackend.get_systemd_boot_regen_command()
            preview = f"options {param_str}  ➔  Regenerate: sudo {regen_cmd}"
            subtitle = f"Updates /etc/kernel/cmdline and loader.conf. Regenerate via: sudo {regen_cmd}"
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
            title="Inspect Bootloader Configuration Diff",
            target_path_or_command=self.config.config_file_path,
            diff_text=diff if diff.strip() else "# No differences detected",
            safety_notes=[
                "Automatic timestamped backups will be created prior to writing.",
                f"Regeneration command: sudo {regen_cmd}",
            ],
            parent=self,
        )
        dlg.exec()

    def _regenerate_only(self) -> None:
        cmd = BootloaderBackend.get_grub_regen_command() if self.active_type == "grub" else BootloaderBackend.get_systemd_boot_regen_command()
        dlg = SafetyExecutionDialog(
            title="Regenerate Bootloader",
            target_path_or_command=f"sudo {cmd}",
            diff_text=f"# No configuration file changes.\n# Will execute: sudo {cmd}",
            safety_notes=["Runs standard bootloader update to re-index kernels."],
            parent=self,
        )
        if dlg.exec() == SafetyExecutionDialog.DialogCode.Accepted:
            res = BootloaderBackend.regenerate_bootloader(self.active_type)
            if res.success:
                QMessageBox.information(self, "Success", f"Bootloader regenerated successfully!\n\n{res.stdout}")
            else:
                QMessageBox.critical(self, "Regeneration Error", f"Failed:\n{res.stderr or res.stdout}")

    def _save_and_regenerate(self) -> None:
        if self.active_type == "grub":
            new_content = BootloaderBackend.serialize_grub_config(self.config)
            diff = generate_diff(self.config.raw_content, new_content, "default/grub")
            regen_cmd = BootloaderBackend.get_grub_regen_command()
            target_desc = f"write {self.config.config_file_path} && sudo {regen_cmd}"
            notes = [
                f"Writes new parameters to {self.config.config_file_path}",
                f"Executes 'sudo {regen_cmd}' to apply changes to /boot/grub/grub.cfg.",
                "Timestamped backup will be created.",
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
                f"Updates persistent kernel parameters in /etc/kernel/cmdline.",
                f"Updates timeout and default in {self.config.loader_conf_path}.",
                f"Executes 'sudo {regen_cmd}' to refresh EFI boot entries.",
                "Timestamped backup will be created.",
            ]

        if self.package_ownership.is_managed:
            notes.insert(0, f"Managed by package: {self.package_ownership.package_name}")

        dlg = SafetyExecutionDialog(
            title="Save Configuration & Regenerate Bootloader",
            target_path_or_command=target_desc,
            diff_text=diff if diff.strip() else "# No differences detected",
            safety_notes=notes,
            parent=self,
        )
        if dlg.exec() == SafetyExecutionDialog.DialogCode.Accepted:
            if self.active_type == "grub":
                write_res = SafeExecutor.safe_write_system_file(self.config.config_file_path, new_content)
                if not write_res.success:
                    QMessageBox.critical(self, "Save Error", f"Failed writing configuration:\n{write_res.stderr}")
                    return
            else:
                # Save /etc/kernel/cmdline
                cmdline_res = SafeExecutor.safe_write_system_file("/etc/kernel/cmdline", cmdline_text)
                if not cmdline_res.success:
                    QMessageBox.critical(self, "Save Error", f"Failed writing /etc/kernel/cmdline:\n{cmdline_res.stderr}")
                    return
                # Save loader.conf if available
                if self.config.loader_conf_path:
                    SafeExecutor.safe_write_system_file(self.config.loader_conf_path, loader_conf_text)

            regen_res = BootloaderBackend.regenerate_bootloader(self.active_type)
            if regen_res.success:
                QMessageBox.information(
                    self,
                    "Bootloader Updated",
                    f"Configuration saved and bootloader regenerated successfully!\n\nOutput:\n{regen_res.stdout}",
                )
                self._load_config()
            else:
                QMessageBox.warning(
                    self,
                    "Saved with Regeneration Warning",
                    f"Configuration file was saved, but regeneration reported an error:\n{regen_res.stderr or regen_res.stdout}",
                )

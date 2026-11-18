"""User interface for udev rules manager."""

import os
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

from linux_gui_core.runner.executor import SafeExecutor
from linux_gui_core.runner.package_manager import PackageManagerInspector, PackageOwnership
from linux_gui_core.widgets.loading_modal import populate_option_catalog_list, run_with_loading_modal
from linux_gui_core.widgets.package_badge import PackageOwnershipBadge
from linux_gui_core.widgets.preview_banner import LivePreviewBanner
from linux_gui_core.widgets.safety_dialog import SafetyExecutionDialog, generate_diff
from linux_gui_core.widgets.tooltips import format_tooltip
from udev_gui.parser import UdevParser, UdevRule
from udev_gui.strings import tr


ADVANCED_UDEV_PRESETS = [
    # --- Commands, Haptics & External Scripts (RUN+=, IMPORT, SYSTEMD_WANTS) ---
    (
        'RUN+="/usr/local/bin/touchpad-tune.sh $devnode"',
        "Run Touchpad / Haptics Configuration Command (RUN+=)",
        "Runs an external command or script after rule matching (e.g. setting ThinkPad touchpad haptic resistance and click feedback, or tuning device registers). $devnode expands to the /dev/... path.",
        "udev(7) RUN+= — Short-running foreground command",
    ),
    (
        'RUN+="/bin/sh -c \'echo 1 > /sys$devpath/device/configure\'"',
        "Run Shell One-Liner to Write Sysfs / Device State (RUN+=)",
        "Executes /bin/sh -c with single-quoted arguments to write to sysfs paths or run a pipeline when a device is added or changed. $devpath expands to the kernel devpath.",
        "udev(7) RUN+= — Use single quotes inside double quotes",
    ),
    (
        'RUN{builtin}+="kmod load i2c_hid_acpi"',
        "Load Kernel Module via Builtin (RUN{builtin}+=)",
        "Instructs systemd-udevd to load the specified kernel module directly using its internal kmod builtin.",
        "udev(7) RUN{builtin}+=",
    ),
    (
        'TAG+="systemd", ENV{SYSTEMD_WANTS}+="my-device.service"',
        "Trigger Systemd Service on Device Plug-in (ENV{SYSTEMD_WANTS}+=)",
        "Starts a system service unit when the device is attached. Recommended by udev(7) instead of RUN+= for long-running daemons or network operations.",
        "udev(7) / systemd.device(5) — Recommended for daemons",
    ),
    (
        'TAG+="systemd", ENV{SYSTEMD_USER_WANTS}+="my-user-device.service"',
        "Trigger User Session Systemd Service (ENV{SYSTEMD_USER_WANTS}+=)",
        "Pulls in a systemd user manager service unit when the device is attached.",
        "systemd.device(5)",
    ),
    (
        'IMPORT{program}="/usr/local/bin/probe-device.sh $devnode"',
        "Import KEY=VALUE Environment from Helper Script (IMPORT{program}=)",
        "Executes an external program and imports its printed KEY=VALUE lines into the device event environment.",
        "udev(7) IMPORT{program}",
    ),
    # --- Input Devices, Touchpads, Keyboards & HID (libinput, uinput, HID) ---
    (
        'ATTRS{name}=="*Touchpad*"',
        "Match Touchpad by Device Name (ATTRS{name}==)",
        "Matches input/hidraw child devices whose parent input device name contains 'Touchpad' (e.g. ThinkPad Sensel/ELAN/Synaptics I2C touchpads).",
        "udev(7) ATTRS{name}",
    ),
    (
        'ENV{ID_INPUT_TOUCHPAD}=="1"',
        "Match Input Touchpad (ENV{ID_INPUT_TOUCHPAD}==\"1\")",
        "Matches any device classified by udev's input_id builtin as a laptop or external touchpad.",
        "udev(7) ENV Match",
    ),
    (
        'ENV{ID_INPUT_KEYBOARD}=="1"',
        "Match Input Keyboard (ENV{ID_INPUT_KEYBOARD}==\"1\")",
        "Matches any device classified by udev's input_id builtin as a keyboard.",
        "udev(7) ENV Match",
    ),
    (
        'ENV{ID_INPUT_MOUSE}=="1"',
        "Match Input Mouse / Pointing Device (ENV{ID_INPUT_MOUSE}==\"1\")",
        "Matches any device classified by udev's input_id builtin as a mouse or trackball.",
        "udev(7) ENV Match",
    ),
    (
        'ENV{ID_INPUT_TABLET}=="1"',
        "Match Drawing Tablet / Stylus (ENV{ID_INPUT_TABLET}==\"1\")",
        "Matches graphics tablets and stylus pads (Wacom, Huion, XP-Pen).",
        "udev(7) ENV Match",
    ),
    (
        'ENV{LIBINPUT_IGNORE_DEVICE}="1"',
        "Ignore Device in libinput / Wayland / X11 (ENV{LIBINPUT_IGNORE_DEVICE})",
        "Instructs the desktop compositor (Wayland / Xorg libinput driver) to ignore this input device completely.",
        "libinput(4) Environment Assignment",
    ),
    (
        'ATTRS{serial}=="*vial:f64c2b3c*"',
        "Match Vial / QMK Programmable Keyboard by Serial (ATTRS{serial}==)",
        "Matches any Vial-enabled custom mechanical keyboard regardless of vendor/product ID so hidraw permissions can be granted.",
        "udev(7) ATTRS{serial}",
    ),
    (
        'OPTIONS+="static_node=uinput"',
        "Create Static /dev/uinput Node (OPTIONS+=\"static_node=uinput\")",
        "Ensures /dev/uinput exists with configured permissions even before the uinput kernel module is loaded (used by Steam Input, Input Remapper, keyd, ydotoold).",
        "udev(7) OPTIONS static_node",
    ),
    (
        'TAG+="udev-acl"',
        "Legacy Desktop ACL Tag (TAG+=\"udev-acl\")",
        "Legacy companion tag often paired with TAG+=\"uaccess\" in third-party rules for older ConsoleKit/logind compatibility.",
        "udev(7) TAG",
    ),
    # --- Power Management & Sleep / Wakeup (sysfs power/*) ---
    (
        'ATTR{power/wakeup}="disabled"',
        "Disable System Wakeup from Sleep (ATTR{power/wakeup}=\"disabled\")",
        "Prevents this device from waking the system from suspend/sleep. Commonly used to stop accidental mouse movement, USB receiver, or dock wakeups.",
        "udev(7) ATTR{power/wakeup}",
    ),
    (
        'ATTR{power/wakeup}="enabled"',
        "Enable System Wakeup from Sleep (ATTR{power/wakeup}=\"enabled\")",
        "Explicitly allows this device to wake the computer from sleep when a key or button is pressed.",
        "udev(7) ATTR{power/wakeup}",
    ),
    (
        'ATTR{power/control}="on"',
        "Disable Runtime USB Autosuspend (ATTR{power/control}=\"on\")",
        "Prevents the kernel from putting the device into runtime power-saving sleep; keeps the device continuously powered (fixes audio DAC pops, mouse lag, or serial drops).",
        "udev(7) ATTR{power/control}",
    ),
    (
        'ATTR{power/control}="auto"',
        "Enable Runtime USB Autosuspend (ATTR{power/control}=\"auto\")",
        "Enables kernel runtime power-saving autosuspend when the device is idle.",
        "udev(7) ATTR{power/control}",
    ),
    (
        'ATTR{power/autosuspend_delay_ms}="5000"',
        "Set USB Autosuspend Idle Delay (ATTR{power/autosuspend_delay_ms})",
        "Sets the idle delay in milliseconds (e.g. 5000 = 5 seconds) before runtime autosuspend activates.",
        "udev(7) ATTR",
    ),
    # --- Serial, Microcontrollers & Embedded Probes ---
    (
        'ENV{ID_MM_DEVICE_IGNORE}="1"',
        "Prevent ModemManager from Probing Serial Device (ENV{ID_MM_DEVICE_IGNORE})",
        "Stops ModemManager from opening and sending AT commands to Arduino, ESP32, RP2040, 3D printer, or Zigbee/Z-Wave USB serial adapters on plug-in.",
        "ModemManager(8) / Embedded Development",
    ),
    # --- Storage, Block & Network Devices ---
    (
        'ATTR{queue/scheduler}="none"',
        "Set Block I/O Scheduler (ATTR{queue/scheduler})",
        "Sets the kernel block I/O scheduler (e.g. none, mq-deadline, bfq, kyber) for matching NVMe/SATA/USB block devices.",
        "udev(7) ATTR{queue/scheduler}",
    ),
    (
        'ENV{UDISKS_IGNORE}="1"',
        "Hide Partition/Disk from Desktop Auto-Mounter (ENV{UDISKS_IGNORE})",
        "Instructs udisks2 and desktop file managers not to show or auto-mount the matching block device or partition.",
        "udisks(8) Environment Assignment",
    ),
    (
        'ENV{UDISKS_AUTO}="1", ENV{UDISKS_SYSTEM}="0"',
        "Treat Internal SATA / eSATA Disk as Removable Drive (Arch Wiki)",
        "Marks an internal SATA or eSATA disk (matched by ENV{ID_SERIAL_SHORT} or DEVPATH) as external/removable so desktop file managers mount it without root password prompts.",
        "Arch Wiki Udev / udisks(8)",
    ),
    (
        'ENV{ID_FS_USAGE}=="filesystem", RUN{program}+="/usr/bin/systemd-mount --no-block --automount=yes --collect $devnode /media"',
        "Automount Block Filesystem via systemd-mount (Arch Wiki)",
        "Recommended way to automount drives from udev rules without violating systemd-udevd's isolated mount namespace or process timeouts (never call /bin/mount directly in RUN+=).",
        "Arch Wiki Udev §5.1 / systemd-mount(1)",
    ),
    (
        'ATTRS{type}=="Mains", ATTRS{online}=="0", RUN+="/usr/bin/systemd-run --machine=1000@.host --user notify-send \'Power State\' \'Using battery power\'"',
        "Send Desktop Notification on AC / Battery Power Change (Arch Wiki)",
        "Uses systemd-run to trigger a user-session desktop notification when SUBSYSTEM==\"power_supply\" emits ACTION==\"change\".",
        "Arch Wiki Udev §5.13 / systemd-run(1)",
    ),
    (
        'ENV{HOTPLUG}=="1", RUN+="/usr/local/bin/monitor-hotplug.sh"',
        "Run Script on External Monitor Hotplug (SUBSYSTEM==\"drm\")",
        "Matches display connector hotplug change events on SUBSYSTEM==\"drm\" (HDMI / DisplayPort / USB-C Alt-Mode).",
        "Arch Wiki Udev §3.1 / §5.4",
    ),
    (
        'RUN+="/bin/chgrp video /sys$devpath/brightness", RUN+="/bin/chmod g+w /sys$devpath/brightness"',
        "Allow 'video' Group to Control Screen Backlight (SUBSYSTEM==\"backlight\")",
        "Grants members of the 'video' group write access to /sys/class/backlight/*/brightness when a backlight device is added.",
        "Arch Wiki Backlight / udev(7)",
    ),
    (
        'ATTR{power/persist}="0"',
        "Disable USB-Persist Across System Suspend (ATTR{power/persist}=\"0\")",
        "Forces the kernel to re-enumerate and re-run udev 'add' rules for the USB device upon waking from suspend instead of persisting the old node.",
        "Arch Wiki Udev §5.11",
    ),
    (
        'NAME="eth_lan0"',
        "Rename Network Interface (NAME=\"...\")",
        "Renames a network interface (when matched by SUBSYSTEM==\"net\" and ATTR{address}==\"aa:bb:cc:dd:ee:ff\"). Device nodes cannot be renamed; only network interfaces support NAME=.",
        "udev(7) NAME",
    ),
    # --- Rule Evaluation & Control Options (udev(7) OPTIONS) ---
    (
        'OPTIONS+="link_priority=100"',
        "Increase Symlink Priority (OPTIONS+=\"link_priority=...\")",
        "Specifies priority when multiple devices claim the same SYMLINK+= name; higher numbers win.",
        "udev(7) OPTIONS link_priority",
    ),
    (
        'OPTIONS+="watch"',
        "Watch Device Node with inotify (OPTIONS+=\"watch\")",
        "Watches the device node with inotify and triggers a 'change' uevent whenever a program opens the device for writing and closes it.",
        "udev(7) OPTIONS watch",
    ),
    (
        'OPTIONS+="db_persist"',
        "Persist udev Database Across initrd Cleanup (OPTIONS+=\"db_persist\")",
        "Sets the sticky bit on the udev database entry so device properties are kept even when udevadm info --cleanup-db is run.",
        "udev(7) OPTIONS db_persist",
    ),
    (
        'OPTIONS="log_level=debug"',
        "Enable Debug Logging for This Rule (OPTIONS=\"log_level=debug\")",
        "Temporarily elevates systemd-udevd logging verbosity to debug while processing events matching this rule.",
        "udev(7) OPTIONS log_level",
    ),
]


class AdvancedAttributeDialog(QDialog):
    """Searchable dialog to select or enter advanced udev attributes."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("dlg_adv_title"))
        self.resize(740, 560)
        self.setMinimumSize(620, 440)
        self.selected_token: str = ""

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        # Search bar
        search_layout = QHBoxLayout()
        search_layout.setSpacing(8)
        search_layout.addWidget(QLabel(tr("lbl_search_attrs")))
        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText(tr("placeholder_search_attrs"))
        self.txt_search.textChanged.connect(self._filter_list)
        search_layout.addWidget(self.txt_search)
        layout.addLayout(search_layout)

        # Presets list
        self.list_widget = QListWidget()
        self.list_widget.setSpacing(2)
        self.list_widget.itemDoubleClicked.connect(self._on_preset_double_clicked)
        self._populate_list()
        layout.addWidget(self.list_widget, 1)

        # Custom entry box
        custom_box = QGroupBox(tr("group_custom_token"))
        c_layout = QHBoxLayout(custom_box)
        self.txt_custom = QLineEdit()
        self.txt_custom.setPlaceholderText(tr("placeholder_custom_token"))
        c_layout.addWidget(self.txt_custom)
        layout.addWidget(custom_box)

        # Button box
        btn_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btn_box.accepted.connect(self._accept_selection)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

    def _populate_list(self) -> None:
        populate_option_catalog_list(self.list_widget, ADVANCED_UDEV_PRESETS)

    def _filter_list(self, text: str) -> None:
        needle = text.lower()
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            searchable = item.data(Qt.ItemDataRole.UserRole + 1) or item.text().lower()
            item.setHidden(needle not in searchable)

    def _on_preset_double_clicked(self, item: QListWidgetItem) -> None:
        self.selected_token = item.data(Qt.ItemDataRole.UserRole)
        self.accept()

    def _accept_selection(self) -> None:
        custom = self.txt_custom.text().strip()
        if custom:
            self.selected_token = custom
            self.accept()
            return

        cur = self.list_widget.currentItem()
        if cur:
            self.selected_token = cur.data(Qt.ItemDataRole.UserRole)
            self.accept()
        else:
            QMessageBox.warning(self, tr("title_no_selection"), tr("msg_no_selection"))


class UdevMainWindow(QMainWindow):
    """Main window for editing and testing udev rules."""

    DEFAULT_RULES_DIR = "/etc/udev/rules.d"

    def __init__(self, rules_dir: str = DEFAULT_RULES_DIR):
        super().__init__()
        self.rules_dir = rules_dir
        self.setWindowTitle(tr("window_title"))
        self.resize(1280, 720)
        self.setMinimumSize(920, 620)

        self.current_file_path: str = ""
        self.rules: list[UdevRule] = []
        self.original_raw: str = ""
        self.current_ownership = PackageOwnership(is_managed=False)
        self._is_updating_ui: bool = False

        self._init_ui()
        self._load_rules_files()

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
            man_pages=["udev(7)", "udevadm(8)", "systemd-udevd.service(8)"],
        )
        self.preview_banner.diffRequested.connect(self._inspect_diff)
        layout.addWidget(self.preview_banner)

        # 2. File Selection Bar with Package Ownership Inspector
        file_bar = QHBoxLayout()
        file_bar.setSpacing(8)
        file_bar.addWidget(QLabel(tr("lbl_rule_file")))
        self.cmb_files = QComboBox()
        self.cmb_files.setMinimumWidth(300)
        self.cmb_files.currentIndexChanged.connect(self._on_file_selected)
        file_bar.addWidget(self.cmb_files)

        # Package Ownership Warning Badge
        self.package_badge = PackageOwnershipBadge()
        file_bar.addWidget(self.package_badge)

        btn_new_file = QPushButton(tr("btn_new_file"))
        btn_new_file.clicked.connect(self._create_new_rule_file)
        file_bar.addWidget(btn_new_file)

        file_bar.addStretch()

        btn_reload_daemon = QPushButton(tr("btn_reload_daemon"))
        btn_reload_daemon.setToolTip(format_tooltip(
            tr("tooltip_reload_daemon_title"),
            tr("tooltip_reload_daemon_cmd"),
            tr("tooltip_reload_daemon_desc"),
            tr("tooltip_reload_daemon_impact"),
            man_page="udevadm(8)",
        ))
        btn_reload_daemon.clicked.connect(self._trigger_udevadm_reload)
        file_bar.addWidget(btn_reload_daemon)

        layout.addLayout(file_bar)

        # 3. Main Splitter: Rules Table vs Interactive Builder
        splitter = QSplitter(Qt.Orientation.Vertical)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels([
            tr("col_action"),
            tr("col_subsystem"),
            tr("col_match"),
            tr("col_permissions"),
            tr("col_advanced"),
        ])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.itemSelectionChanged.connect(self._on_table_selection_changed)
        splitter.addWidget(self.table)

        # Form container with scroll area for responsive no-clipping layout
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)

        form_widget = QWidget()
        form_layout = QVBoxLayout(form_widget)
        form_layout.setContentsMargins(4, 4, 4, 4)
        form_layout.setSpacing(10)

        # 1. Match Conditions Group
        match_group = QGroupBox(tr("group_match_conditions"))
        match_grid = QGridLayout(match_group)
        match_grid.setSpacing(8)

        match_grid.addWidget(QLabel(tr("lbl_subsystem")), 0, 0)
        self.cmb_subsystem = QComboBox()
        self.cmb_subsystem.setEditable(True)
        self.cmb_subsystem.addItems([
            "", "usb", "hidraw", "input", "tty", "net", "block",
            "sound", "drm", "backlight", "power_supply", "video4linux",
            "hid", "i2c-dev", "pci", "nvme", "scsi", "rfkill", "thunderbolt", "misc",
        ])
        self.cmb_subsystem.setToolTip(format_tooltip(
            tr("tooltip_subsystem_title"),
            tr("tooltip_subsystem_syntax"),
            tr("tooltip_subsystem_desc"),
            man_page="udev(7)",
            can_be_blank=True,
            blank_behavior="Matches events across all kernel subsystems.",
        ))
        self.cmb_subsystem.currentTextChanged.connect(self._on_rule_modified)
        match_grid.addWidget(self.cmb_subsystem, 0, 1)

        match_grid.addWidget(QLabel(tr("lbl_action")), 0, 2)
        self.cmb_action = QComboBox()
        self.cmb_action.setEditable(True)
        self.cmb_action.addItems([
            "", "add", "add|change", "change", "remove", "bind", "unbind", "online", "offline", "move",
        ])
        self.cmb_action.setToolTip(format_tooltip(
            tr("tooltip_action_title"),
            tr("tooltip_action_syntax"),
            tr("tooltip_action_desc"),
            man_page="udev(7)",
            can_be_blank=True,
            blank_behavior="Matches all uevent actions (note: rules should normally match add or add|change).",
        ))
        self.cmb_action.currentTextChanged.connect(self._on_rule_modified)
        match_grid.addWidget(self.cmb_action, 0, 3)

        match_grid.addWidget(QLabel(tr("lbl_vendor")), 1, 0)
        self.txt_vendor = QLineEdit()
        self.txt_vendor.setPlaceholderText(tr("placeholder_vendor"))
        self.txt_vendor.setToolTip(format_tooltip(
            tr("tooltip_vendor_title"),
            tr("tooltip_vendor_syntax"),
            tr("tooltip_vendor_desc"),
            man_page="udev(7)",
            can_be_blank=True,
            blank_behavior="Does not filter by vendor ID.",
        ))
        self.txt_vendor.textChanged.connect(self._on_rule_modified)
        match_grid.addWidget(self.txt_vendor, 1, 1)

        match_grid.addWidget(QLabel(tr("lbl_product")), 1, 2)
        self.txt_product = QLineEdit()
        self.txt_product.setPlaceholderText(tr("placeholder_product"))
        self.txt_product.setToolTip(format_tooltip(
            tr("tooltip_product_title"),
            tr("tooltip_product_syntax"),
            tr("tooltip_product_desc"),
            man_page="udev(7)",
            can_be_blank=True,
            blank_behavior="Does not filter by product ID.",
        ))
        self.txt_product.textChanged.connect(self._on_rule_modified)
        match_grid.addWidget(self.txt_product, 1, 3)

        match_grid.addWidget(QLabel(tr("lbl_kernel")), 2, 0)
        self.txt_kernel = QLineEdit()
        self.txt_kernel.setPlaceholderText(tr("placeholder_kernel"))
        self.txt_kernel.setToolTip(format_tooltip(
            tr("tooltip_kernel_title"),
            tr("tooltip_kernel_syntax"),
            tr("tooltip_kernel_desc"),
            man_page="udev(7)",
            can_be_blank=True,
            blank_behavior="Matches any kernel device name.",
        ))
        self.txt_kernel.textChanged.connect(self._on_rule_modified)
        match_grid.addWidget(self.txt_kernel, 2, 1)

        match_grid.addWidget(QLabel(tr("lbl_driver")), 2, 2)
        self.txt_driver = QLineEdit()
        self.txt_driver.setPlaceholderText(tr("placeholder_driver"))
        self.txt_driver.setToolTip(format_tooltip(
            tr("tooltip_driver_title"),
            tr("tooltip_driver_syntax"),
            tr("tooltip_driver_desc"),
            man_page="udev(7)",
            can_be_blank=True,
            blank_behavior="Matches regardless of bound kernel driver.",
        ))
        self.txt_driver.textChanged.connect(self._on_rule_modified)
        match_grid.addWidget(self.txt_driver, 2, 3)

        match_grid.addWidget(QLabel(tr("lbl_attr_match")), 3, 0)
        attr_match_row = QHBoxLayout()
        attr_match_row.setSpacing(6)
        self.cmb_attr_match_key = QComboBox()
        self.cmb_attr_match_key.addItems([
            "ATTRS{name}",
            "ATTR{name}",
            "ATTRS{serial}",
            "ATTR{serial}",
            "ENV{ID_SERIAL_SHORT}",
            "ATTRS{manufacturer}",
            "ATTRS{product}",
            "ATTR{address}",
            "DEVPATH",
        ])
        self.cmb_attr_match_key.setToolTip(format_tooltip(
            tr("tooltip_attr_match_title"),
            tr("tooltip_attr_match_syntax"),
            tr("tooltip_attr_match_desc"),
            man_page="udev(7)",
        ))
        self.cmb_attr_match_key.currentTextChanged.connect(self._on_rule_modified)
        attr_match_row.addWidget(self.cmb_attr_match_key)

        self.txt_attr_match_val = QLineEdit()
        self.txt_attr_match_val.setPlaceholderText(tr("placeholder_attr_match"))
        self.txt_attr_match_val.setToolTip(format_tooltip(
            tr("tooltip_attr_match_title"),
            tr("tooltip_attr_match_syntax"),
            tr("tooltip_attr_match_desc"),
            man_page="udev(7)",
            can_be_blank=True,
            blank_behavior="No sysfs name or serial match expression added.",
        ))
        self.txt_attr_match_val.textChanged.connect(self._on_rule_modified)
        attr_match_row.addWidget(self.txt_attr_match_val, 1)
        match_grid.addLayout(attr_match_row, 3, 1)

        self.chk_parent_attrs = QCheckBox(tr("chk_parent_attrs"))
        self.chk_parent_attrs.setToolTip(format_tooltip(
            tr("tooltip_parent_attrs_title"),
            tr("tooltip_parent_attrs_syntax"),
            tr("tooltip_parent_attrs_desc"),
            man_page="udev(7)",
        ))
        self.chk_parent_attrs.toggled.connect(self._on_rule_modified)
        match_grid.addWidget(self.chk_parent_attrs, 3, 2, 1, 2)

        form_layout.addWidget(match_group)

        # 2. Assignment Actions Group (Permissions, Ownership & Symlinks)
        assign_group = QGroupBox(tr("group_permissions"))
        assign_grid = QGridLayout(assign_group)
        assign_grid.setSpacing(8)

        assign_grid.addWidget(QLabel(tr("lbl_mode")), 0, 0)
        self.cmb_mode = QComboBox()
        self.cmb_mode.setEditable(True)
        self.cmb_mode.addItems(["", "0660", "0666", "0640", "0600"])
        self.cmb_mode.setToolTip(format_tooltip(
            tr("tooltip_mode_title"),
            tr("tooltip_mode_syntax"),
            tr("tooltip_mode_desc"),
            tr("tooltip_mode_impact"),
            man_page="udev(7)",
            can_be_blank=True,
            blank_behavior="Keeps default kernel/system device node permissions.",
        ))
        self.cmb_mode.currentTextChanged.connect(self._on_rule_modified)
        assign_grid.addWidget(self.cmb_mode, 0, 1)

        assign_grid.addWidget(QLabel(tr("lbl_group")), 0, 2)
        self.cmb_group = QComboBox()
        self.cmb_group.setEditable(True)
        self.cmb_group.addItems(["", "plugdev", "dialout", "input", "uinput", "audio", "video", "render", "kvm"])
        self.cmb_group.setToolTip(format_tooltip(
            tr("tooltip_group_title"),
            tr("tooltip_group_syntax"),
            tr("tooltip_group_desc"),
            tr("tooltip_group_impact"),
            man_page="udev(7)",
            can_be_blank=True,
            blank_behavior="Keeps default group ownership (typically root).",
        ))
        self.cmb_group.currentTextChanged.connect(self._on_rule_modified)
        assign_grid.addWidget(self.cmb_group, 0, 3)

        self.chk_uaccess = QCheckBox(tr("chk_uaccess"))
        self.chk_uaccess.setToolTip(format_tooltip(
            tr("tooltip_uaccess_title"),
            tr("tooltip_uaccess_syntax"),
            tr("tooltip_uaccess_desc"),
            tr("tooltip_uaccess_impact"),
            man_page="udev(7)",
        ))
        self.chk_uaccess.toggled.connect(self._on_rule_modified)
        assign_grid.addWidget(self.chk_uaccess, 1, 0, 1, 2)

        assign_grid.addWidget(QLabel(tr("lbl_symlink")), 1, 2)
        self.txt_symlink = QLineEdit()
        self.txt_symlink.setPlaceholderText(tr("placeholder_symlink"))
        self.txt_symlink.setToolTip(format_tooltip(
            tr("tooltip_symlink_title"),
            tr("tooltip_symlink_syntax"),
            tr("tooltip_symlink_desc"),
            man_page="udev(7)",
            can_be_blank=True,
            blank_behavior="No additional /dev/ symlink created.",
        ))
        self.txt_symlink.textChanged.connect(self._on_rule_modified)
        assign_grid.addWidget(self.txt_symlink, 1, 3)

        assign_grid.addWidget(QLabel(tr("lbl_owner")), 2, 0)
        self.txt_owner = QLineEdit()
        self.txt_owner.setPlaceholderText(tr("placeholder_owner"))
        self.txt_owner.setToolTip(format_tooltip(
            tr("tooltip_owner_title"),
            tr("tooltip_owner_syntax"),
            tr("tooltip_owner_desc"),
            man_page="udev(7)",
            can_be_blank=True,
            blank_behavior="Default user owner (root) is preserved.",
        ))
        self.txt_owner.textChanged.connect(self._on_rule_modified)
        assign_grid.addWidget(self.txt_owner, 2, 1)

        form_layout.addWidget(assign_group)

        # 3. Run Commands, Systemd Services & Hardware Power Group
        cmd_power_group = QGroupBox(tr("group_commands_power"))
        cmd_power_grid = QGridLayout(cmd_power_group)
        cmd_power_grid.setSpacing(8)

        cmd_power_grid.addWidget(QLabel(tr("lbl_run_cmd")), 0, 0)
        run_row = QHBoxLayout()
        run_row.setSpacing(6)
        self.cmb_run_type = QComboBox()
        self.cmb_run_type.addItems(["RUN+=", "RUN{program}+=", "RUN{builtin}+=", "RUN="])
        self.cmb_run_type.setToolTip(format_tooltip(
            tr("tooltip_run_cmd_title"),
            tr("tooltip_run_cmd_syntax"),
            tr("tooltip_run_cmd_desc"),
            security=tr("tooltip_run_cmd_security"),
            man_page="udev(7)",
        ))
        self.cmb_run_type.currentTextChanged.connect(self._on_rule_modified)
        run_row.addWidget(self.cmb_run_type)

        self.txt_run_cmd = QLineEdit()
        self.txt_run_cmd.setPlaceholderText(tr("placeholder_run_cmd"))
        self.txt_run_cmd.setToolTip(format_tooltip(
            tr("tooltip_run_cmd_title"),
            tr("tooltip_run_cmd_syntax"),
            tr("tooltip_run_cmd_desc"),
            security=tr("tooltip_run_cmd_security"),
            man_page="udev(7)",
            can_be_blank=True,
            blank_behavior="No external command or builtin is executed for this rule.",
        ))
        self.txt_run_cmd.textChanged.connect(self._on_rule_modified)
        run_row.addWidget(self.txt_run_cmd, 1)

        self.cmb_insert_sub = QComboBox()
        self.cmb_insert_sub.addItem(tr("sub_placeholder"), "")
        self.cmb_insert_sub.addItem("$devnode (%N) — /dev/... device node", "$devnode")
        self.cmb_insert_sub.addItem("$kernel (%k) — kernel device name", "$kernel")
        self.cmb_insert_sub.addItem("/sys$devpath (%S%p) — full sysfs path", "/sys$devpath")
        self.cmb_insert_sub.addItem("$attr{idVendor} — sysfs attribute value", "$attr{idVendor}")
        self.cmb_insert_sub.addItem("/bin/sh -c '...' — shell wrapper", "/bin/sh -c ''")
        self.cmb_insert_sub.setToolTip(format_tooltip(
            tr("tooltip_insert_sub_title"),
            tr("tooltip_insert_sub_syntax"),
            tr("tooltip_insert_sub_desc"),
            man_page="udev(7)",
        ))
        self.cmb_insert_sub.currentIndexChanged.connect(self._on_insert_run_substitution)
        run_row.addWidget(self.cmb_insert_sub)

        cmd_power_grid.addLayout(run_row, 0, 1, 1, 3)

        cmd_power_grid.addWidget(QLabel(tr("lbl_systemd_wants")), 1, 0)
        self.txt_systemd_wants = QLineEdit()
        self.txt_systemd_wants.setPlaceholderText(tr("placeholder_systemd_wants"))
        self.txt_systemd_wants.setToolTip(format_tooltip(
            tr("tooltip_systemd_wants_title"),
            tr("tooltip_systemd_wants_syntax"),
            tr("tooltip_systemd_wants_desc"),
            man_page="udev(7)",
            can_be_blank=True,
            blank_behavior="Does not trigger a systemd unit.",
        ))
        self.txt_systemd_wants.textChanged.connect(self._on_rule_modified)
        cmd_power_grid.addWidget(self.txt_systemd_wants, 1, 1, 1, 3)

        cmd_power_grid.addWidget(QLabel(tr("lbl_wakeup")), 2, 0)
        self.cmb_wakeup = QComboBox()
        self.cmb_wakeup.addItem(tr("wakeup_unchanged"), "")
        self.cmb_wakeup.addItem(tr("wakeup_disabled"), "disabled")
        self.cmb_wakeup.addItem(tr("wakeup_enabled"), "enabled")
        self.cmb_wakeup.setToolTip(format_tooltip(
            tr("tooltip_wakeup_title"),
            tr("tooltip_wakeup_syntax"),
            tr("tooltip_wakeup_desc"),
            man_page="udev(7)",
        ))
        self.cmb_wakeup.currentIndexChanged.connect(self._on_rule_modified)
        cmd_power_grid.addWidget(self.cmb_wakeup, 2, 1)

        cmd_power_grid.addWidget(QLabel(tr("lbl_power_control")), 2, 2)
        self.cmb_power_control = QComboBox()
        self.cmb_power_control.addItem(tr("power_unchanged"), "")
        self.cmb_power_control.addItem(tr("power_on"), "on")
        self.cmb_power_control.addItem(tr("power_auto"), "auto")
        self.cmb_power_control.setToolTip(format_tooltip(
            tr("tooltip_power_control_title"),
            tr("tooltip_power_control_syntax"),
            tr("tooltip_power_control_desc"),
            man_page="udev(7)",
        ))
        self.cmb_power_control.currentIndexChanged.connect(self._on_rule_modified)
        cmd_power_grid.addWidget(self.cmb_power_control, 2, 3)

        form_layout.addWidget(cmd_power_group)

        # 4. Additional Match & Assignment Directives Group
        adv_group = QGroupBox(tr("group_advanced"))
        adv_layout = QVBoxLayout(adv_group)
        adv_layout.setSpacing(6)

        adv_bar = QHBoxLayout()
        self.lbl_extra_count = QLabel(tr("lbl_extra_count"))
        self.lbl_extra_count.setStyleSheet("color: #6899e6; font-weight: 600; font-size: 12px;")
        adv_bar.addWidget(self.lbl_extra_count)
        adv_bar.addStretch()

        btn_add_adv = QPushButton(tr("btn_add_adv"))
        btn_add_adv.setToolTip(tr("tooltip_add_adv"))
        btn_add_adv.clicked.connect(self._open_advanced_dialog)
        adv_bar.addWidget(btn_add_adv)
        adv_layout.addLayout(adv_bar)

        self.tbl_extras = QTableWidget(0, 2)
        self.tbl_extras.setHorizontalHeaderLabels([tr("col_extra_directive"), tr("col_extra_action")])
        self.tbl_extras.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.tbl_extras.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.tbl_extras.setColumnWidth(1, 90)
        self.tbl_extras.setFixedHeight(110)
        self.tbl_extras.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        adv_layout.addWidget(self.tbl_extras)

        form_layout.addWidget(adv_group)

        scroll.setWidget(form_widget)
        splitter.addWidget(scroll)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)
        layout.addWidget(splitter)

        # Bottom Action Bar
        action_bar = QHBoxLayout()
        action_bar.setSpacing(8)
        btn_add_rule = QPushButton(tr("btn_add_rule"))
        btn_add_rule.clicked.connect(self._add_new_rule)
        action_bar.addWidget(btn_add_rule)

        btn_del_rule = QPushButton(tr("btn_remove_rule"))
        btn_del_rule.clicked.connect(self._remove_selected_rule)
        action_bar.addWidget(btn_del_rule)

        action_bar.addStretch()

        btn_save = QPushButton(tr("btn_save_rules"))
        btn_save.setObjectName("primaryBtn")
        btn_save.clicked.connect(self._save_rules_file)
        action_bar.addWidget(btn_save)

        layout.addLayout(action_bar)

    def _on_insert_run_substitution(self, index: int) -> None:
        if index <= 0:
            return
        token = self.cmb_insert_sub.itemData(index)
        if token:
            current = self.txt_run_cmd.text()
            if not current:
                self.txt_run_cmd.setText(token)
            elif current.endswith(" "):
                self.txt_run_cmd.setText(current + token)
            else:
                self.txt_run_cmd.setText(f"{current} {token}")
            self.txt_run_cmd.setFocus()
        self.cmb_insert_sub.blockSignals(True)
        self.cmb_insert_sub.setCurrentIndex(0)
        self.cmb_insert_sub.blockSignals(False)

    _MATCH_KEY_CANDIDATES = (
        "ATTRS{name}",
        "ATTR{name}",
        "ATTRS{serial}",
        "ATTR{serial}",
        "ENV{ID_SERIAL_SHORT}",
        "ATTRS{manufacturer}",
        "ATTRS{product}",
        "ATTR{address}",
        "DEVPATH",
    )

    def _format_rule_summary_columns(self, rule: UdevRule) -> tuple[str, str, str]:
        match_parts = []
        if rule.vendor_id:
            match_parts.append(f"Vendor={rule.vendor_id}")
        if rule.product_id:
            match_parts.append(f"Product={rule.product_id}")
        if rule.kernel:
            match_parts.append(f"Kernel={rule.kernel}")
        if rule.driver:
            match_parts.append(f"Driver={rule.driver}")
        for attr_key in self._MATCH_KEY_CANDIDATES:
            val = rule.get_extra_value(attr_key)
            if val:
                match_parts.append(f"{attr_key}={val}")
        match_str = " ".join(match_parts) if match_parts else f"Vendor={rule.vendor_id or '*'} Product={rule.product_id or '*'} Kernel={rule.kernel or '*'}"

        perm_parts = [f"Mode={rule.mode or 'def'}", f"Group={rule.group or 'root'}"]
        if rule.owner:
            perm_parts.append(f"Owner={rule.owner}")
        perm_parts.append(f"uaccess={rule.tag_uaccess}")
        if rule.symlink:
            perm_parts.append(f"Symlink={rule.symlink}")
        perm_str = " ".join(perm_parts)

        adv_parts = []
        if rule.run_cmd:
            adv_parts.append(f'{rule.run_key}{rule.run_op}"{rule.run_cmd}"')
        if rule.systemd_wants:
            adv_parts.append(f'ENV{{SYSTEMD_WANTS}}+="{rule.systemd_wants}"')
        adv_parts.extend(rule.extra_tokens)
        extra_str = ", ".join(adv_parts) if adv_parts else tr("val_none")
        return match_str, perm_str, extra_str

    def _load_rules_files(self) -> None:
        self.cmb_files.clear()
        files = UdevParser.list_rules_files(self.rules_dir)
        if not files:
            default_demo = os.path.join(self.rules_dir, "70-custom-devices.rules")
            self.cmb_files.addItem(default_demo)
        else:
            for f in files:
                self.cmb_files.addItem(f)

    def _on_file_selected(self) -> None:
        path = self.cmb_files.currentText()
        if not path:
            return
        self.current_file_path = path

        # Check package manager ownership off the UI thread when visible
        self.current_ownership = run_with_loading_modal(
            self,
            title="Loading udev Rules...",
            subtitle=f"Inspecting package ownership for {os.path.basename(path)}...",
            task_fn=lambda: PackageManagerInspector.check_file_owner(path),
        )
        self.package_badge.update_status(self.current_ownership, path)

        self.rules = []
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                self.original_raw = f.read()
                for line in self.original_raw.splitlines():
                    self.rules.append(UdevParser.parse_rule_line(line))
        else:
            self.original_raw = ""

        self._populate_table()

    def _populate_table(self) -> None:
        self._is_updating_ui = True
        self.table.setRowCount(0)
        row = 0
        for rule in self.rules:
            if rule.is_comment or not rule.to_line().strip():
                continue
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(rule.action or tr("val_all")))
            self.table.setItem(row, 1, QTableWidgetItem(rule.subsystem or tr("val_all")))
            match_str, perm_str, extra_str = self._format_rule_summary_columns(rule)
            self.table.setItem(row, 2, QTableWidgetItem(match_str))
            self.table.setItem(row, 3, QTableWidgetItem(perm_str))
            self.table.setItem(row, 4, QTableWidgetItem(extra_str))
            self.table.item(row, 0).setData(Qt.ItemDataRole.UserRole, rule)
            row += 1

        self._is_updating_ui = False
        if self.table.rowCount() > 0:
            self.table.selectRow(0)

    def _sync_ui_from_rule(self, rule: UdevRule) -> None:
        self._is_updating_ui = True
        self.cmb_subsystem.setCurrentText(rule.subsystem)
        self.cmb_action.setCurrentText(rule.action)
        self.txt_vendor.setText(rule.vendor_id)
        self.txt_product.setText(rule.product_id)
        self.txt_kernel.setText(rule.kernel)
        self.txt_driver.setText(rule.driver)
        self.chk_parent_attrs.setChecked(
            rule.vendor_key == "ATTRS{idVendor}" or rule.product_key == "ATTRS{idProduct}"
        )

        # Populate Name / Serial / Property match if present in extra_tokens
        found_attr_key = "ATTRS{name}"
        found_attr_val = ""
        for candidate in self._MATCH_KEY_CANDIDATES:
            v = rule.get_extra_value(candidate)
            if v:
                found_attr_key = candidate
                found_attr_val = v
                break
        self.cmb_attr_match_key.setCurrentText(found_attr_key)
        self.txt_attr_match_val.setText(found_attr_val)

        # Permissions & Nodes
        self.cmb_mode.setCurrentText(rule.mode)
        self.cmb_group.setCurrentText(rule.group)
        self.txt_owner.setText(rule.owner)
        self.chk_uaccess.setChecked(rule.tag_uaccess)
        self.txt_symlink.setText(rule.symlink)

        # Commands, Systemd & Power
        run_prefix = f"{rule.run_key}{rule.run_op}"
        if self.cmb_run_type.findText(run_prefix) == -1:
            self.cmb_run_type.addItem(run_prefix)
        self.cmb_run_type.setCurrentText(run_prefix)
        self.txt_run_cmd.setText(rule.run_cmd)
        self.txt_systemd_wants.setText(rule.systemd_wants)

        wakeup_val = rule.get_extra_value("ATTR{power/wakeup}")
        idx_wake = self.cmb_wakeup.findData(wakeup_val)
        self.cmb_wakeup.setCurrentIndex(idx_wake if idx_wake >= 0 else 0)

        power_val = rule.get_extra_value("ATTR{power/control}")
        idx_power = self.cmb_power_control.findData(power_val)
        self.cmb_power_control.setCurrentIndex(idx_power if idx_power >= 0 else 0)

        self._populate_extras_table(rule)
        self._is_updating_ui = False

    def _on_table_selection_changed(self) -> None:
        if self._is_updating_ui:
            return
        selected = self.table.selectedItems()
        if not selected:
            return
        row = selected[0].row()
        rule: UdevRule = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)

        self._sync_ui_from_rule(rule)
        self.preview_banner.set_text(rule.to_line())

    def _populate_extras_table(self, rule: UdevRule) -> None:
        self.tbl_extras.setRowCount(0)
        for idx, token in enumerate(rule.extra_tokens):
            self.tbl_extras.insertRow(idx)
            self.tbl_extras.setItem(idx, 0, QTableWidgetItem(token))
            btn_del = QPushButton(tr("btn_remove_extra"))
            btn_del.setStyleSheet("font-size: 12px; padding: 2px 8px;")
            btn_del.clicked.connect(lambda _, t=token: self._remove_extra_token(t))
            self.tbl_extras.setCellWidget(idx, 1, btn_del)

    def _remove_extra_token(self, token: str) -> None:
        selected = self.table.selectedItems()
        if not selected:
            return
        row = selected[0].row()
        rule: UdevRule = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        if token in rule.extra_tokens:
            rule.extra_tokens.remove(token)
            self._sync_ui_from_rule(rule)
            self._on_rule_modified()

    def _open_advanced_dialog(self) -> None:
        selected = self.table.selectedItems()
        if not selected:
            QMessageBox.warning(self, tr("title_no_rule_selected"), tr("msg_select_rule_first"))
            return
        row = selected[0].row()
        rule: UdevRule = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)

        dlg = AdvancedAttributeDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted and dlg.selected_token:
            parsed = UdevParser.parse_rule_line(dlg.selected_token)
            if parsed.run_cmd and not rule.run_cmd:
                rule.run_cmd = parsed.run_cmd
                rule.run_key = parsed.run_key
                rule.run_op = parsed.run_op
            elif parsed.systemd_wants and not rule.systemd_wants:
                rule.systemd_wants = parsed.systemd_wants
            elif dlg.selected_token not in rule.extra_tokens:
                rule.extra_tokens.append(dlg.selected_token)
            self._sync_ui_from_rule(rule)
            self._on_rule_modified()

    def _on_rule_modified(self) -> None:
        if self._is_updating_ui:
            return
        selected = self.table.selectedItems()
        if not selected:
            return
        row = selected[0].row()
        rule: UdevRule = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)

        rule.subsystem = self.cmb_subsystem.currentText().strip()
        rule.action = self.cmb_action.currentText().strip()
        rule.vendor_id = self.txt_vendor.text().strip()
        rule.product_id = self.txt_product.text().strip()
        if self.chk_parent_attrs.isChecked():
            rule.vendor_key = "ATTRS{idVendor}"
            rule.product_key = "ATTRS{idProduct}"
        else:
            rule.vendor_key = "ATTR{idVendor}"
            rule.product_key = "ATTR{idProduct}"
        rule.kernel = self.txt_kernel.text().strip()
        rule.driver = self.txt_driver.text().strip()

        # Sync Name / Serial / Property match into extra_tokens
        selected_attr_key = self.cmb_attr_match_key.currentText().strip()
        selected_attr_val = self.txt_attr_match_val.text().strip()
        for candidate in self._MATCH_KEY_CANDIDATES:
            if candidate == selected_attr_key:
                rule.set_extra_value(candidate, "==", selected_attr_val)
            else:
                rule.set_extra_value(candidate, "==", "")

        # Permissions & Ownership
        rule.mode = self.cmb_mode.currentText().strip()
        rule.group = self.cmb_group.currentText().strip()
        rule.owner = self.txt_owner.text().strip()
        rule.tag_uaccess = self.chk_uaccess.isChecked()
        rule.symlink = self.txt_symlink.text().strip()

        # Commands, Systemd & Power
        run_type_text = self.cmb_run_type.currentText().strip()
        if run_type_text.endswith("+="):
            rule.run_key = run_type_text[:-2]
            rule.run_op = "+="
        elif run_type_text.endswith(":="):
            rule.run_key = run_type_text[:-2]
            rule.run_op = ":="
        elif run_type_text.endswith("="):
            rule.run_key = run_type_text[:-1]
            rule.run_op = "="
        rule.run_cmd = self.txt_run_cmd.text().strip()
        rule.systemd_wants = self.txt_systemd_wants.text().strip()

        wakeup_val = self.cmb_wakeup.currentData() or ""
        rule.set_extra_value("ATTR{power/wakeup}", "=", wakeup_val)

        power_val = self.cmb_power_control.currentData() or ""
        rule.set_extra_value("ATTR{power/control}", "=", power_val)

        # Update table row text and extras table
        self._is_updating_ui = True
        self._populate_extras_table(rule)
        self.table.item(row, 0).setText(rule.action or tr("val_all"))
        self.table.item(row, 1).setText(rule.subsystem or tr("val_all"))
        match_str, perm_str, extra_str = self._format_rule_summary_columns(rule)
        self.table.item(row, 2).setText(match_str)
        self.table.item(row, 3).setText(perm_str)
        self.table.item(row, 4).setText(extra_str)
        self._is_updating_ui = False

        # Live update top banner
        self.preview_banner.set_text(rule.to_line())

    def _add_new_rule(self) -> None:
        new_rule = UdevRule(
            subsystem="usb",
            action="add",
            vendor_id="1234",
            product_id="5678",
            mode="0666",
            group="plugdev",
            tag_uaccess=True,
        )
        self.rules.append(new_rule)
        self._populate_table()
        self.table.selectRow(self.table.rowCount() - 1)

    def _remove_selected_rule(self) -> None:
        selected = self.table.selectedItems()
        if not selected:
            return
        row = selected[0].row()
        rule = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        self.rules.remove(rule)
        self._populate_table()

    def _create_new_rule_file(self) -> None:
        name = "70-custom-devices.rules"
        full = os.path.join(self.rules_dir, name)
        if self.cmb_files.findText(full) == -1:
            self.cmb_files.addItem(full)
        self.cmb_files.setCurrentText(full)
        self.package_badge.set_unmanaged("custom")

    def _inspect_diff(self) -> None:
        new_content = "\n".join(r.to_line() for r in self.rules) + "\n"
        diff = generate_diff(self.original_raw, new_content, os.path.basename(self.current_file_path))
        
        notes = []
        if self.current_ownership.is_managed:
            notes.append(
                tr(
                    "note_managed_file",
                    pkg=self.current_ownership.package_name,
                    manager=self.current_ownership.package_manager,
                )
            )
        else:
            notes.append(tr("note_unmanaged_file"))

        dlg = SafetyExecutionDialog(
            title=tr("dialog_diff_title"),
            target_path_or_command=self.current_file_path,
            diff_text=diff if diff.strip() else tr("diff_no_changes"),
            safety_notes=notes,
            parent=self,
        )
        dlg.exec()

    def _trigger_udevadm_reload(self) -> None:
        cmd = "udevadm control --reload-rules && udevadm trigger"
        dlg = SafetyExecutionDialog(
            title=tr("dialog_reload_title"),
            target_path_or_command=cmd,
            safety_notes=[
                tr("note_reload_rules"),
                tr("note_trigger_events"),
            ],
            parent=self,
        )
        if dlg.exec() == SafetyExecutionDialog.DialogCode.Accepted:
            res = SafeExecutor.run_command(["bash", "-c", cmd], elevated=True)
            if res.success:
                QMessageBox.information(self, tr("title_reloaded"), tr("msg_reload_success"))
            else:
                QMessageBox.critical(self, tr("title_reload_failed"), tr("msg_reload_failed", error=res.stderr))

    def _save_rules_file(self) -> None:
        new_content = "\n".join(r.to_line() for r in self.rules) + "\n"
        diff = generate_diff(self.original_raw, new_content, os.path.basename(self.current_file_path))

        notes = [
            tr("note_save_elevated"),
            tr("note_save_backup"),
        ]
        if self.current_ownership.is_managed:
            notes.insert(0, tr(
                "note_save_pkg_warning",
                pkg=self.current_ownership.package_name,
                manager=self.current_ownership.package_manager,
            ))

        dlg = SafetyExecutionDialog(
            title=tr("dialog_save_title"),
            target_path_or_command=self.current_file_path,
            diff_text=diff if diff.strip() else tr("diff_no_diff"),
            safety_notes=notes,
            parent=self,
        )
        if dlg.exec() == SafetyExecutionDialog.DialogCode.Accepted:
            res = SafeExecutor.safe_write_system_file(self.current_file_path, new_content)
            if res.success:
                QMessageBox.information(self, tr("title_saved"), tr("msg_saved_success", backup=res.backup_file))
                self._on_file_selected()
            else:
                QMessageBox.critical(self, tr("title_error_saving"), tr("msg_saved_failed", error=res.stderr))

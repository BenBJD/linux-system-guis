"""User interface for Linux Device Manager."""

import os
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from linux_gui_core.runner.executor import SafeExecutor
from linux_gui_core.runner.package_manager import PackageManagerInspector
from linux_gui_core.widgets.package_badge import PackageOwnershipBadge
from linux_gui_core.widgets.preview_banner import LivePreviewBanner
from linux_gui_core.widgets.safety_dialog import SafetyExecutionDialog
from linux_gui_core.widgets.tooltips import format_tooltip
from device_gui.backend import (
    CATEGORY_METADATA,
    DeviceInfo,
    DeviceManagerBackend,
    SystemSummary,
)
from device_gui.strings import tr


class DeviceMainWindow(QMainWindow):
    """Main window for Linux Device Manager, hardware tree, and driver inspector."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle(tr("window_title"))
        self.resize(1280, 720)
        self.setMinimumSize(940, 600)

        self.backend = DeviceManagerBackend()
        self.devices: list[DeviceInfo] = []
        self.summary: SystemSummary = SystemSummary()
        self.selected_device: DeviceInfo | None = None

        self._init_ui()
        # Initial scan deferred by single shot timer to ensure UI renders instantly
        QTimer.singleShot(50, self.refresh_devices)

    def _init_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(12, 10, 12, 10)
        root_layout.setSpacing(6)

        # 1. Top Live Preview Banner
        self.preview_banner = LivePreviewBanner(
            title=tr("preview_title"),
            subtitle=tr("preview_subtitle"),
        )
        root_layout.addWidget(self.preview_banner)

        # 2. Controls Toolbar
        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)

        # Search Bar
        toolbar.addWidget(QLabel(tr("lbl_search")))
        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText(tr("placeholder_search"))
        self.txt_search.setClearButtonEnabled(True)
        self.txt_search.textChanged.connect(self._on_search_changed)
        toolbar.addWidget(self.txt_search, stretch=3)

        # View Mode Selector
        toolbar.addWidget(QLabel(tr("lbl_view")))
        self.cmb_view_mode = QComboBox()
        self.cmb_view_mode.addItem(tr("view_category"), "category")
        self.cmb_view_mode.addItem(tr("view_connection"), "connection")
        self.cmb_view_mode.currentIndexChanged.connect(self._rebuild_tree)
        toolbar.addWidget(self.cmb_view_mode, stretch=1)

        # Action Buttons
        btn_expand = QPushButton(tr("btn_expand_all"))
        btn_expand.clicked.connect(lambda: self.tree.expandAll())
        toolbar.addWidget(btn_expand)

        btn_collapse = QPushButton(tr("btn_collapse_all"))
        btn_collapse.clicked.connect(lambda: self.tree.collapseAll())
        toolbar.addWidget(btn_collapse)

        self.btn_refresh = QPushButton(tr("btn_refresh"))
        self.btn_refresh.setToolTip(format_tooltip(
            tr("tooltip_refresh_title"),
            tr("tooltip_refresh_cmd"),
            tr("tooltip_refresh_desc"),
            tr("tooltip_refresh_impact"),
        ))
        self.btn_refresh.clicked.connect(self.refresh_devices)
        toolbar.addWidget(self.btn_refresh)

        btn_report = QPushButton(tr("btn_export_report"))
        btn_report.setToolTip(format_tooltip(
            tr("tooltip_report_title"),
            tr("tooltip_report_cmd"),
            tr("tooltip_report_desc"),
            tr("tooltip_report_impact"),
        ))
        btn_report.clicked.connect(self._export_report)
        toolbar.addWidget(btn_report)

        root_layout.addLayout(toolbar)

        # 3. Main Splitter: Left Pane (Details/Inspector) vs Right Pane (Device Tree)
        self.splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left Pane: Selected Device Info (or System Summary)
        self.left_scroll = QScrollArea()
        self.left_scroll.setWidgetResizable(True)
        self.left_scroll.setFrameShape(QScrollArea.Shape.NoFrame)

        self.left_container = QWidget()
        self.left_layout = QVBoxLayout(self.left_container)
        self.left_layout.setContentsMargins(4, 4, 8, 4)
        self.left_layout.setSpacing(8)
        self.left_scroll.setWidget(self.left_container)
        self.splitter.addWidget(self.left_scroll)

        # Right Pane: Modernized Device Tree
        tree_widget_container = QWidget()
        tree_layout = QVBoxLayout(tree_widget_container)
        tree_layout.setContentsMargins(2, 2, 2, 2)
        tree_layout.setSpacing(4)

        self.tree_status_lbl = QLabel(tr("lbl_tree_loading"))
        self.tree_status_lbl.setStyleSheet("color: #9498a1; font-size: 11px;")
        tree_layout.addWidget(self.tree_status_lbl)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels([tr("col_device_component"), tr("col_driver"), tr("col_hw_id_path")])
        self.tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        self.tree.header().setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        self.tree.header().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.tree.setColumnWidth(0, 340)
        self.tree.setColumnWidth(1, 140)
        self.tree.itemSelectionChanged.connect(self._on_tree_selection_changed)
        tree_layout.addWidget(self.tree)

        self.splitter.addWidget(tree_widget_container)

        # Set 42% / 58% splitter ratio
        self.splitter.setSizes([720, 480])
        root_layout.addWidget(self.splitter, stretch=1)

        # Render initial placeholder on left pane
        self._show_system_summary()

    def refresh_devices(self) -> None:
        """Rescans system hardware and updates the UI."""
        self.btn_refresh.setEnabled(False)
        self.tree_status_lbl.setText(tr("lbl_tree_scanning"))
        QApplication.processEvents()

        try:
            self.devices = self.backend.scan_all_devices()
            self.summary = self.backend.get_system_summary(self.devices)
            self._rebuild_tree()
            self._show_system_summary()
            self.tree_status_lbl.setText(
                tr(
                    "lbl_tree_discovered",
                    devices=len(self.devices),
                    categories=len(self.summary.device_counts_by_category),
                )
            )
        finally:
            self.btn_refresh.setEnabled(True)

    def _rebuild_tree(self) -> None:
        """Constructs tree items either By Category or By Connection Hierarchy."""
        self.tree.clear()
        mode = self.cmb_view_mode.currentData()

        if mode == "connection":
            self._build_connection_tree()
        else:
            self._build_category_tree()

        # Re-apply search filter if active
        query = self.txt_search.text().strip()
        if query:
            self._filter_tree(query)

    def _build_category_tree(self) -> None:
        """Standard Windows Device Manager view grouped by device category."""
        grouped: dict[str, list[DeviceInfo]] = {}
        for dev in self.devices:
            grouped.setdefault(dev.category, []).append(dev)

        sorted_cats = sorted(
            grouped.keys(),
            key=lambda c: CATEGORY_METADATA.get(c, ("❓", 999))[1],
        )

        for cat in sorted_cats:
            devs_in_cat = grouped[cat]
            icon_str, _ = CATEGORY_METADATA.get(cat, ("🧩", 120))

            cat_item = QTreeWidgetItem()
            cat_item.setText(0, f"{icon_str}  {cat} ({len(devs_in_cat)})")
            cat_item.setFont(0, QFont("", -1, QFont.Weight.Bold))
            cat_item.setData(0, Qt.ItemDataRole.UserRole, None)

            for dev in devs_in_cat:
                child = QTreeWidgetItem()
                child.setText(0, f"    {dev.name}")

                driver_text = dev.driver_name or "—"
                if dev.driver_type == "dkms":
                    driver_text = f"{dev.driver_name} [DKMS]"
                elif dev.driver_type == "builtin":
                    driver_text = f"{dev.driver_name} [builtin]"
                child.setText(1, driver_text)

                hw_id = ""
                if dev.vendor_id and dev.product_id:
                    hw_id = f"{dev.vendor_id}:{dev.product_id}"
                elif dev.pci_slot:
                    hw_id = dev.pci_slot
                elif dev.device_node:
                    hw_id = dev.device_node
                child.setText(2, hw_id)

                child.setData(0, Qt.ItemDataRole.UserRole, dev)
                cat_item.addChild(child)

            self.tree.addTopLevelItem(cat_item)
            cat_item.setExpanded(True)

    def _build_connection_tree(self) -> None:
        """Physical topology hierarchy (Root -> Buses -> Controllers -> Peripherals)."""
        root_item = QTreeWidgetItem()
        root_item.setText(0, f"💻  {self.summary.hostname or 'System Hardware'}")
        root_item.setFont(0, QFont("", -1, QFont.Weight.Bold))
        root_item.setData(0, Qt.ItemDataRole.UserRole, None)

        node_map: dict[str, QTreeWidgetItem] = {"system:root": root_item}

        for dev in self.devices:
            item = QTreeWidgetItem()
            item.setText(0, f"{dev.category_icon}  {dev.name}")
            item.setText(1, dev.driver_name or "—")
            item.setText(2, dev.pci_slot or dev.usb_port or dev.device_node)
            item.setData(0, Qt.ItemDataRole.UserRole, dev)
            node_map[dev.id] = item

        for dev in self.devices:
            item = node_map[dev.id]
            parent = node_map.get(dev.parent_id, root_item)
            parent.addChild(item)

        self.tree.addTopLevelItem(root_item)
        root_item.setExpanded(True)

    def _on_search_changed(self, text: str) -> None:
        self._filter_tree(text.strip().lower())

    def _filter_tree(self, needle: str) -> None:
        """Filters tree nodes matching name, vendor, device id, driver, or path."""
        for i in range(self.tree.topLevelItemCount()):
            top = self.tree.topLevelItem(i)
            self._filter_item_recursive(top, needle)

    def _filter_item_recursive(self, item: QTreeWidgetItem, needle: str) -> bool:
        if not needle:
            item.setHidden(False)
            for j in range(item.childCount()):
                self._filter_item_recursive(item.child(j), needle)
            return True

        dev: DeviceInfo | None = item.data(0, Qt.ItemDataRole.UserRole)
        match = False

        if dev:
            text_corpus = (
                f"{dev.name} {dev.vendor_name} {dev.product_name} {dev.vendor_id} "
                f"{dev.product_id} {dev.driver_name} {dev.driver_type_label} "
                f"{dev.pci_slot} {dev.usb_port} {dev.device_node} {dev.modalias}"
            ).lower()
            match = needle in text_corpus
        else:
            match = needle in item.text(0).lower()

        any_child_match = False
        for j in range(item.childCount()):
            child_matched = self._filter_item_recursive(item.child(j), needle)
            if child_matched:
                any_child_match = True

        visible = match or any_child_match
        item.setHidden(not visible)
        if visible and needle:
            item.setExpanded(True)
        return visible

    def _on_tree_selection_changed(self) -> None:
        """Triggered when an item in the device tree is selected."""
        items = self.tree.selectedItems()
        if not items:
            self._show_system_summary()
            return

        item = items[0]
        dev: DeviceInfo | None = item.data(0, Qt.ItemDataRole.UserRole)
        if dev is None:
            self._show_system_summary()
        else:
            self.selected_device = dev
            self._show_device_details(dev)

    def _clear_left_layout(self) -> None:
        """Recursively detaches and cleans all widgets and sub-layouts in left pane."""
        def _clear_item(item):
            w = item.widget()
            if w is not None:
                w.setParent(None)
                w.deleteLater()
            l = item.layout()
            if l is not None:
                while l.count():
                    _clear_item(l.takeAt(0))

        while self.left_layout.count():
            item = self.left_layout.takeAt(0)
            if item is not None:
                _clear_item(item)

    def _show_system_summary(self) -> None:
        """Renders system hardware and inventory card when no specific device is selected."""
        self._clear_left_layout()
        self.selected_device = None

        header_frame = QFrame()
        header_frame.setStyleSheet("""
            QFrame {
                background-color: #222428;
                border: 1px solid #2d3036;
                border-radius: 4px;
                padding: 8px;
            }
        """)
        h_layout = QVBoxLayout(header_frame)
        h_layout.setSpacing(4)

        title = QLabel(f"💻 {self.summary.hostname or tr('lbl_system_overview')}")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #6899e6;")
        h_layout.addWidget(title)

        os_info = f"<b>Distribution:</b> {self.summary.distro} | <b>Kernel:</b> {self.summary.kernel} ({self.summary.arch})"
        lbl_os = QLabel(os_info)
        lbl_os.setStyleSheet("color: #e3e5e8; font-size: 12px;")
        h_layout.addWidget(lbl_os)

        if self.summary.motherboard:
            lbl_mb = QLabel(f"<b>Motherboard:</b> {self.summary.motherboard} (BIOS {self.summary.bios_version} {self.summary.bios_date})")
            lbl_mb.setStyleSheet("color: #9498a1; font-size: 11px;")
            h_layout.addWidget(lbl_mb)

        self.left_layout.addWidget(header_frame)

        inv_box = QGroupBox(tr("lbl_hardware_inventory"))
        inv_layout = QGridLayout(inv_box)
        inv_layout.setSpacing(6)

        inv_layout.addWidget(QLabel(tr("lbl_total_devices")), 0, 0)
        lbl_total = QLabel(str(self.summary.device_count_total))
        lbl_total.setStyleSheet("color: #57ab5a; font-weight: bold;")
        inv_layout.addWidget(lbl_total, 0, 1)

        inv_layout.addWidget(QLabel(tr("lbl_processors")), 0, 2)
        inv_layout.addWidget(QLabel(f"{self.summary.cpu_model} ({self.summary.cpu_cores} cores)"), 0, 3)

        inv_layout.addWidget(QLabel(tr("lbl_system_memory")), 1, 0)
        inv_layout.addWidget(QLabel(f"{self.summary.memory_used} / {self.summary.memory_total}"), 1, 1)

        dkms_count = len(self.backend.dkms_modules)
        inv_layout.addWidget(QLabel(tr("lbl_dkms_drivers")), 1, 2)
        lbl_dkms = QLabel(f"{dkms_count} installed ({', '.join(sorted(self.backend.dkms_modules)) or 'none'})")
        lbl_dkms.setStyleSheet("color: #b58ae6;" if dkms_count else "color: #9498a1;")
        inv_layout.addWidget(lbl_dkms, 1, 3)

        self.left_layout.addWidget(inv_box)

        counts_box = QGroupBox(tr("lbl_discovered_categories"))
        c_layout = QGridLayout(counts_box)
        c_layout.setSpacing(4)

        sorted_counts = sorted(
            self.summary.device_counts_by_category.items(),
            key=lambda x: CATEGORY_METADATA.get(x[0], ("❓", 999))[1],
        )

        for idx, (cat_name, count) in enumerate(sorted_counts):
            icon, _ = CATEGORY_METADATA.get(cat_name, ("🧩", 120))
            row = idx // 2
            col = (idx % 2) * 2

            lbl_cat = QLabel(f"{icon} {cat_name}:")
            lbl_cat.setStyleSheet("color: #e3e5e8; font-size: 12px;")
            c_layout.addWidget(lbl_cat, row, col)

            lbl_cnt = QLabel(f"<b>{count}</b>")
            lbl_cnt.setStyleSheet("color: #6899e6; font-size: 12px;")
            c_layout.addWidget(lbl_cnt, row, col + 1)

        self.left_layout.addWidget(counts_box)

        tip_lbl = QLabel(tr("lbl_tip_card"))
        tip_lbl.setWordWrap(True)
        tip_lbl.setStyleSheet("""
            background-color: #18191c;
            color: #d49a3d;
            border-left: 3px solid #d49a3d;
            padding: 6px 8px;
            border-radius: 3px;
            font-size: 11px;
            line-height: 1.3;
        """)
        self.left_layout.addWidget(tip_lbl)
        self.left_layout.addStretch()

    def _show_device_details(self, dev: DeviceInfo) -> None:
        """Renders comprehensive device property inspector for the selected device."""
        self._clear_left_layout()

        # 1. Device Header Card
        header_frame = QFrame()
        header_frame.setStyleSheet("""
            QFrame {
                background-color: #222428;
                border: 1px solid #2d3036;
                border-radius: 4px;
                padding: 8px;
            }
        """)
        h_layout = QVBoxLayout(header_frame)
        h_layout.setSpacing(3)

        top_row = QHBoxLayout()
        icon_lbl = QLabel(dev.category_icon)
        icon_lbl.setStyleSheet("font-size: 22px;")
        top_row.addWidget(icon_lbl)

        title_col = QVBoxLayout()
        title_col.setSpacing(1)

        name_lbl = QLabel(dev.name)
        name_lbl.setStyleSheet("font-size: 14px; font-weight: bold; color: #e3e5e8;")
        name_lbl.setWordWrap(True)
        title_col.addWidget(name_lbl)

        sub_lbl = QLabel(f"{dev.category}  •  Bus: {dev.bus_type.upper()}")
        sub_lbl.setStyleSheet("color: #6899e6; font-size: 11px; font-weight: 600;")
        title_col.addWidget(sub_lbl)

        top_row.addLayout(title_col, stretch=1)
        h_layout.addLayout(top_row)
        self.left_layout.addWidget(header_frame)

        # 2. Driver & Kernel Module Inspector Card
        drv_box = QGroupBox(tr("group_driver_module"))
        d_layout = QGridLayout(drv_box)
        d_layout.setSpacing(6)

        badge_color = "#9498a1"
        badge_bg = "#2b2d33"
        if dev.driver_type == "dkms":
            badge_color = "#b58ae6"
            badge_bg = "#302242"
        elif dev.driver_type == "module":
            badge_color = "#57ab5a"
            badge_bg = "#193022"
        elif dev.driver_type == "builtin":
            badge_color = "#6899e6"
            badge_bg = "#1b2c47"

        lbl_status_badge = QLabel(f"  {dev.driver_type_label}  ")
        lbl_status_badge.setStyleSheet(f"""
            background-color: {badge_bg};
            color: {badge_color};
            font-weight: 600;
            font-size: 11px;
            border-radius: 3px;
            padding: 2px 6px;
        """)
        d_layout.addWidget(QLabel(tr("lbl_driver_status")), 0, 0)
        d_layout.addWidget(lbl_status_badge, 0, 1)

        d_layout.addWidget(QLabel(tr("lbl_driver_name")), 1, 0)
        d_layout.addWidget(QLabel(dev.driver_name or tr("val_driverless")), 1, 1)

        if dev.driver_module_path:
            d_layout.addWidget(QLabel(tr("lbl_module_path")), 2, 0)
            lbl_path = QLabel(dev.driver_module_path)
            lbl_path.setWordWrap(True)
            lbl_path.setStyleSheet("color: #9498a1; font-family: monospace; font-size: 11px;")
            d_layout.addWidget(lbl_path, 2, 1)

        if dev.driver_memory_size:
            d_layout.addWidget(QLabel(tr("lbl_ram_footprint")), 3, 0)
            d_layout.addWidget(QLabel(dev.driver_memory_size), 3, 1)

        if dev.driver_used_by:
            d_layout.addWidget(QLabel(tr("lbl_used_by")), 4, 0)
            d_layout.addWidget(QLabel(", ".join(dev.driver_used_by)), 4, 1)

        if dev.driver_version:
            d_layout.addWidget(QLabel(tr("lbl_version")), 5, 0)
            d_layout.addWidget(QLabel(dev.driver_version), 5, 1)

        if dev.driver_license:
            d_layout.addWidget(QLabel(tr("lbl_license")), 6, 0)
            d_layout.addWidget(QLabel(dev.driver_license), 6, 1)

        self.left_layout.addWidget(drv_box)

        # 3. Hardware Identifiers Box
        hw_box = QGroupBox(tr("group_hw_identifiers"))
        hw_layout = QGridLayout(hw_box)
        hw_layout.setSpacing(6)

        row = 0
        if dev.vendor_id:
            hw_layout.addWidget(QLabel(tr("lbl_vendor_id")), row, 0)
            hw_layout.addWidget(QLabel(f"<code>{dev.vendor_id}</code> ({dev.vendor_name or tr('val_unknown')})"), row, 1)
            row += 1

        if dev.product_id:
            hw_layout.addWidget(QLabel(tr("lbl_product_id")), row, 0)
            hw_layout.addWidget(QLabel(f"<code>{dev.product_id}</code> ({dev.product_name or tr('val_unknown')})"), row, 1)
            row += 1

        if dev.subsystem_vendor or dev.subsystem_device:
            hw_layout.addWidget(QLabel(tr("lbl_subsystem_id")), row, 0)
            hw_layout.addWidget(QLabel(f"<code>{dev.subsystem_vendor}:{dev.subsystem_device}</code>"), row, 1)
            row += 1

        if dev.pci_slot:
            hw_layout.addWidget(QLabel(tr("lbl_pci_slot")), row, 0)
            hw_layout.addWidget(QLabel(f"<code>{dev.pci_slot}</code>"), row, 1)
            row += 1

        if dev.usb_port:
            hw_layout.addWidget(QLabel(tr("lbl_usb_port")), row, 0)
            hw_layout.addWidget(QLabel(f"Port {dev.usb_port}  •  {dev.usb_speed or tr('val_standard')}"), row, 1)
            row += 1

        if dev.device_node:
            hw_layout.addWidget(QLabel(tr("lbl_device_node")), row, 0)
            node_widget = QWidget()
            node_row = QHBoxLayout(node_widget)
            node_row.setContentsMargins(0, 0, 0, 0)
            node_row.setSpacing(4)
            node_row.addWidget(QLabel(f"<code>{dev.device_node}</code>"))

            ownership = PackageManagerInspector.check_file_owner(dev.device_node)
            if ownership.is_managed:
                badge = PackageOwnershipBadge(ownership)
                node_row.addWidget(badge)
            node_row.addStretch()
            hw_layout.addWidget(node_widget, row, 1)
            row += 1

        if dev.sysfs_path:
            hw_layout.addWidget(QLabel(tr("lbl_sysfs_path")), row, 0)
            lbl_sysfs = QLabel(dev.sysfs_path)
            lbl_sysfs.setWordWrap(True)
            lbl_sysfs.setStyleSheet("font-family: monospace; font-size: 11px; color: #9498a1;")
            hw_layout.addWidget(lbl_sysfs, row, 1)
            row += 1

        if dev.modalias:
            hw_layout.addWidget(QLabel(tr("lbl_modalias")), row, 0)
            lbl_mod = QLabel(dev.modalias)
            lbl_mod.setWordWrap(True)
            lbl_mod.setStyleSheet("font-family: monospace; font-size: 11px; color: #9498a1;")
            hw_layout.addWidget(lbl_mod, row, 1)
            row += 1

        if dev.power_state:
            hw_layout.addWidget(QLabel(tr("lbl_power_runtime")), row, 0)
            hw_layout.addWidget(QLabel(f"{dev.power_state} (Wakeup: {dev.wakeup_enabled or tr('val_unspecified')})"), row, 1)
            row += 1

        self.left_layout.addWidget(hw_box)

        # 4. Educational Action Buttons (wrapped in container widget to prevent layout leaks)
        btn_container = QWidget()
        btn_bar = QHBoxLayout(btn_container)
        btn_bar.setContentsMargins(0, 2, 0, 2)
        btn_bar.setSpacing(6)

        if dev.vendor_id and dev.product_id:
            btn_copy_hw = QPushButton(tr("btn_copy_hw_id"))
            btn_copy_hw.setToolTip(format_tooltip(
                tr("tooltip_copy_hw_title"),
                tr("tooltip_copy_hw_syntax", vendor=dev.vendor_id, product=dev.product_id),
                tr("tooltip_copy_hw_desc", vendor=dev.vendor_id, product=dev.product_id),
                "Safe",
            ))
            btn_copy_hw.clicked.connect(lambda: self._copy_text(f"{dev.vendor_id}:{dev.product_id}", "Hardware ID"))
            btn_bar.addWidget(btn_copy_hw)

        if dev.modalias:
            btn_copy_mod = QPushButton(tr("btn_copy_modalias"))
            btn_copy_mod.setToolTip(format_tooltip(
                tr("tooltip_copy_mod_title"),
                dev.modalias[:40] + "...",
                tr("tooltip_copy_mod_desc"),
                "Safe",
            ))
            btn_copy_mod.clicked.connect(lambda: self._copy_text(dev.modalias, "Modalias"))
            btn_bar.addWidget(btn_copy_mod)

        if dev.bus_type in ("usb", "pci"):
            btn_udev = QPushButton(tr("btn_open_udev"))
            btn_udev.setToolTip(format_tooltip(
                tr("tooltip_open_udev_title"),
                tr("tooltip_open_udev_syntax", bus=dev.bus_type),
                tr("tooltip_open_udev_desc"),
                "Safe",
            ))
            btn_udev.clicked.connect(lambda: self._open_in_udev(dev))
            btn_bar.addWidget(btn_udev)

        if dev.driver_name and dev.driver_type in ("module", "dkms"):
            btn_reload = QPushButton(tr("btn_reload_driver"))
            btn_reload.setToolTip(format_tooltip(
                tr("tooltip_reload_driver_title"),
                tr("tooltip_reload_driver_syntax", name=dev.driver_name),
                tr("tooltip_reload_driver_desc", name=dev.driver_name),
                tr("tooltip_reload_driver_impact"),
            ))
            btn_reload.clicked.connect(lambda: self._reload_driver(dev.driver_name))
            btn_bar.addWidget(btn_reload)

        self.left_layout.addWidget(btn_container)

        # 5. Raw Properties & Attributes Table
        if dev.properties:
            prop_box = QGroupBox(tr("group_raw_properties"))
            p_layout = QVBoxLayout(prop_box)
            p_layout.setContentsMargins(4, 4, 4, 4)

            tbl = QTableWidget(len(dev.properties), 2)
            tbl.setHorizontalHeaderLabels([tr("col_attribute"), tr("col_value")])
            tbl.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
            tbl.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
            tbl.setColumnWidth(0, 150)
            tbl.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)

            for idx, (k, v) in enumerate(sorted(dev.properties.items())):
                k_item = QTableWidgetItem(k)
                k_item.setFont(QFont("monospace", 10))
                v_item = QTableWidgetItem(str(v))
                v_item.setFont(QFont("monospace", 10))
                tbl.setItem(idx, 0, k_item)
                tbl.setItem(idx, 1, v_item)

            tbl.setMaximumHeight(180)
            p_layout.addWidget(tbl)
            self.left_layout.addWidget(prop_box)

        self.left_layout.addStretch()

    def _copy_text(self, text: str, label: str) -> None:
        """Copies text to the system clipboard and notifies via preview banner."""
        QApplication.clipboard().setText(text)
        self.preview_banner.set_text(text)
        self.preview_banner.set_subtitle(tr("preview_sub_copied", label=label))

    def _open_in_udev(self, dev: DeviceInfo) -> None:
        """Launches udev-gui and copies rule snippet."""
        rule_snippet = f'SUBSYSTEM=="{dev.bus_type}", '
        if dev.vendor_id:
            rule_snippet += f'ATTR{{idVendor}}=="{dev.vendor_id}", '
        if dev.product_id:
            rule_snippet += f'ATTR{{idProduct}}=="{dev.product_id}", '
        rule_snippet += 'MODE="0666"'

        QApplication.clipboard().setText(rule_snippet)

        try:
            from udev_gui.ui import UdevMainWindow
            win = UdevMainWindow()
            win.show()
            self._child_windows = getattr(self, "_child_windows", [])
            self._child_windows.append(win)
            self.preview_banner.set_text(rule_snippet)
            self.preview_banner.set_subtitle(tr("preview_sub_udev_opened"))
        except Exception:
            QMessageBox.information(
                self,
                tr("title_udev_snippet_copied"),
                tr("msg_udev_snippet_copied", snippet=rule_snippet),
            )

    def _reload_driver(self, module_name: str) -> None:
        """Prompts safety confirmation dialog before reloading kernel driver module."""
        if not module_name:
            QMessageBox.warning(self, tr("title_no_driver"), tr("msg_no_driver"))
            return

        cmd = f"modprobe -r {module_name} && modprobe {module_name}"
        self.preview_banner.set_text(cmd)
        self.preview_banner.set_subtitle(tr("preview_sub_reload_cmd", name=module_name))

        dlg = SafetyExecutionDialog(
            title=tr("dialog_reload_driver_title"),
            target_path_or_command=cmd,
            safety_notes=[
                tr("note_unload_module", name=module_name),
                tr("note_reload_module", name=module_name),
                tr("note_device_reset"),
                tr("note_root_privileges"),
            ],
            parent=self,
        )

        if dlg.exec() == SafetyExecutionDialog.DialogCode.Accepted:
            res = SafeExecutor.run_command(["sh", "-c", cmd], elevated=True)
            if res.success:
                self.preview_banner.set_text(tr("preview_text_reloaded", name=module_name))
                self.preview_banner.set_subtitle(tr("preview_sub_reload_done"))
                QMessageBox.information(
                    self,
                    tr("title_driver_reloaded"),
                    tr("msg_driver_reloaded", name=module_name),
                )
                self.refresh_devices()
            else:
                err_msg = res.stderr.strip() or res.stdout.strip() or "Failed to reload module (it may be in use by other kernel subsystems)."
                self.preview_banner.set_text(tr("preview_text_reload_err", name=module_name))
                self.preview_banner.set_subtitle(tr("preview_sub_reload_err"))
                QMessageBox.warning(
                    self,
                    tr("title_driver_reload_notice"),
                    tr("msg_driver_reload_notice", name=module_name, error=err_msg),
                )

    def _export_report(self) -> None:
        """Exports a full hardware and driver status report to a dialog or file."""
        lines = [
            "# Linux System GUIs — Hardware & Driver Inventory Report",
            f"- Hostname: {self.summary.hostname}",
            f"- OS: {self.summary.distro} ({self.summary.arch})",
            f"- Kernel: {self.summary.kernel}",
            f"- Motherboard: {self.summary.motherboard} (BIOS {self.summary.bios_version})",
            f"- CPU: {self.summary.cpu_model} ({self.summary.cpu_cores} cores)",
            f"- Memory: {self.summary.memory_used} / {self.summary.memory_total}",
            f"- Total Devices: {len(self.devices)}",
            "",
            "## Devices by Category:",
        ]

        grouped: dict[str, list[DeviceInfo]] = {}
        for d in self.devices:
            grouped.setdefault(d.category, []).append(d)

        for cat, dlist in sorted(grouped.items()):
            lines.append(f"\n### {cat} ({len(dlist)})")
            for dev in dlist:
                hw = f"[{dev.vendor_id}:{dev.product_id}]" if dev.vendor_id and dev.product_id else dev.pci_slot
                lines.append(f"- **{dev.name}** {hw}")
                lines.append(f"  - Driver: `{dev.driver_name or 'None'}` ({dev.driver_type_label})")
                if dev.device_node:
                    lines.append(f"  - Device Node: `{dev.device_node}`")
                if dev.sysfs_path:
                    lines.append(f"  - Sysfs: `{dev.sysfs_path}`")

        report_text = "\n".join(lines)

        dlg = QDialog(self)
        dlg.setWindowTitle(tr("dialog_report_title"))
        dlg.resize(720, 520)
        d_layout = QVBoxLayout(dlg)
        d_layout.setContentsMargins(10, 10, 10, 10)
        d_layout.setSpacing(6)

        txt = QTextEdit()
        txt.setPlainText(report_text)
        txt.setReadOnly(True)
        txt.setFont(QFont("monospace", 10))
        d_layout.addWidget(txt)

        btn_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        btn_copy = btn_box.addButton(tr("btn_copy_clipboard"), QDialogButtonBox.ButtonRole.ActionRole)
        btn_copy.clicked.connect(lambda: self._copy_text(report_text, tr("val_report_label")))
        btn_box.rejected.connect(dlg.reject)
        d_layout.addWidget(btn_box)

        dlg.exec()

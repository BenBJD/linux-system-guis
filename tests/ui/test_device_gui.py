"""GUI tests for DeviceMainWindow using pytest-qt."""

from unittest.mock import MagicMock, patch
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QLabel, QPushButton
from device_gui.backend import DeviceInfo
from device_gui.ui import DeviceMainWindow
from linux_gui_core.runner.executor import ExecutionResult


def test_device_window_init(qapp, qtbot):
    win = DeviceMainWindow()
    qtbot.addWidget(win)

    assert "Device Manager" in win.windowTitle()
    assert win.tree is not None
    assert win.txt_search is not None
    assert win.cmb_view_mode is not None


def test_device_tree_selection_and_inspector(qapp, qtbot):
    win = DeviceMainWindow()
    qtbot.addWidget(win)

    # Provide controlled test devices
    test_dev = DeviceInfo(
        id="pci:0000:01:00.0",
        name="Test Graphics Card",
        category="Display Adapters",
        category_icon="🖥️",
        bus_type="pci",
        vendor_name="TestVendor",
        vendor_id="10de",
        product_name="TestGPU",
        product_id="2489",
        driver_name="test_driver",
        driver_type="module",
        driver_type_label="Active (Kernel Module)",
        driver_module_path="/lib/modules/test.ko",
        device_node="/dev/dri/card0",
        properties={"BUS": "PCI", "TEST_KEY": "TEST_VAL"},
    )
    win.devices = [test_dev]
    win.summary = win.backend.get_system_summary(win.devices)
    win._rebuild_tree()

    # Tree should have 1 category item with 1 child
    assert win.tree.topLevelItemCount() == 1
    cat_item = win.tree.topLevelItem(0)
    assert "Display Adapters" in cat_item.text(0)
    assert cat_item.childCount() == 1

    child_item = cat_item.child(0)
    assert "Test Graphics Card" in child_item.text(0)
    assert "test_driver" in child_item.text(1)

    # Select child item
    win.tree.setCurrentItem(child_item)
    assert win.selected_device == test_dev

    # Left pane should have rendered device details
    rendered_labels = [lbl.text() for lbl in win.left_container.findChildren(QLabel)]
    assert any("Test Graphics Card" in t for t in rendered_labels)
    assert any("Active (Kernel Module)" in t for t in rendered_labels)
    assert any("10de" in t for t in rendered_labels)


def test_left_pane_clearing_prevents_duplicate_buttons(qapp, qtbot):
    """Ensures repeated selections cleanly destroy old buttons without duplicate button bars."""
    win = DeviceMainWindow()
    qtbot.addWidget(win)

    dev1 = DeviceInfo(
        id="usb:1",
        name="Device One",
        category="Input Devices",
        category_icon="⌨️",
        bus_type="usb",
        vendor_id="046d",
        product_id="c077",
        driver_name="usbhid",
        driver_type="module",
    )
    dev2 = DeviceInfo(
        id="usb:2",
        name="Device Two",
        category="Input Devices",
        category_icon="⌨️",
        bus_type="usb",
        vendor_id="046d",
        product_id="c078",
        driver_name="usbhid",
        driver_type="module",
    )
    win.devices = [dev1, dev2]
    win.summary = win.backend.get_system_summary(win.devices)
    win._rebuild_tree()

    # Select dev1
    win._show_device_details(dev1)
    buttons_first = win.left_container.findChildren(QPushButton)
    assert len(buttons_first) > 0
    first_btn_count = len(buttons_first)

    # Select dev2 repeatedly
    win._show_device_details(dev2)
    win._show_device_details(dev1)
    win._show_device_details(dev2)

    buttons_after = [b for b in win.left_container.findChildren(QPushButton) if b.isVisibleTo(win.left_container)]
    # Button count should not multiply or accumulate
    assert len(buttons_after) == first_btn_count


def test_reload_driver_confirmation_and_execution(qapp, qtbot):
    """Verifies _reload_driver properly instantiates SafetyExecutionDialog and handles execution."""
    win = DeviceMainWindow()
    qtbot.addWidget(win)

    with (
        patch("device_gui.ui.SafetyExecutionDialog") as mock_dialog_cls,
        patch("device_gui.ui.SafeExecutor.run_command") as mock_run_cmd,
        patch("device_gui.ui.QMessageBox.information") as mock_msg,
    ):
        mock_dialog_instance = MagicMock()
        mock_dialog_instance.exec.return_value = 1  # Accepted
        mock_dialog_cls.return_value = mock_dialog_instance
        mock_dialog_cls.DialogCode.Accepted = 1

        mock_run_cmd.return_value = ExecutionResult(
            success=True,
            stdout="Module reloaded successfully",
            stderr="",
            command_executed="sh -c modprobe -r testmod && modprobe testmod",
        )

        win._reload_driver("testmod")

        mock_dialog_cls.assert_called_once()
        args, kwargs = mock_dialog_cls.call_args
        assert kwargs["title"] == "Confirm Kernel Driver Reload"
        assert "modprobe -r testmod && modprobe testmod" in kwargs["target_path_or_command"]
        assert len(kwargs["safety_notes"]) > 0

        mock_run_cmd.assert_called_once_with(
            ["sh", "-c", "modprobe -r testmod && modprobe testmod"],
            elevated=True,
        )
        mock_msg.assert_called_once()


def test_device_tree_search_filter(qapp, qtbot):
    win = DeviceMainWindow()
    qtbot.addWidget(win)

    dev1 = DeviceInfo(id="1", name="Logitech Mouse", category="Human Interface Devices (HID)", category_icon="⌨️", vendor_id="046d")
    dev2 = DeviceInfo(id="2", name="NVIDIA GPU", category="Display Adapters", category_icon="🖥️", vendor_id="10de")
    win.devices = [dev1, dev2]
    win.summary = win.backend.get_system_summary(win.devices)
    win._rebuild_tree()

    # Filter for 'mouse'
    win.txt_search.setText("mouse")
    # Category with mouse should be visible, GPU hidden
    top_items = [win.tree.topLevelItem(i) for i in range(win.tree.topLevelItemCount())]
    visible_tops = [t for t in top_items if not t.isHidden()]
    assert len(visible_tops) == 1
    assert "Human Interface Devices" in visible_tops[0].text(0)

    # Clear filter
    win.txt_search.setText("")
    visible_tops = [t for t in top_items if not t.isHidden()]
    assert len(visible_tops) == 2


def test_device_view_mode_toggle(qapp, qtbot):
    win = DeviceMainWindow()
    qtbot.addWidget(win)

    dev = DeviceInfo(id="1", name="Test Device", category="Display Adapters", category_icon="🖥️")
    win.devices = [dev]
    win.summary = win.backend.get_system_summary(win.devices)

    # Category mode
    win.cmb_view_mode.setCurrentIndex(0)
    win._rebuild_tree()
    assert win.tree.topLevelItemCount() == 1
    assert "Display Adapters" in win.tree.topLevelItem(0).text(0)

    # Connection mode
    win.cmb_view_mode.setCurrentIndex(1)
    win._rebuild_tree()
    assert win.tree.topLevelItemCount() == 1
    assert "System Hardware" in win.tree.topLevelItem(0).text(0) or win.summary.hostname in win.tree.topLevelItem(0).text(0)


def test_copy_hardware_id(qapp, qtbot):
    win = DeviceMainWindow()
    qtbot.addWidget(win)

    win._copy_text("10de:2489", "Hardware ID")
    assert QApplication.clipboard().text() == "10de:2489"

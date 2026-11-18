"""GUI tests for FstabMainWindow using pytest-qt."""

from fstab_gui.ui import ADVANCED_FSTAB_OPTIONS, AdvancedFstabOptionDialog, FstabMainWindow
from linux_gui_core.widgets.loading_modal import OptionCatalogRowWidget


def test_fstab_window_init(qapp, qtbot, tmp_path, sample_fstab):
    mock_file = tmp_path / "fstab"
    mock_file.write_text(sample_fstab)

    window = FstabMainWindow(fstab_path=str(mock_file))
    qtbot.addWidget(window)

    assert "fstab Editor" in window.windowTitle()
    assert window.table.rowCount() == 5

    # Check top live preview banner matches selected entry
    banner = window.preview_banner.get_text()
    assert len(banner) > 0


def test_fstab_toggle_option(qapp, qtbot, tmp_path, sample_fstab):
    mock_file = tmp_path / "fstab"
    mock_file.write_text(sample_fstab)

    window = FstabMainWindow(fstab_path=str(mock_file))
    qtbot.addWidget(window)

    # Select first row
    window.table.selectRow(0)

    # Toggle nofail option checkbox
    assert "nofail" in window.option_checkboxes
    window.option_checkboxes["nofail"].setChecked(True)
    banner = window.preview_banner.get_text()
    assert "nofail" in banner


def test_advanced_fstab_option_dialog_cards_and_search(qapp, qtbot):
    dlg = AdvancedFstabOptionDialog()
    qtbot.addWidget(dlg)

    assert dlg.list_widget.count() == len(ADVANCED_FSTAB_OPTIONS)
    first_item = dlg.list_widget.item(0)
    card_widget = dlg.list_widget.itemWidget(first_item)
    assert isinstance(card_widget, OptionCatalogRowWidget)

    # Search filter hides non-matching items using the structured metadata
    dlg.txt_search.setText("zstd")
    visible_items = [
        dlg.list_widget.item(i)
        for i in range(dlg.list_widget.count())
        if not dlg.list_widget.item(i).isHidden()
    ]
    assert len(visible_items) == 1
    assert visible_items[0].data(0x0100) == "compress=zstd"


def test_fstab_and_udev_tables_are_non_editable_and_udev_run_command(qapp, qtbot, tmp_path, sample_fstab):
    from PyQt6.QtWidgets import QTableWidget
    from udev_gui.ui import UdevMainWindow

    mock_file = tmp_path / "fstab"
    mock_file.write_text(sample_fstab)

    fstab_win = FstabMainWindow(fstab_path=str(mock_file))
    qtbot.addWidget(fstab_win)
    assert fstab_win.table.editTriggers() == QTableWidget.EditTrigger.NoEditTriggers
    assert fstab_win.tbl_adv.editTriggers() == QTableWidget.EditTrigger.NoEditTriggers

    rules_dir = tmp_path / "rules.d"
    rules_dir.mkdir()
    rule_file = rules_dir / "99-thinkpad-touchpad.rules"
    rule_file.write_text(
        'ACTION=="add", SUBSYSTEM=="hidraw", ATTRS{name}=="*Touchpad*", '
        'RUN+="/usr/local/bin/tp-haptics --resistance 40"\n'
    )

    udev_win = UdevMainWindow(rules_dir=str(rules_dir))
    qtbot.addWidget(udev_win)
    assert udev_win.table.editTriggers() == QTableWidget.EditTrigger.NoEditTriggers
    assert udev_win.tbl_extras.editTriggers() == QTableWidget.EditTrigger.NoEditTriggers

    # Verify parsed fields populate the main window controls
    assert udev_win.txt_run_cmd.text() == "/usr/local/bin/tp-haptics --resistance 40"
    assert udev_win.txt_attr_match_val.text() == "*Touchpad*"

    # Modify RUN+= command and verify live preview banner updates
    udev_win.txt_run_cmd.setText("/usr/local/bin/tp-haptics --resistance 60 --click 2")
    udev_win.cmb_wakeup.setCurrentIndex(1)  # disabled
    preview = udev_win.preview_banner.get_text()
    assert 'RUN+="/usr/local/bin/tp-haptics --resistance 60 --click 2"' in preview
    assert 'ATTR{power/wakeup}="disabled"' in preview



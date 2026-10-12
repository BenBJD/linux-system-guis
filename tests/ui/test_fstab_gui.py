"""GUI tests for FstabMainWindow using pytest-qt."""

from fstab_gui.ui import FstabMainWindow


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

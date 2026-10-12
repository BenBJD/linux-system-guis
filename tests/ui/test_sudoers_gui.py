"""GUI tests for SudoersMainWindow using pytest-qt."""

from sudoers_gui.ui import SudoersMainWindow
from sudoers_gui.parser import SudoersRule


def test_sudoers_window_init(qapp, qtbot, tmp_path):
    mock_d = tmp_path / "sudoers.d"
    mock_d.mkdir()

    window = SudoersMainWindow(target_dir=str(mock_d))
    qtbot.addWidget(window)

    assert window.windowTitle() == "Sudoers Privilege Manager (visudo safe)"
    assert window.cmb_files.count() >= 1

    # Verify live preview banner exists
    banner_text = window.preview_banner.get_text()
    assert len(banner_text) > 0


def test_sudoers_rule_builder_interaction(qapp, qtbot, tmp_path):
    mock_d = tmp_path / "sudoers.d"
    mock_d.mkdir()

    window = SudoersMainWindow(target_dir=str(mock_d))
    qtbot.addWidget(window)

    # Inject mock rules to avoid reading host /etc/sudoers
    window._cached_contents["/etc/sudoers"] = "root ALL=(ALL) ALL\n%wheel ALL=(ALL) ALL\n"
    window._on_file_selected()

    assert window.table.rowCount() == 2

    # Toggle NOPASSWD on first selected rule
    window.chk_nopasswd.setChecked(True)
    banner_text = window.preview_banner.get_text()
    assert "NOPASSWD:" in banner_text


def test_sudoers_tabs_switching(qapp, qtbot, tmp_path):
    mock_d = tmp_path / "sudoers.d"
    mock_d.mkdir()

    window = SudoersMainWindow(target_dir=str(mock_d))
    qtbot.addWidget(window)

    # Switch to Raw Editor tab
    window.tabs.setCurrentIndex(1)
    raw_text = window.raw_editor.toPlainText()
    assert isinstance(raw_text, str)

    # Switch back to Visual Builder tab
    window.tabs.setCurrentIndex(0)
    assert window.table.rowCount() >= 0

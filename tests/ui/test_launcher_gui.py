"""GUI tests for LauncherMainWindow hub using pytest-qt."""

from linux_system_guis.main import LauncherMainWindow


def test_launcher_hub_cards(qapp, qtbot):
    launcher = LauncherMainWindow()
    qtbot.addWidget(launcher)

    # Launcher should have all 9 tool cards
    assert len(launcher.cards) == 9

    # Filter cards by 'visudo'
    launcher.txt_filter.setText("visudo")
    visible_cards = [c for c in launcher.cards if not c.isHidden()]
    assert len(visible_cards) == 1

    # Filter cards by 'journal'
    launcher.txt_filter.setText("journal")
    visible_cards = [c for c in launcher.cards if not c.isHidden()]
    assert len(visible_cards) == 1

    # Clear filter
    launcher.txt_filter.setText("")
    visible_cards = [c for c in launcher.cards if not c.isHidden()]
    assert len(visible_cards) == 9

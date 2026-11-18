"""GUI tests for LauncherMainWindow hub and core UI fixes using pytest-qt."""

from PyQt6.QtWidgets import QGroupBox, QLabel, QTabWidget, QWidget

from linux_system_guis.main import LauncherMainWindow


def test_launcher_hub_cards(qapp, qtbot):
    launcher = LauncherMainWindow()
    qtbot.addWidget(launcher)

    # Launcher should have all 10 tool cards
    assert len(launcher.cards) == 10

    # Ensure LauncherCard stylesheet is scoped to QFrame#launcherCard and QLabel has border: none
    first_card = launcher.cards[0]
    assert first_card.objectName() == "launcherCard"
    assert "QFrame#launcherCard" in first_card.styleSheet()
    for lbl in first_card.findChildren(QLabel):
        assert "border: none" in lbl.styleSheet() or "QLabel" in first_card.styleSheet()

    # Filter cards by 'visudo'
    launcher.txt_filter.setText("visudo")
    visible_cards = [c for c in launcher.cards if not c.isHidden()]
    assert len(visible_cards) == 1

    # Filter cards by 'device'
    launcher.txt_filter.setText("device")
    visible_cards = [c for c in launcher.cards if not c.isHidden()]
    assert len(visible_cards) >= 1

    # Clear filter
    launcher.txt_filter.setText("")
    visible_cards = [c for c in launcher.cards if not c.isHidden()]
    assert len(visible_cards) == 10


def test_ampersand_escaping_in_tabs_and_groupboxes(qapp, qtbot):
    tabs = QTabWidget()
    qtbot.addWidget(tabs)
    tabs.addTab(QWidget(), "Timers & Scheduler")
    assert tabs.tabText(0) == "Timers && Scheduler"

    grp = QGroupBox("Authentication & Commands")
    qtbot.addWidget(grp)
    assert grp.title() == "Authentication && Commands"


def test_systemd_timer_editor_populates_and_updates_preview(qapp, qtbot, monkeypatch):
    from systemd_gui.manager import SystemdManager, TimerConfig, TimerUnit
    from systemd_gui.ui import SystemdMainWindow

    monkeypatch.setattr(SystemdManager, "list_services", classmethod(lambda cls, user_mode=False: []))
    sample_timer = TimerUnit(
        next_elapse="Tue 2026-10-27 00:00:00 GMT",
        left="1h 12min left",
        last_trigger="Mon 2026-10-26 00:00:01 GMT",
        passed="22h ago",
        unit="fstrim.timer",
        activates="fstrim.service",
        schedule_summary="OnCalendar=weekly, Persistent=true",
    )
    monkeypatch.setattr(SystemdManager, "list_timers", classmethod(lambda cls, user_mode=False: [sample_timer]))
    sample_cfg = TimerConfig(
        unit_name="fstrim.timer",
        activates="fstrim.service",
        description="Discard unused blocks once a week",
        fragment_path="/usr/lib/systemd/system/fstrim.timer",
        on_calendar="weekly",
        on_boot_sec="15min",
        on_unit_active_sec="1d",
        accuracy_sec="1h",
        randomized_delay_sec="6000",
        persistent=True,
        wake_system=False,
    )
    monkeypatch.setattr(
        SystemdManager,
        "get_timer_config",
        classmethod(lambda cls, unit_name, user_mode=False, activates="": sample_cfg),
    )

    win = SystemdMainWindow()
    qtbot.addWidget(win)

    # Check that tab title escaped '&' properly
    assert win.tabs.tabText(1) == "Timers && Scheduler"

    # First timer row is automatically selected and loaded into editor
    assert win.txt_timer_name.text() == "fstrim.timer"
    assert win.txt_activates_unit.text() == "fstrim.service"
    assert win.cmb_schedule.currentText() == "weekly"
    assert win.cmb_onbootsec.currentText() == "15min"
    assert win.cmb_onunitactivesec.currentText() == "1d"
    assert win.cmb_accuracysec.currentText() == "1h"
    assert win.cmb_randomizeddelaysec.currentText() == "6000"
    assert win.chk_persistent.isChecked() is True
    assert win.chk_wakesystem.isChecked() is False

    # Adjusting OnBootSec, FixedRandomDelay, OnClockChange, and WakeSystem updates the live preview banner
    win.cmb_onbootsec.setCurrentText("5min")
    win.cmb_onactivesec.setCurrentText("30s")
    win.chk_fixedrandomdelay.setChecked(True)
    win.chk_onclockchange.setChecked(True)
    win.chk_wakesystem.setChecked(True)
    preview_text = win.preview_banner.get_text()
    assert "OnBootSec=5min" in preview_text
    assert "OnActiveSec=30s" in preview_text
    assert "OnUnitActiveSec=1d" in preview_text
    assert "FixedRandomDelay=true" in preview_text
    assert "OnClockChange=true" in preview_text
    assert "Persistent=true" in preview_text
    assert "WakeSystem=true" in preview_text


def test_help_window_tabs_and_ansi_man_rendering(qapp, qtbot):
    from linux_gui_core.widgets.preview_banner import (
        LivePreviewBanner,
        ansi_man_to_terminal_html,
    )

    # 1. Verify ANSI SGR and backspace overstrikes produce clean HTML with zero ESC/BS chars
    raw_sample = "\x1b[4mFSTAB\x1b[24m(5)\n\x1b[1mNAME\x1b[0m\n    f\x08fs\x08st\x08ta\x08ab - see mount(8)"
    rendered_html = ansi_man_to_terminal_html(raw_sample)
    assert "\x1b" not in rendered_html
    assert "\x08" not in rendered_html
    assert "font-weight: bold" in rendered_html
    assert "text-decoration: underline" in rendered_html
    assert "href='man:mount(8)'" in rendered_html

    # 2. Verify LivePreviewBanner shows Help button, Arch Wiki links, and opens tabbed ManPageHelpWindow
    banner = LivePreviewBanner(
        title="Test Banner",
        subtitle="Test Subtitle",
        man_pages=["lspci(8)", "lsusb(8)", "modprobe(8)"],
    )
    qtbot.addWidget(banner)
    assert not banner.btn_help.isHidden()
    assert not banner.arch_wiki_label.isHidden()
    assert "https://wiki.archlinux.org/title/" in banner.arch_wiki_label.text()

    help_win = banner.open_help_window(initial_page="lsusb(8)")
    qtbot.addWidget(help_win)
    assert help_win.tabs.count() == 3
    assert "lsusb(8)" in help_win.tabs.tabText(help_win.tabs.currentIndex())
    assert not help_win.lbl_arch_wiki.isHidden()
    assert "https://wiki.archlinux.org/title/" in help_win.lbl_arch_wiki.text()
    # Ensure no raw ESC characters appear in the rendered QTextBrowser plain text
    assert "\x1b" not in help_win.viewer.toPlainText()
    help_win.close()


def test_structured_tooltip_and_interactive_popup_link(qapp, qtbot):
    from PyQt6.QtCore import QPoint
    from linux_gui_core.widgets.preview_banner import LivePreviewBanner
    from linux_gui_core.widgets.tooltips import InteractiveTooltipPopup, format_tooltip

    # 1. Arbitrary 'Safe' impact is omitted; blank behavior, default, and man link are structured
    tip_opt = format_tooltip(
        "Accuracy Window (AccuracySec=)",
        "AccuracySec=1min",
        "Specify the accuracy the timer shall elapse with.",
        "Safe",
        can_be_blank=True,
        blank_behavior="Uses systemd's default 1min coalescing window.",
        default_value="1min",
        man_page="systemd.timer(5)",
    )
    assert "Security / Safety:" not in tip_opt
    assert "Optional (Can be blank)" in tip_opt
    assert "Uses systemd's default 1min coalescing window." in tip_opt
    assert "1min" in tip_opt
    assert "href='man:systemd.timer(5)'" in tip_opt

    # 2. Required field with genuine security warning shows both
    tip_req = format_tooltip(
        "Passwordless Execution Tag",
        "NOPASSWD:",
        "Bypasses the sudo password prompt.",
        can_be_blank=False,
        blank_behavior="Required if passwordless execution is desired.",
        security="Critical Security Impact",
        man_page="sudoers(5)",
    )
    assert "Required (Cannot be blank)" in tip_req
    assert "Security / Safety:" in tip_req
    assert "Critical Security Impact" in tip_req

    # 3. Clicking the man: link inside InteractiveTooltipPopup opens the help window on that tab
    host = QWidget()
    host.preview_banner = LivePreviewBanner(man_pages=["systemd.service(5)", "systemd.timer(5)"])
    qtbot.addWidget(host)

    target_btn = QLabel("Test", parent=host)
    target_btn.setToolTip(tip_opt)

    popup = InteractiveTooltipPopup()
    qtbot.addWidget(popup)
    popup.show_for_widget(target_btn, QPoint(100, 100))
    assert popup.isVisible()

    # Simulate clicking the man:systemd.timer(5) link in the tooltip
    popup._on_link_activated("man:systemd.timer(5)")
    assert not popup.isVisible()
    help_win = getattr(host, "_man_help_window", None)
    assert help_win is not None
    assert "systemd.timer(5)" in help_win.tabs.tabText(help_win.tabs.currentIndex())
    help_win.close()


def test_loading_modal_and_background_worker(qapp, qtbot):
    from linux_gui_core.widgets.loading_modal import LoadingModal, run_with_loading_modal

    host = QWidget()
    qtbot.addWidget(host)

    res = run_with_loading_modal(
        host,
        title="Loading Test...",
        subtitle="Running background task...",
        task_fn=lambda: 42,
        force_show=True,
    )
    assert res == 42
    assert LoadingModal._active_instance is None





"""Unit tests for systemd manager state translations and unit parsing."""

from systemd_gui.manager import SystemdManager, TimerConfig


def test_translate_runtime_status():
    assert "Running" in SystemdManager._translate_runtime_status("active", "running", "loaded")
    assert "Failed" in SystemdManager._translate_runtime_status("failed", "failed", "loaded")
    assert "Stopped" in SystemdManager._translate_runtime_status("inactive", "dead", "loaded")
    assert "one-shot" in SystemdManager._translate_runtime_status("active", "exited", "loaded")


def test_translate_boot_status():
    assert "Runs on boot" in SystemdManager._translate_boot_status("enabled")
    assert "Manual" in SystemdManager._translate_boot_status("disabled")
    assert "Blocked" in SystemdManager._translate_boot_status("masked")


def test_parse_list_timers_output_full():
    sample_output = (
        "Tue 2026-10-27 00:00:00 GMT 1h 12min left Mon 2026-10-26 00:00:01 GMT 22h ago logrotate.timer              logrotate.service\n"
        "Tue 2026-10-27 00:25:17 GMT 1h 37min left Mon 2026-10-26 11:02:45 GMT 11h ago systemd-tmpfiles-clean.timer systemd-tmpfiles-clean.service\n"
        "-                           -             -                           -       fstrim.timer                 fstrim.service\n"
        "n/a                         n/a           Mon 2026-10-26 08:15:00 GMT 14h ago man-db.timer                 man-db.service\n"
    )
    timers = SystemdManager.parse_list_timers_output(sample_output)
    assert len(timers) == 4
    assert timers[0].unit == "logrotate.timer"
    assert timers[0].activates == "logrotate.service"
    assert timers[0].next_elapse == "Tue 2026-10-27 00:00:00 GMT"
    assert timers[0].left == "1h 12min left"
    assert timers[0].last_trigger == "Mon 2026-10-26 00:00:01 GMT"
    assert timers[0].passed == "22h ago"

    assert timers[1].unit == "systemd-tmpfiles-clean.timer"
    assert timers[1].activates == "systemd-tmpfiles-clean.service"

    assert timers[2].unit == "fstrim.timer"
    assert timers[2].next_elapse == "-"

    assert timers[3].unit == "man-db.timer"
    assert timers[3].next_elapse == "n/a"
    assert timers[3].last_trigger == "Mon 2026-10-26 08:15:00 GMT"


def test_parse_timer_unit_text_and_dropin_reset():
    raw_cat = """# /usr/lib/systemd/system/fstrim.timer
[Unit]
Description=Discard unused filesystem blocks once a week
Documentation=man:fstrim

[Timer]
OnCalendar=weekly
AccuracySec=1h
Persistent=true
RandomizedDelaySec=6000

# /etc/systemd/system/fstrim.timer.d/override.conf
[Timer]
OnCalendar=
OnCalendar=daily
OnBootSec=15min
OnUnitActiveSec=12h
WakeSystem=true
"""
    cfg = SystemdManager.parse_timer_unit_text("fstrim.timer", raw_cat)
    assert cfg.unit_name == "fstrim.timer"
    assert cfg.description == "Discard unused filesystem blocks once a week"
    assert cfg.on_calendar == "daily"
    assert cfg.on_boot_sec == "15min"
    assert cfg.on_unit_active_sec == "12h"
    assert cfg.accuracy_sec == "1h"
    assert cfg.randomized_delay_sec == "6000"
    assert cfg.persistent is True
    assert cfg.wake_system is True
    assert cfg.dropin_paths == ["/etc/systemd/system/fstrim.timer.d/override.conf"]


def test_timer_config_serialization():
    cfg = TimerConfig(
        unit_name="backup.timer",
        description="Daily system backup timer",
        activates="backup.service",
        on_calendar="*-*-* 03:00:00",
        on_boot_sec="10min",
        on_unit_active_sec="24h",
        randomized_delay_sec="5min",
        accuracy_sec="1min",
        persistent=True,
        wake_system=False,
    )
    override_text = cfg.to_override_content()
    assert "[Timer]" in override_text
    assert "OnCalendar=\nOnCalendar=*-*-* 03:00:00" in override_text
    assert "OnBootSec=10min" in override_text
    assert "OnUnitActiveSec=24h" in override_text
    assert "RandomizedDelaySec=5min" in override_text
    assert "AccuracySec=1min" in override_text
    assert "Persistent=true" in override_text

    unit_text = cfg.to_unit_file_content()
    assert "[Unit]" in unit_text
    assert "Description=Daily system backup timer" in unit_text
    assert "[Install]" in unit_text
    assert "WantedBy=timers.target" in unit_text


def test_timer_arch_wiki_flags_and_calendar_validation():
    raw_cat = """[Timer]
OnCalendar=weekly
RandomizedDelaySec=12h
FixedRandomDelay=true
OnClockChange=true
OnTimezoneChange=yes
"""
    cfg = SystemdManager.parse_timer_unit_text("weekly-maint.timer", raw_cat)
    assert cfg.fixed_random_delay is True
    assert cfg.on_clock_change is True
    assert cfg.on_timezone_change is True

    serialized = cfg.to_override_content()
    assert "FixedRandomDelay=true" in serialized
    assert "OnClockChange=true" in serialized
    assert "OnTimezoneChange=true" in serialized

    ok, out = SystemdManager.validate_calendar_expression("Mon..Fri 22:30")
    assert ok is True
    assert "Normalized form:" in out



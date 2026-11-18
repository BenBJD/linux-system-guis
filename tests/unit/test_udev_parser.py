"""Unit tests for udev rule parser and serializer."""

from udev_gui.parser import UdevParser, UdevRule


def test_parse_usb_device_rule():
    line = 'SUBSYSTEM=="usb", ATTR{idVendor}=="1234", ATTR{idProduct}=="5678", MODE="0666", TAG+="uaccess"'
    rule = UdevParser.parse_rule_line(line)
    assert rule.is_comment is False
    assert rule.subsystem == "usb"
    assert rule.vendor_id == "1234"
    assert rule.product_id == "5678"
    assert rule.mode == "0666"
    assert rule.tag_uaccess is True


def test_parse_power_wakeup_attribute():
    line = 'ACTION=="add", SUBSYSTEM=="input", ATTR{name}=="My Keyboard", ATTR{power/wakeup}="disabled"'
    rule = UdevParser.parse_rule_line(line)
    assert rule.action == "add"
    assert rule.subsystem == "input"
    assert any("power/wakeup" in t for t in rule.extra_tokens)


def test_udev_rule_to_line():
    rule = UdevRule(
        subsystem="usb",
        vendor_id="0403",
        product_id="6001",
        mode="0666",
        tag_uaccess=True,
    )
    line = rule.to_line()
    assert 'SUBSYSTEM=="usb"' in line
    assert 'ATTR{idVendor}=="0403"' in line
    assert 'ATTR{idProduct}=="6001"' in line
    assert 'MODE="0666"' in line
    assert 'TAG+="uaccess"' in line


def test_parse_and_serialize_run_command_and_touchpad_rule():
    line = (
        'ACTION=="add|change", SUBSYSTEM=="hidraw", ATTRS{idVendor}=="2c2f", '
        'ATTRS{name}=="*Touchpad*", MODE="0660", GROUP="input", '
        'RUN+="/usr/local/bin/thinkpad-x9-touchpad --device $devnode --resistance 45 --click-feedback 70"'
    )
    rule = UdevParser.parse_rule_line(line)
    assert rule.action == "add|change"
    assert rule.subsystem == "hidraw"
    assert rule.vendor_id == "2c2f"
    assert rule.vendor_key == "ATTRS{idVendor}"
    assert rule.get_extra_value("ATTRS{name}") == "*Touchpad*"
    assert rule.mode == "0660"
    assert rule.group == "input"
    assert rule.run_key == "RUN"
    assert rule.run_op == "+="
    assert rule.run_cmd == "/usr/local/bin/thinkpad-x9-touchpad --device $devnode --resistance 45 --click-feedback 70"

    serialized = rule.to_line()
    assert 'ATTRS{idVendor}=="2c2f"' in serialized
    assert 'ATTRS{name}=="*Touchpad*"' in serialized
    assert 'RUN+="/usr/local/bin/thinkpad-x9-touchpad --device $devnode --resistance 45 --click-feedback 70"' in serialized


def test_parse_driver_owner_and_systemd_wants():
    line = (
        'SUBSYSTEM=="usb", DRIVER=="usbhid", OWNER="alice", '
        'TAG+="systemd", ENV{SYSTEMD_WANTS}+="custom-hid-helper.service"'
    )
    rule = UdevParser.parse_rule_line(line)
    assert rule.driver == "usbhid"
    assert rule.owner == "alice"
    assert rule.systemd_wants == "custom-hid-helper.service"
    out = rule.to_line()
    assert 'DRIVER=="usbhid"' in out
    assert 'OWNER="alice"' in out
    assert 'TAG+="systemd"' in out
    assert 'ENV{SYSTEMD_WANTS}+="custom-hid-helper.service"' in out


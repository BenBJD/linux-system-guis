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

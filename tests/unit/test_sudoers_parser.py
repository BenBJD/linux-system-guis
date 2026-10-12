"""Unit tests for sudoers parser, drop-in filename validation, and visudo checks."""

from sudoers_gui.parser import SudoersParser, SudoersRule


def test_parse_group_rule():
    rule = SudoersParser.parse_line("%wheel ALL=(ALL:ALL) ALL")
    assert not rule.is_comment
    assert rule.is_group is True
    assert rule.entity == "wheel"
    assert rule.hosts == "ALL"
    assert rule.runas_user == "ALL"
    assert rule.runas_group == "ALL"
    assert rule.nopasswd is False
    assert rule.commands == "ALL"
    assert rule.to_line() == "%wheel ALL=(ALL:ALL) ALL"


def test_parse_user_nopasswd_rule():
    rule = SudoersParser.parse_line("alice ALL=(ALL) NOPASSWD: /usr/bin/systemctl restart nginx")
    assert not rule.is_comment
    assert rule.is_group is False
    assert rule.entity == "alice"
    assert rule.nopasswd is True
    assert rule.commands == "/usr/bin/systemctl restart nginx"
    assert rule.to_line() == "alice ALL=(ALL) NOPASSWD: /usr/bin/systemctl restart nginx"


def test_parse_comment_and_defaults():
    comment = SudoersParser.parse_line("# This is a comment")
    assert comment.is_comment is True
    assert comment.to_line() == "# This is a comment"

    defaults = SudoersParser.parse_line("Defaults env_reset")
    assert defaults.is_comment is True
    assert defaults.to_line() == "Defaults env_reset"


def test_dropin_filename_validation():
    # Valid filenames
    valid_names = ["10-wheel", "99-custom-admin", "developer_nopasswd", "admin"]
    for name in valid_names:
        is_val, _ = SudoersParser.is_valid_dropin_filename(name)
        assert is_val is True, f"Expected {name} to be valid"

    # Sudoers explicitly ignores files with dots or ending with ~
    invalid_cases = [
        ("99-admin.conf", "contains period"),
        ("rules~", "ends with tilde"),
        ("", "empty string"),
        ("bad name!", "special characters"),
    ]
    for name, reason in invalid_cases:
        is_val, msg = SudoersParser.is_valid_dropin_filename(name)
        assert is_val is False, f"Expected {name} to be invalid ({reason})"
        assert len(msg) > 0


def test_validate_with_visudo_valid():
    valid_content = "root ALL=(ALL) ALL\n%wheel ALL=(ALL) ALL\n"
    is_valid, msg = SudoersParser.validate_with_visudo(valid_content)
    # If visudo is installed, must be valid; if not installed, passes gracefully
    assert is_valid is True


def test_validate_with_visudo_syntax_error():
    import shutil
    if not shutil.which("visudo"):
        return  # Skip if visudo binary is not available in environment

    invalid_content = "THIS IS COMPLETELY INVALID SUDOERS SYNTAX !!!\n"
    is_valid, msg = SudoersParser.validate_with_visudo(invalid_content)
    assert is_valid is False
    assert len(msg) > 0

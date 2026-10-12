"""Unit tests for SafetyExecutionDialog and diff generator."""

from PyQt6.QtWidgets import QDialogButtonBox
from linux_gui_core.widgets.safety_dialog import SafetyExecutionDialog, generate_diff


def test_safety_dialog_apply_button_accepts(qapp):
    """Verify that clicking the 'Apply Changes (Requires Root)' button emits accepted."""
    dlg = SafetyExecutionDialog(
        title="Test Apply",
        target_path_or_command="systemctl restart test",
        safety_notes=["Note 1", "Note 2"],
    )
    btn_apply = dlg.btn_box.button(QDialogButtonBox.StandardButton.Ok)
    assert btn_apply is not None
    assert "Apply Changes" in btn_apply.text()

    accepted_fired = []
    dlg.accepted.connect(lambda: accepted_fired.append(True))
    btn_apply.click()

    assert len(accepted_fired) == 1


def test_safety_dialog_cancel_button_rejects(qapp):
    """Verify that clicking Cancel rejects the dialog."""
    dlg = SafetyExecutionDialog(
        title="Test Cancel",
        target_path_or_command="systemctl restart test",
    )
    btn_cancel = dlg.btn_box.button(QDialogButtonBox.StandardButton.Cancel)
    assert btn_cancel is not None

    rejected_fired = []
    dlg.rejected.connect(lambda: rejected_fired.append(True))
    btn_cancel.click()

    assert len(rejected_fired) == 1


def test_generate_diff_identical():
    """Verify identical text produces empty diff."""
    text = "line1\nline2\n"
    diff = generate_diff(text, text, "test.conf")
    assert diff == ""


def test_generate_diff_modifications():
    """Verify modifications generate unified diff with + and - markers."""
    orig = "quiet loglevel=3\n"
    mod = "quiet loglevel=3 nomodeset\n"
    diff = generate_diff(orig, mod, "grub")
    assert "-quiet loglevel=3" in diff
    assert "+quiet loglevel=3 nomodeset" in diff

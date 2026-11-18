"""Standardized rich educational tooltips and interactive hoverable tooltip popup."""

import re
from PyQt6.QtCore import QEvent, QObject, QPoint, QRect, Qt, QTimer, QUrl
from PyQt6.QtGui import QCursor, QDesktopServices, QGuiApplication
from PyQt6.QtWidgets import (
    QApplication,
    QFrame,
    QLabel,
    QToolTip,
    QVBoxLayout,
    QWidget,
)

from linux_gui_core.strings import tr
from linux_gui_core.widgets.preview_banner import open_man_page

# Badge colours per explicit severity level.
LEVEL_COLOURS: dict[str, str] = {
    "danger": "#f85149",
    "caution": "#d29922",
    "safe": "#3fb950",
    "info": "#58a6ff",
    "hardening": "#388bfd",
}

# Generic filler strings that should NOT be displayed as a "Security / Safety" row.
_GENERIC_FILLER_IMPACTS = {
    "safe",
    "standard",
    "optional",
    "safe match",
    "recommended",
    "recommended after changes",
    "safe / power saving",
    "safe / troubleshooting",
    "safe / performance",
    "safe / virtualization",
    "safe / hardware access",
    "safe / virtual input devices",
    "safe / stability fix for audio/serial interfaces",
    "safe / recommended",
}

_CAN_BE_BLANK_RE = re.compile(
    r"(?:<br>\s*)*<b>Can be blank:?</b>\.?\s*(.*)",
    re.IGNORECASE | re.DOTALL,
)
_CANNOT_BE_BLANK_RE = re.compile(
    r"(?:<br>\s*)*<b>Cannot be blank:?</b>\.?\s*(.*)",
    re.IGNORECASE | re.DOTALL,
)
_KERNEL_DEFAULT_RE = re.compile(
    r"(?:<br>\s*)+<b>Kernel Default:</b>\s*<code>([^<]+)</code>\.?",
    re.IGNORECASE,
)


def _guess_level(security_text: str) -> str:
    """Infer a severity level from English security/safety text."""
    impact = security_text.lower()
    if "danger" in impact or "critical" in impact or "lockout" in impact:
        return "danger"
    if "caution" in impact or "warning" in impact or "risk" in impact or "reset" in impact:
        return "caution"
    if "recommended" in impact or "safe" in impact:
        return "safe"
    return "info"


def _classify_legacy_impact(
    security_impact: str | None,
    can_be_blank: bool | None,
    blank_behavior: str | None,
    default_value: str | None,
    recommended_value: str | None,
    security: str | None,
) -> tuple[bool | None, str | None, str | None, str | None, str | None]:
    """Route legacy positional ``security_impact`` strings into structured fields
    (blankness, default_value, recommended_value, or security) while dropping arbitrary
    filler like 'Safe' or 'Standard'.
    """
    if not security_impact:
        return can_be_blank, blank_behavior, default_value, recommended_value, security

    raw = security_impact.strip()
    low = raw.lower()

    if low in _GENERIC_FILLER_IMPACTS:
        return can_be_blank, blank_behavior, default_value, recommended_value, security

    if low == "required":
        if can_be_blank is None:
            can_be_blank = False
        return can_be_blank, blank_behavior, default_value, recommended_value, security

    if low == "required directory" or low.startswith("target directory"):
        if can_be_blank is None:
            can_be_blank = False
        if not blank_behavior:
            blank_behavior = raw
        return can_be_blank, blank_behavior, default_value, recommended_value, security

    if low.startswith("standard:") or low.startswith("default:"):
        val = raw.split(":", 1)[1].strip()
        if default_value is None and val:
            default_value = val
        return can_be_blank, blank_behavior, default_value, recommended_value, security

    if low.startswith("recommended:") or low.startswith("recommended for") or low.startswith("safe / recommended for"):
        if recommended_value is None:
            cleaned = re.sub(r"^(?:safe\s*/\s*)?recommended:?\s*", "", raw, flags=re.IGNORECASE).strip()
            recommended_value = cleaned or raw
        return can_be_blank, blank_behavior, default_value, recommended_value, security

    if low.startswith("1 for root") or low.startswith("safer to use") or low.startswith("restricted paths"):
        if recommended_value is None:
            recommended_value = raw
        return can_be_blank, blank_behavior, default_value, recommended_value, security

    # Genuine security or safety notice
    if security is None:
        security = raw
    return can_be_blank, blank_behavior, default_value, recommended_value, security


def format_tooltip(
    title: str,
    directive: str = "",
    description: str = "",
    security_impact: str | None = None,
    example: str | None = None,
    level: str | None = None,
    man_page: str | None = None,
    *,
    can_be_blank: bool | None = None,
    blank_behavior: str | None = None,
    default_value: str | None = None,
    recommended_value: str | None = None,
    security: str | None = None,
) -> str:
    """Format an organized, structured HTML tooltip with optional, controllable sections:
    - Blank / Empty value rules (whether blank is allowed and what blank means)
    - Default value (when applicable)
    - Recommended value (when applicable)
    - Security / Safety note (only when genuinely relevant)
    - Example syntax (when applicable)
    - Clickable Man Page reference link that opens the Help & Man Pages window on that tab
    """
    app = QApplication.instance()
    if isinstance(app, QApplication):
        install_interactive_tooltips(app)

    clean_desc = description.strip()

    # Extract inline Kernel Default if present in description
    m_def = _KERNEL_DEFAULT_RE.search(clean_desc)
    if m_def:
        if default_value is None:
            default_value = m_def.group(1).strip()
        clean_desc = _KERNEL_DEFAULT_RE.sub("", clean_desc).strip()

    # Extract inline "Can be blank" / "Cannot be blank" from description into dedicated section
    m_can = _CAN_BE_BLANK_RE.search(clean_desc)
    if m_can:
        if can_be_blank is None:
            can_be_blank = True
        extracted = m_can.group(1).strip()
        if not blank_behavior and extracted:
            blank_behavior = extracted
        clean_desc = clean_desc[: m_can.start()].strip()
    else:
        m_cannot = _CANNOT_BE_BLANK_RE.search(clean_desc)
        if m_cannot:
            if can_be_blank is None:
                can_be_blank = False
            extracted = m_cannot.group(1).strip()
            if not blank_behavior and extracted:
                blank_behavior = extracted
            clean_desc = clean_desc[: m_cannot.start()].strip()

    # Route legacy positional security_impact into structured sections
    can_be_blank, blank_behavior, default_value, recommended_value, security = _classify_legacy_impact(
        security_impact,
        can_be_blank,
        blank_behavior,
        default_value,
        recommended_value,
        security,
    )

    parts: list[str] = [
        "<div style='max-width: 480px; min-width: 300px; line-height: 1.5; color: #f0f3f6; font-family: sans-serif;'>",
        f"<div style='margin-bottom: 5px;'><b style='font-size: 13.5px; color: #85abf2; letter-spacing: 0.1px;'>{title}</b></div>",
    ]

    if directive:
        parts.append(
            "<div style='margin-bottom: 7px;'>"
            "<code style='background-color: #12151c; border: 1px solid #283247; border-radius: 4px; "
            "padding: 2px 7px; color: #79c0ff; font-family: monospace; font-size: 11.5px; font-weight: 600;'>"
            f"{directive}</code></div>"
        )

    if clean_desc:
        parts.append(f"<div style='margin: 6px 0 8px 0; color: #c9d1d9; font-size: 12.5px; line-height: 1.5;'>{clean_desc}</div>")

    # 1. Structured Property / Requirements Box (Blank policy, Default, Recommended)
    has_spec = (can_be_blank is not None or blank_behavior or default_value or recommended_value)
    if has_spec:
        spec_rows: list[str] = []
        if can_be_blank is not None or blank_behavior:
            is_allowed = True if can_be_blank is None else can_be_blank
            badge_color = "#3fb950" if is_allowed else "#f85149"
            badge_bg = "rgba(63, 185, 80, 0.12)" if is_allowed else "rgba(248, 81, 73, 0.12)"
            badge_border = "#234d31" if is_allowed else "#5c2025"
            badge_text = tr("tooltip_blank_allowed") if is_allowed else tr("tooltip_blank_required")
            default_expl = (
                tr("tooltip_blank_allowed_default_desc")
                if is_allowed
                else tr("tooltip_blank_required_default_desc")
            )
            expl_text = blank_behavior or default_expl
            spec_rows.append(
                f"<div style='margin: 3px 0;'>"
                f"<span style='color: {badge_color}; background-color: {badge_bg}; border: 1px solid {badge_border}; "
                f"border-radius: 3px; padding: 1px 6px; font-weight: 600; font-size: 11px;'>{badge_text}</span> "
                f"<span style='color: #8b949e; font-size: 11.5px; margin-left: 4px;'>{expl_text}</span></div>"
            )

        if default_value:
            spec_rows.append(
                f"<div style='margin: 3px 0;'><b style='color: #8b949e;'>{tr('tooltip_default_label')}</b> "
                f"<code style='background-color: #1a1e26; border: 1px solid #2d3340; border-radius: 3px; "
                f"padding: 1px 5px; color: #f0f3f6; font-family: monospace;'>{default_value}</code></div>"
            )

        if recommended_value:
            spec_rows.append(
                f"<div style='margin: 3px 0;'><b style='color: #8b949e;'>{tr('tooltip_recommended_label')}</b> "
                f"<span style='color: #3fb950; font-weight: 600;'>{recommended_value}</span></div>"
            )

        parts.append(
            "<div style='background-color: #121418; border: 1px solid #262b36; border-radius: 5px; "
            "padding: 6px 9px; margin: 8px 0; font-size: 12px; line-height: 1.45;'>"
            + "".join(spec_rows)
            + "</div>"
        )

    # 2. Security & Safety Callout (GitHub-style alert box)
    if security:
        badge_color = LEVEL_COLOURS.get(level or _guess_level(security), LEVEL_COLOURS["caution"])
        callout_bg = (
            "#251e18" if badge_color == LEVEL_COLOURS["caution"]
            else ("#27181c" if badge_color == LEVEL_COLOURS["danger"]
            else ("#142218" if badge_color == LEVEL_COLOURS["safe"]
            else "#15202b"))
        )
        parts.append(
            f"<div style='margin: 8px 0; padding: 6px 10px; background-color: {callout_bg}; "
            f"border-left: 3px solid {badge_color}; border-radius: 4px; font-size: 12px; line-height: 1.45;'>"
            f"<div><b style='color: #8b949e;'>{tr('tooltip_security_label')}</b> "
            f"<span style='color: {badge_color}; font-weight: bold;'>{security}</span></div>"
            "</div>"
        )

    # 3. Example Code Box
    if example:
        parts.append(
            f"<div style='margin: 8px 0; padding: 6px 10px; background-color: #0f1115; "
            f"border: 1px solid #262b36; border-radius: 4px; font-size: 12px;'>"
            f"<div style='color: #8b949e; font-size: 11px; margin-bottom: 2px;'><b>{tr('tooltip_example_label')}</b></div>"
            f"<code style='color: #79c0ff; font-family: monospace; font-size: 11.5px;'>{example}</code>"
            "</div>"
        )

    # 4. Clickable Man Page Footer Link
    if man_page:
        link_label = tr("tooltip_man_link_text", man_page=man_page)
        parts.append(
            "<div style='margin-top: 8px; padding-top: 7px; border-top: 1px solid #282d38; font-size: 11.5px;'>"
            f"<b style='color: #8b949e;'>{tr('tooltip_man_label')}</b> "
            f"<a href='man:{man_page}' style='color: #58a6ff; text-decoration: underline; font-weight: 600;'>"
            f"{link_label}</a>"
            "</div>"
        )

    parts.append("</div>")
    return "".join(parts)


class InteractiveTooltipPopup(QFrame):
    """Custom floating tooltip window that stays open when the user moves the cursor
    onto the tooltip, allowing text selection and clicking `man:` links.
    """

    def __init__(self) -> None:
        super().__init__(
            None,
            Qt.WindowType.ToolTip
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.BypassWindowManagerHint,
        )
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setObjectName("interactiveTooltipPopup")
        self.setStyleSheet(
            """
            QFrame#interactiveTooltipPopup {
                background-color: #181b22;
                color: #f0f3f6;
                border: 1px solid #3d4352;
                border-radius: 8px;
                padding: 10px 12px;
            }
            QLabel {
                border: none;
                background: transparent;
                color: #f0f3f6;
            }
            """
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(0)

        self.label = QLabel()
        self.label.setWordWrap(True)
        self.label.setTextFormat(Qt.TextFormat.RichText)
        self.label.setTextInteractionFlags(
            Qt.TextInteractionFlag.LinksAccessibleByMouse
            | Qt.TextInteractionFlag.TextSelectableByMouse
        )
        self.label.linkActivated.connect(self._on_link_activated)
        layout.addWidget(self.label)

        self._source_widget: QWidget | None = None
        self._outside_ticks: int = 0
        self._hover_timer = QTimer(self)
        self._hover_timer.setInterval(90)
        self._hover_timer.timeout.connect(self._check_hover)

    def show_for_widget(self, widget: QWidget, global_pos: QPoint) -> None:
        tip = widget.toolTip()
        if not tip:
            self.hide_tooltip()
            return

        self._source_widget = widget
        self._outside_ticks = 0
        self.label.setText(tip)
        self.label.adjustSize()
        self.adjustSize()

        # Position slightly below/right of cursor, clamped to screen bounds
        target_pos = QPoint(global_pos.x() + 10, global_pos.y() + 16)
        screen = QGuiApplication.screenAt(global_pos) or QGuiApplication.primaryScreen()
        if screen is not None:
            avail = screen.availableGeometry()
            if target_pos.x() + self.width() > avail.right() - 8:
                target_pos.setX(max(avail.left() + 8, avail.right() - self.width() - 8))
            if target_pos.y() + self.height() > avail.bottom() - 8:
                target_pos.setY(max(avail.top() + 8, global_pos.y() - self.height() - 10))

        self.move(target_pos)
        self.show()
        self.raise_()
        if not self._hover_timer.isActive():
            self._hover_timer.start()

    def hide_tooltip(self) -> None:
        self._hover_timer.stop()
        self._source_widget = None
        self._outside_ticks = 0
        if self.isVisible():
            self.hide()

    def _check_hover(self) -> None:
        if not self.isVisible():
            self._hover_timer.stop()
            return

        src = self._source_widget
        if src is None or not src.isVisible():
            self.hide_tooltip()
            return

        cursor_pos = QCursor.pos()

        # Expand popup rect by 18px margin so moving diagonally from widget to popup never drops
        popup_rect = QRect(self.mapToGlobal(QPoint(0, 0)), self.size()).adjusted(-18, -18, 18, 18)
        src_rect = QRect(src.mapToGlobal(QPoint(0, 0)), src.size()).adjusted(-6, -6, 6, 6)

        if popup_rect.contains(cursor_pos) or src_rect.contains(cursor_pos):
            self._outside_ticks = 0
        else:
            self._outside_ticks += 1
            if self._outside_ticks >= 3:
                self.hide_tooltip()

    def _on_link_activated(self, href: str) -> None:
        src = self._source_widget
        host_win = src.window() if isinstance(src, QWidget) else None
        self.hide_tooltip()
        if href.startswith("man:"):
            open_man_page(man_ref=href, parent=host_win)
        elif href.startswith("http://") or href.startswith("https://"):
            QDesktopServices.openUrl(QUrl(href))


class InteractiveTooltipManager(QObject):
    """Application-wide event filter replacing ephemeral QToolTips with
    hover-persistent InteractiveTooltipPopup instances.
    """

    def __init__(self, app: QApplication) -> None:
        super().__init__(app)
        self._popup: InteractiveTooltipPopup | None = None

    def _get_popup(self) -> InteractiveTooltipPopup:
        if self._popup is None:
            self._popup = InteractiveTooltipPopup()
        return self._popup

    def eventFilter(self, watched: QObject | None, event: QEvent | None) -> bool:
        if event is None:
            return False
        etype = event.type()

        if etype == QEvent.Type.ToolTip and isinstance(watched, QWidget):
            tip = watched.toolTip()
            if tip and ("<div" in tip or "<b" in tip or "man:" in tip):
                QToolTip.hideText()
                global_pos = getattr(event, "globalPos", lambda: QCursor.pos())()
                self._get_popup().show_for_widget(watched, global_pos)
                return True

        elif etype in (QEvent.Type.ApplicationDeactivate, QEvent.Type.WindowDeactivate):
            if self._popup and self._popup.isVisible():
                self._popup.hide_tooltip()

        elif etype == QEvent.Type.KeyPress:
            if self._popup and self._popup.isVisible():
                key = getattr(event, "key", lambda: 0)()
                if key == Qt.Key.Key_Escape:
                    self._popup.hide_tooltip()

        elif etype == QEvent.Type.MouseButtonPress and isinstance(watched, QWidget):
            if self._popup and self._popup.isVisible():
                if watched is not self._popup and not self._popup.isAncestorOf(watched):
                    self._popup.hide_tooltip()

        return False


def install_interactive_tooltips(app: QApplication) -> InteractiveTooltipManager:
    """Install the global InteractiveTooltipManager on ``app`` (idempotent)."""
    existing = getattr(app, "_interactive_tooltip_manager", None)
    if isinstance(existing, InteractiveTooltipManager):
        return existing
    mgr = InteractiveTooltipManager(app)
    app.installEventFilter(mgr)
    setattr(app, "_interactive_tooltip_manager", mgr)
    return mgr

"""Standardized rich educational tooltips for Linux options and permissions."""

from linux_gui_core.strings import tr

# Badge colours per explicit severity level.
LEVEL_COLOURS: dict[str, str] = {
    "danger": "#e5534b",
    "caution": "#e3b341",
    "safe": "#57ab5a",
    "info": "#6899e6",
}


def _guess_level(security_impact: str) -> str:
    """Infer a severity level from English impact text.

    Only used when no explicit ``level`` is passed. Translated impact text will not
    match these keywords, so localised callers should always pass ``level``.
    """
    impact = security_impact.lower()
    if "danger" in impact or "critical" in impact:
        return "danger"
    if "caution" in impact or "warning" in impact:
        return "caution"
    if "recommended" in impact or "safe" in impact:
        return "safe"
    return "info"


def format_tooltip(
    title: str,
    directive: str,
    description: str,
    security_impact: str | None = None,
    example: str | None = None,
    level: str | None = None,
) -> str:
    """Format an informative, nicely styled HTML tooltip explaining an option,
    its exact command/file syntax, and system impact.

    ``level`` is one of ``"danger"``, ``"caution"``, ``"safe"`` or ``"info"`` and controls
    the badge colour independently of the (translatable) ``security_impact`` text.
    """
    if security_impact is None:
        security_impact = tr("tooltip_default_impact")
    badge_color = LEVEL_COLOURS.get(level or _guess_level(security_impact), LEVEL_COLOURS["info"])

    html = f"""
    <div style='max-width: 320px; line-height: 1.4;'>
        <b style='font-size: 13px; color: #6899e6;'>{title}</b><br>
        <span style='font-family: monospace; background: #2b2d33; color: #e3e5e8; padding: 2px 4px; border-radius: 3px;'>
            {directive}
        </span>
        <p style='margin: 6px 0 4px 0; color: #e3e5e8;'>{description}</p>
        <div style='font-size: 11px; margin-top: 4px;'>
            <b>{tr("tooltip_security_label")}</b>
            <span style='color: {badge_color}; font-weight: bold;'> {security_impact}</span>
        </div>
    """
    if example:
        html += f"""
        <div style='font-size: 11px; color: #9498a1; margin-top: 4px;'>
            <b>{tr("tooltip_example_label")}</b> <i>{example}</i>
        </div>
        """
    html += "</div>"
    return html.strip()

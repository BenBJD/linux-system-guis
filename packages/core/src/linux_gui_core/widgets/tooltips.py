"""Standardized rich educational tooltips for Linux options and permissions."""

def format_tooltip(
    title: str,
    directive: str,
    description: str,
    security_impact: str = "Standard",
    example: str | None = None,
) -> str:
    """Format an informative, nicely styled HTML tooltip explaining an option,

    its exact command/file syntax, and system impact.
    """
    badge_color = "#89b4fa"
    if "danger" in security_impact.lower() or "critical" in security_impact.lower():
        badge_color = "#f38ba8"
    elif "caution" in security_impact.lower() or "warning" in security_impact.lower():
        badge_color = "#f9e2af"
    elif "recommended" in security_impact.lower() or "safe" in security_impact.lower():
        badge_color = "#a6e3a1"

    html = f"""
    <div style='max-width: 320px; line-height: 1.4;'>
        <b style='font-size: 13px; color: #89b4fa;'>{title}</b><br>
        <span style='font-family: monospace; background: #313244; color: #cdd6f4; padding: 2px 4px; border-radius: 3px;'>
            {directive}
        </span>
        <p style='margin: 6px 0 4px 0; color: #cdd6f4;'>{description}</p>
        <div style='font-size: 11px; margin-top: 4px;'>
            <b>Security / Safety:</b>
            <span style='color: {badge_color}; font-weight: bold;'> {security_impact}</span>
        </div>
    """
    if example:
        html += f"""
        <div style='font-size: 11px; color: #a6adc8; margin-top: 4px;'>
            <b>Example:</b> <i>{example}</i>
        </div>
        """
    html += "</div>"
    return html.strip()

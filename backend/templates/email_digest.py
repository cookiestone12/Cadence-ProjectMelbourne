from datetime import datetime


def generate_digest_html(user_name, grouped_items, summary_stats, platform_url=""):
    priority_colors = {
        "critical": "#C47068",
        "high": "#C4956B",
        "medium": "#5B8A72",
        "low": "#7A8580",
    }

    priority_labels = {
        "critical": "Critical",
        "high": "High",
        "medium": "Medium",
        "low": "Low",
    }

    def truncate(text, length=120):
        if not text:
            return ""
        return text[:length] + "..." if len(text) > length else text

    def format_deadline(deadline):
        if not deadline:
            return ""
        if isinstance(deadline, str):
            try:
                deadline = datetime.fromisoformat(deadline)
            except (ValueError, TypeError):
                return deadline
        now = datetime.utcnow()
        is_overdue = deadline < now
        formatted = deadline.strftime("%b %d, %Y")
        if is_overdue:
            return f'<span style="color:#C47068;font-weight:bold;">{formatted} (Overdue)</span>'
        return f'<span style="color:#3D4A44;">{formatted}</span>'

    def render_item(item, color):
        deadline_html = format_deadline(item.get("deadline"))
        deadline_row = ""
        if deadline_html:
            deadline_row = f'''
                <tr>
                    <td style="padding:4px 0 0 0;font-size:12px;font-family:Arial,sans-serif;">
                        &#128197; {deadline_html}
                    </td>
                </tr>'''

        entity_badge = ""
        entity_type = item.get("entity_type", "")
        entity_label = item.get("entity_label", "")
        if entity_type:
            badge_text = entity_label if entity_label else entity_type
            entity_badge = f'''
                <span style="display:inline-block;background:#F5F7F4;color:#5B8A72;font-size:11px;padding:2px 8px;border-radius:10px;font-family:Arial,sans-serif;margin-right:6px;">
                    {badge_text}
                </span>'''

        action_badge = ""
        action_type = item.get("action_type", "")
        if action_type:
            action_badge = f'''
                <span style="display:inline-block;background:#F5F7F4;color:#7A8580;font-size:11px;padding:2px 8px;border-radius:10px;font-family:Arial,sans-serif;">
                    {action_type}
                </span>'''

        return f'''
        <tr>
            <td style="padding:8px 0;">
                <table width="100%" cellpadding="0" cellspacing="0" border="0" style="border-left:4px solid {color};background:#ffffff;border-radius:6px;">
                    <tr>
                        <td style="padding:14px 16px;">
                            <table width="100%" cellpadding="0" cellspacing="0" border="0">
                                <tr>
                                    <td style="font-size:15px;font-weight:bold;color:#3D4A44;font-family:Arial,sans-serif;padding-bottom:4px;">
                                        {item.get("title", "")}
                                    </td>
                                </tr>
                                <tr>
                                    <td style="font-size:13px;color:#7A8580;font-family:Arial,sans-serif;padding-bottom:6px;line-height:1.4;">
                                        {truncate(item.get("description", ""))}
                                    </td>
                                </tr>
                                <tr>
                                    <td style="padding:4px 0 0 0;">
                                        {entity_badge}{action_badge}
                                    </td>
                                </tr>{deadline_row}
                            </table>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>'''

    def render_priority_group(priority_key, items):
        if not items:
            return ""
        color = priority_colors.get(priority_key, "#7A8580")
        label = priority_labels.get(priority_key, priority_key.title())
        items_html = "".join(render_item(item, color) for item in items)
        return f'''
        <tr>
            <td style="padding:20px 0 6px 0;">
                <table width="100%" cellpadding="0" cellspacing="0" border="0">
                    <tr>
                        <td style="font-size:14px;font-weight:bold;color:{color};font-family:Arial,sans-serif;text-transform:uppercase;letter-spacing:1px;padding-bottom:8px;border-bottom:2px solid {color};">
                            &#9679; {label} Priority ({len(items)})
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
        {items_html}'''

    total = summary_stats.get("total_items", 0)
    overdue = summary_stats.get("overdue_count", 0)
    critical = summary_stats.get("critical_count", 0)
    high = summary_stats.get("high_count", 0)

    overdue_color = "#C47068" if overdue > 0 else "#7A8580"

    summary_html = f'''
    <tr>
        <td style="padding:0 0 10px 0;">
            <table width="100%" cellpadding="0" cellspacing="0" border="0" style="background:#ffffff;border-radius:8px;">
                <tr>
                    <td style="padding:20px;">
                        <table width="100%" cellpadding="0" cellspacing="0" border="0">
                            <tr>
                                <td align="center" width="25%" style="padding:8px;">
                                    <table cellpadding="0" cellspacing="0" border="0">
                                        <tr>
                                            <td align="center" style="font-size:28px;font-weight:bold;color:#5B8A72;font-family:Arial,sans-serif;">
                                                {total}
                                            </td>
                                        </tr>
                                        <tr>
                                            <td align="center" style="font-size:11px;color:#7A8580;font-family:Arial,sans-serif;text-transform:uppercase;letter-spacing:0.5px;">
                                                Total Items
                                            </td>
                                        </tr>
                                    </table>
                                </td>
                                <td align="center" width="25%" style="padding:8px;">
                                    <table cellpadding="0" cellspacing="0" border="0">
                                        <tr>
                                            <td align="center" style="font-size:28px;font-weight:bold;color:{overdue_color};font-family:Arial,sans-serif;">
                                                {overdue}
                                            </td>
                                        </tr>
                                        <tr>
                                            <td align="center" style="font-size:11px;color:#7A8580;font-family:Arial,sans-serif;text-transform:uppercase;letter-spacing:0.5px;">
                                                Overdue
                                            </td>
                                        </tr>
                                    </table>
                                </td>
                                <td align="center" width="25%" style="padding:8px;">
                                    <table cellpadding="0" cellspacing="0" border="0">
                                        <tr>
                                            <td align="center" style="font-size:28px;font-weight:bold;color:#C47068;font-family:Arial,sans-serif;">
                                                {critical}
                                            </td>
                                        </tr>
                                        <tr>
                                            <td align="center" style="font-size:11px;color:#7A8580;font-family:Arial,sans-serif;text-transform:uppercase;letter-spacing:0.5px;">
                                                Critical
                                            </td>
                                        </tr>
                                    </table>
                                </td>
                                <td align="center" width="25%" style="padding:8px;">
                                    <table cellpadding="0" cellspacing="0" border="0">
                                        <tr>
                                            <td align="center" style="font-size:28px;font-weight:bold;color:#C4956B;font-family:Arial,sans-serif;">
                                                {high}
                                            </td>
                                        </tr>
                                        <tr>
                                            <td align="center" style="font-size:11px;color:#7A8580;font-family:Arial,sans-serif;text-transform:uppercase;letter-spacing:0.5px;">
                                                High
                                            </td>
                                        </tr>
                                    </table>
                                </td>
                            </tr>
                        </table>
                    </td>
                </tr>
            </table>
        </td>
    </tr>'''

    groups_html = ""
    for priority in ["critical", "high", "medium", "low"]:
        items = grouped_items.get(priority, [])
        groups_html += render_priority_group(priority, items)

    view_link = ""
    if platform_url:
        view_link = f'''
    <tr>
        <td align="center" style="padding:24px 0 10px 0;">
            <table cellpadding="0" cellspacing="0" border="0">
                <tr>
                    <td align="center" style="background:#5B8A72;border-radius:6px;">
                        <a href="{platform_url}/actions" target="_blank" style="display:inline-block;padding:12px 32px;color:#ffffff;font-size:14px;font-weight:bold;font-family:Arial,sans-serif;text-decoration:none;border-radius:6px;">
                            View in Platform &rarr;
                        </a>
                    </td>
                </tr>
            </table>
        </td>
    </tr>'''

    html = f'''<!DOCTYPE html>
<html lang="en" xmlns="http://www.w3.org/1999/xhtml">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <title>Rythm - Action Items Digest</title>
    <!--[if mso]>
    <style type="text/css">
        table {{border-collapse:collapse;border-spacing:0;margin:0;padding:0;}}
        div, td {{padding:0;}}
    </style>
    <![endif]-->
    <style type="text/css">
        @media only screen and (max-width: 620px) {{
            .outer-table {{
                width: 100% !important;
            }}
            .inner-pad {{
                padding: 16px !important;
            }}
            td[class="stat-cell"] {{
                display: block !important;
                width: 50% !important;
                box-sizing: border-box !important;
                float: left !important;
            }}
        }}
    </style>
</head>
<body style="margin:0;padding:0;background-color:#F5F7F4;-webkit-text-size-adjust:100%;-ms-text-size-adjust:100%;">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color:#F5F7F4;">
        <tr>
            <td align="center" style="padding:20px 10px;">
                <table role="presentation" class="outer-table" width="600" cellpadding="0" cellspacing="0" border="0" style="max-width:600px;width:100%;">
                    <tr>
                        <td align="center" style="padding:30px 0 20px 0;">
                            <table cellpadding="0" cellspacing="0" border="0">
                                <tr>
                                    <td align="center" style="font-size:32px;font-weight:bold;color:#5B8A72;font-family:Georgia,'Times New Roman',serif;letter-spacing:2px;">
                                        Rythm
                                    </td>
                                </tr>
                                <tr>
                                    <td align="center" style="font-size:14px;color:#7A8580;font-family:Arial,sans-serif;padding-top:6px;letter-spacing:0.5px;">
                                        Action Items Digest
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>

                    <tr>
                        <td class="inner-pad" style="padding:0 0 16px 0;">
                            <table width="100%" cellpadding="0" cellspacing="0" border="0" style="background:#5B8A72;border-radius:8px 8px 0 0;">
                                <tr>
                                    <td style="padding:20px 24px;font-size:18px;color:#ffffff;font-family:Arial,sans-serif;">
                                        Hi {user_name},
                                    </td>
                                </tr>
                                <tr>
                                    <td style="padding:0 24px 20px 24px;font-size:14px;color:#e8f0ec;font-family:Arial,sans-serif;line-height:1.5;">
                                        Here&#39;s your latest action items summary. Stay on top of your priorities.
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>

                    {summary_html}

                    <tr>
                        <td class="inner-pad" style="padding:0;">
                            <table width="100%" cellpadding="0" cellspacing="0" border="0">
                                {groups_html}
                            </table>
                        </td>
                    </tr>

                    {view_link}

                    <tr>
                        <td align="center" style="padding:30px 20px 10px 20px;">
                            <table width="100%" cellpadding="0" cellspacing="0" border="0" style="border-top:1px solid #d4ddd8;">
                                <tr>
                                    <td align="center" style="padding:20px 0 6px 0;font-size:12px;color:#7A8580;font-family:Arial,sans-serif;line-height:1.5;">
                                        You received this because you have email digest enabled in Rythm settings.
                                    </td>
                                </tr>
                                <tr>
                                    <td align="center" style="padding:0 0 20px 0;font-size:12px;color:#7A8580;font-family:Arial,sans-serif;">
                                        To stop receiving these emails, update your notification preferences in Settings.
                                    </td>
                                </tr>
                                <tr>
                                    <td align="center" style="padding:0 0 10px 0;font-size:11px;color:#a8b2ad;font-family:Arial,sans-serif;">
                                        &copy; {datetime.utcnow().year} Rythm. All rights reserved.
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>'''

    return html

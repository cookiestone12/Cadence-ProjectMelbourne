from datetime import datetime


SAGE_GREEN = "#5B8A72"
SAGE_GREEN_LIGHT = "#e8f0ec"
SAGE_GREEN_BG = "#F5F7F4"
TEXT_DARK = "#3D4A44"
TEXT_MUTED = "#7A8580"
TEXT_FAINT = "#a8b2ad"
BORDER_COLOR = "#d4ddd8"
WHITE = "#ffffff"

LOGO_URL = "https://cadence-catalog-intelligence.replit.app/cadence-logo.png"
PLATFORM_NAME = "Cadence"


def wrap_email(content_html: str, subject: str = "", preheader: str = "", platform_url: str = "") -> str:
    year = datetime.utcnow().year

    preheader_html = ""
    if preheader:
        preheader_html = f'''<div style="display:none;font-size:1px;color:#F5F7F4;line-height:1px;max-height:0px;max-width:0px;opacity:0;overflow:hidden;">{preheader}</div>'''

    return f'''<!DOCTYPE html>
<html lang="en" xmlns="http://www.w3.org/1999/xhtml">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <title>{subject or PLATFORM_NAME}</title>
    <!--[if mso]>
    <style type="text/css">
        table {{border-collapse:collapse;border-spacing:0;margin:0;padding:0;}}
        div, td {{padding:0;}}
    </style>
    <![endif]-->
    <style type="text/css">
        @media only screen and (max-width: 620px) {{
            .outer-table {{ width: 100% !important; }}
            .inner-pad {{ padding: 16px !important; }}
        }}
    </style>
</head>
<body style="margin:0;padding:0;background-color:{SAGE_GREEN_BG};-webkit-text-size-adjust:100%;-ms-text-size-adjust:100%;">
    {preheader_html}
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color:{SAGE_GREEN_BG};">
        <tr>
            <td align="center" style="padding:20px 10px;">
                <table role="presentation" class="outer-table" width="600" cellpadding="0" cellspacing="0" border="0" style="max-width:600px;width:100%;">

                    <tr>
                        <td align="center" style="padding:30px 0 20px 0;">
                            <img src="{LOGO_URL}" alt="{PLATFORM_NAME}" style="height:50px;display:block;margin:0 auto;" />
                        </td>
                    </tr>

                    <tr>
                        <td class="inner-pad" style="padding:0;">
                            <table width="100%" cellpadding="0" cellspacing="0" border="0" style="background:{WHITE};border-radius:8px;">
                                <tr>
                                    <td style="padding:32px 28px;">
                                        {content_html}
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>

                    <tr>
                        <td align="center" style="padding:30px 20px 10px 20px;">
                            <table width="100%" cellpadding="0" cellspacing="0" border="0" style="border-top:1px solid {BORDER_COLOR};">
                                <tr>
                                    <td align="center" style="padding:20px 0 0 0;">
                                        <img src="{LOGO_URL}" alt="{PLATFORM_NAME}" style="height:30px;display:block;margin:0 auto;" />
                                    </td>
                                </tr>
                                <tr>
                                    <td align="center" style="padding:12px 0 6px 0;font-size:12px;color:{TEXT_MUTED};font-family:Arial,sans-serif;line-height:1.5;">
                                        Sent by {PLATFORM_NAME} &mdash; Music Catalog Intelligence
                                    </td>
                                </tr>
                                <tr>
                                    <td align="center" style="padding:0 0 10px 0;font-size:11px;color:{TEXT_FAINT};font-family:Arial,sans-serif;">
                                        &copy; {year} {PLATFORM_NAME}. All rights reserved.
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


def heading(text: str) -> str:
    return f'<h1 style="margin:0 0 16px 0;font-size:22px;font-weight:bold;color:{TEXT_DARK};font-family:Arial,sans-serif;">{text}</h1>'


def subheading(text: str) -> str:
    return f'<h2 style="margin:0 0 12px 0;font-size:16px;font-weight:bold;color:{TEXT_DARK};font-family:Arial,sans-serif;">{text}</h2>'


def paragraph(text: str) -> str:
    return f'<p style="margin:0 0 14px 0;font-size:14px;color:{TEXT_DARK};font-family:Arial,sans-serif;line-height:1.6;">{text}</p>'


def muted_text(text: str) -> str:
    return f'<p style="margin:0 0 14px 0;font-size:13px;color:{TEXT_MUTED};font-family:Arial,sans-serif;line-height:1.5;">{text}</p>'


def button(label: str, url: str) -> str:
    return f'''<table cellpadding="0" cellspacing="0" border="0" style="margin:20px 0;">
    <tr>
        <td align="center" style="background:{SAGE_GREEN};border-radius:6px;">
            <a href="{url}" target="_blank" style="display:inline-block;padding:12px 32px;color:{WHITE};font-size:14px;font-weight:bold;font-family:Arial,sans-serif;text-decoration:none;border-radius:6px;">
                {label}
            </a>
        </td>
    </tr>
</table>'''


def divider() -> str:
    return f'<hr style="border:none;border-top:1px solid {BORDER_COLOR};margin:20px 0;" />'


def badge(text: str, color: str = SAGE_GREEN) -> str:
    return f'<span style="display:inline-block;background:{SAGE_GREEN_BG};color:{color};font-size:11px;padding:3px 10px;border-radius:12px;font-family:Arial,sans-serif;margin-right:4px;">{text}</span>'


def key_value_row(label: str, value: str) -> str:
    return f'''<tr>
    <td style="padding:6px 0;font-size:13px;color:{TEXT_MUTED};font-family:Arial,sans-serif;width:140px;vertical-align:top;">{label}</td>
    <td style="padding:6px 0;font-size:13px;color:{TEXT_DARK};font-family:Arial,sans-serif;vertical-align:top;">{value}</td>
</tr>'''


def key_value_table(rows: list) -> str:
    rows_html = "".join(key_value_row(r[0], r[1]) for r in rows)
    return f'<table width="100%" cellpadding="0" cellspacing="0" border="0" style="margin:12px 0;">{rows_html}</table>'

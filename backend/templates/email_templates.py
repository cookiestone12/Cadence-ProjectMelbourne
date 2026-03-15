from datetime import datetime
from typing import Optional, List, Dict, Any

from backend.templates.email_base import (
    wrap_email,
    heading,
    subheading,
    paragraph,
    muted_text,
    button,
    divider,
    badge,
    key_value_table,
    SAGE_GREEN,
    TEXT_DARK,
    TEXT_MUTED,
    SAGE_GREEN_BG,
    SAGE_GREEN_LIGHT,
    WHITE,
)


def welcome_invite(
    recipient_name: str,
    org_name: str,
    inviter_name: str = "",
    platform_url: str = "",
) -> str:
    invited_by = f" by {inviter_name}" if inviter_name else ""
    content = heading(f"Welcome to Cadence, {recipient_name}!")
    content += paragraph(
        f"You&#39;ve been invited{invited_by} to join <strong>{org_name}</strong> on Cadence &mdash; "
        "the music catalog intelligence platform built for publishers, labels, and managers."
    )
    content += divider()
    content += subheading("What&#39;s Coming")
    content += paragraph(
        "Cadence gives you a centralized workspace for catalog management, royalty tracking, "
        "contract administration, and creative collaboration &mdash; all in one place."
    )
    content += paragraph(
        "&#127925; <strong>Catalog Intelligence</strong> &mdash; Track every song, split, and registration<br>"
        "&#128200; <strong>Royalty Analytics</strong> &mdash; Real-time earnings and forecasting<br>"
        "&#128221; <strong>Contract Management</strong> &mdash; Never miss a deadline or renewal<br>"
        "&#127912; <strong>Creative Tools</strong> &mdash; Brief builder, placement tracking, and more"
    )
    if platform_url:
        content += button("Get Started &rarr;", platform_url)
    else:
        content += paragraph("We&#39;ll notify you when your account is ready to go.")
    content += muted_text("If you didn&#39;t expect this invitation, you can safely ignore this email.")
    return wrap_email(content, subject="Welcome to Cadence", preheader=f"You've been invited to {org_name} on Cadence", platform_url=platform_url)


def registration_report(
    recipient_name: str,
    org_name: str,
    report_date: str,
    total_works: int = 0,
    registered: int = 0,
    pending: int = 0,
    gaps: int = 0,
    works_summary: Optional[List[Dict[str, Any]]] = None,
    platform_url: str = "",
) -> str:
    content = heading("Bulk Registration Report")
    content += paragraph(f"Hi {recipient_name}, here&#39;s the registration status report for <strong>{org_name}</strong>.")
    content += muted_text(f"Report generated: {report_date}")

    pct = round((registered / total_works * 100) if total_works > 0 else 0)
    stats_html = f'''<table width="100%" cellpadding="0" cellspacing="0" border="0" style="margin:16px 0;">
    <tr>
        <td align="center" width="25%" style="padding:12px 4px;">
            <div style="font-size:28px;font-weight:bold;color:{SAGE_GREEN};font-family:Arial,sans-serif;">{total_works}</div>
            <div style="font-size:11px;color:{TEXT_MUTED};font-family:Arial,sans-serif;text-transform:uppercase;">Total Works</div>
        </td>
        <td align="center" width="25%" style="padding:12px 4px;">
            <div style="font-size:28px;font-weight:bold;color:{SAGE_GREEN};font-family:Arial,sans-serif;">{registered}</div>
            <div style="font-size:11px;color:{TEXT_MUTED};font-family:Arial,sans-serif;text-transform:uppercase;">Registered</div>
        </td>
        <td align="center" width="25%" style="padding:12px 4px;">
            <div style="font-size:28px;font-weight:bold;color:#C4956B;font-family:Arial,sans-serif;">{pending}</div>
            <div style="font-size:11px;color:{TEXT_MUTED};font-family:Arial,sans-serif;text-transform:uppercase;">Pending</div>
        </td>
        <td align="center" width="25%" style="padding:12px 4px;">
            <div style="font-size:28px;font-weight:bold;color:#C47068;font-family:Arial,sans-serif;">{gaps}</div>
            <div style="font-size:11px;color:{TEXT_MUTED};font-family:Arial,sans-serif;text-transform:uppercase;">Gaps</div>
        </td>
    </tr>
</table>'''
    content += stats_html

    content += paragraph(f"Overall registration coverage: <strong>{pct}%</strong>")

    if works_summary:
        content += divider()
        content += subheading("Works Detail")
        for w in works_summary[:20]:
            status_color = SAGE_GREEN if w.get("status") == "registered" else "#C4956B"
            content += f'''<div style="padding:8px 0;border-bottom:1px solid #eee;font-family:Arial,sans-serif;">
                <span style="font-size:14px;color:{TEXT_DARK};font-weight:bold;">{w.get("title", "Untitled")}</span>
                <span style="float:right;">{badge(w.get("status", "unknown"), status_color)}</span>
            </div>'''

    if platform_url:
        content += button("View Full Report &rarr;", f"{platform_url}/registration-reports")

    return wrap_email(content, subject=f"Bulk Registration Report - {org_name}", preheader=f"{registered}/{total_works} works registered", platform_url=platform_url)


def share_contact_card(
    sender_name: str,
    contact_name: str,
    contact_role: str = "",
    contact_email: str = "",
    contact_phone: str = "",
    contact_company: str = "",
    message: str = "",
    platform_url: str = "",
) -> str:
    content = heading("Shared Contact Card")
    content += paragraph(f"<strong>{sender_name}</strong> shared a contact with you from Cadence.")

    if message:
        content += f'''<div style="background:{SAGE_GREEN_BG};border-left:4px solid {SAGE_GREEN};padding:12px 16px;margin:16px 0;border-radius:4px;">
            <p style="margin:0;font-size:14px;color:{TEXT_DARK};font-family:Arial,sans-serif;font-style:italic;">"{message}"</p>
        </div>'''

    content += divider()

    rows = [("Name", f"<strong>{contact_name}</strong>")]
    if contact_role:
        rows.append(("Role", contact_role))
    if contact_company:
        rows.append(("Company", contact_company))
    if contact_email:
        rows.append(("Email", f'<a href="mailto:{contact_email}" style="color:{SAGE_GREEN};">{contact_email}</a>'))
    if contact_phone:
        rows.append(("Phone", contact_phone))

    content += key_value_table(rows)

    if platform_url:
        content += button("View in Cadence &rarr;", f"{platform_url}/creative-directory")

    return wrap_email(content, subject=f"Contact Shared: {contact_name}", preheader=f"{sender_name} shared {contact_name}'s contact card", platform_url=platform_url)


def notification_alert(
    recipient_name: str,
    notification_title: str,
    notification_body: str,
    notification_type: str = "",
    entity_type: str = "",
    entity_label: str = "",
    priority: str = "medium",
    platform_url: str = "",
    action_url: str = "",
) -> str:
    priority_colors = {
        "critical": "#C47068",
        "high": "#C4956B",
        "medium": SAGE_GREEN,
        "low": TEXT_MUTED,
    }
    border_color = priority_colors.get(priority, SAGE_GREEN)

    content = heading("New Notification")
    content += paragraph(f"Hi {recipient_name},")

    badges_html = ""
    if priority:
        badges_html += badge(priority.title(), border_color)
    if notification_type:
        badges_html += badge(notification_type.replace("_", " ").title())
    if entity_type:
        label = entity_label or entity_type
        badges_html += badge(label)

    content += f'''<div style="border-left:4px solid {border_color};background:{SAGE_GREEN_BG};border-radius:4px;padding:16px;margin:16px 0;">
        <div style="font-size:16px;font-weight:bold;color:{TEXT_DARK};font-family:Arial,sans-serif;margin-bottom:8px;">{notification_title}</div>
        <div style="font-size:14px;color:{TEXT_DARK};font-family:Arial,sans-serif;line-height:1.5;margin-bottom:10px;">{notification_body}</div>
        <div>{badges_html}</div>
    </div>'''

    link = action_url or (f"{platform_url}/actions" if platform_url else "")
    if link:
        content += button("View Details &rarr;", link)

    return wrap_email(content, subject=notification_title, preheader=notification_body[:100], platform_url=platform_url)


def release_distribution(
    recipient_name: str,
    release_title: str,
    artist_name: str,
    release_date: str = "",
    upc: str = "",
    label: str = "",
    track_count: int = 0,
    tracks: Optional[List[Dict[str, str]]] = None,
    notes: str = "",
    sender_name: str = "",
    platform_url: str = "",
) -> str:
    content = heading("Release Delivery")
    if sender_name:
        content += paragraph(f"<strong>{sender_name}</strong> has sent you release delivery information.")
    content += paragraph(f"Hi {recipient_name}, please find details for the upcoming release below.")

    content += divider()

    rows = [
        ("Release", f"<strong>{release_title}</strong>"),
        ("Artist", artist_name),
    ]
    if release_date:
        rows.append(("Release Date", release_date))
    if upc:
        rows.append(("UPC", upc))
    if label:
        rows.append(("Label", label))
    if track_count:
        rows.append(("Tracks", str(track_count)))

    content += key_value_table(rows)

    if tracks:
        content += divider()
        content += subheading("Track Listing")
        for i, t in enumerate(tracks, 1):
            isrc_html = f' <span style="color:{TEXT_MUTED};font-size:12px;">({t.get("isrc", "")})</span>' if t.get("isrc") else ""
            content += f'''<div style="padding:6px 0;border-bottom:1px solid #eee;font-family:Arial,sans-serif;font-size:14px;color:{TEXT_DARK};">
                <span style="color:{TEXT_MUTED};margin-right:8px;">{i}.</span>{t.get("title", "Untitled")}{isrc_html}
            </div>'''

    if notes:
        content += divider()
        content += subheading("Notes")
        content += paragraph(notes)

    if platform_url:
        content += button("View Release &rarr;", f"{platform_url}/releases")

    return wrap_email(content, subject=f"Release Delivery: {release_title} by {artist_name}", preheader=f"Release info for {release_title}", platform_url=platform_url)


def action_items_push(
    recipient_name: str,
    items: List[Dict[str, Any]],
    platform_url: str = "",
) -> str:
    priority_colors = {
        "critical": "#C47068",
        "high": "#C4956B",
        "medium": SAGE_GREEN,
        "low": TEXT_MUTED,
    }

    content = heading("Your Action Items")
    content += paragraph(f"Hi {recipient_name}, here are action items that need your attention.")

    total = len(items)
    content += muted_text(f"{total} item{'s' if total != 1 else ''} pending")

    for item in items[:25]:
        p = item.get("priority", "medium")
        color = priority_colors.get(p, SAGE_GREEN)
        title = item.get("title", "Untitled")
        description = item.get("description", "")
        if len(description) > 120:
            description = description[:120] + "..."

        deadline_html = ""
        if item.get("deadline"):
            deadline_html = f'<div style="font-size:12px;color:{TEXT_MUTED};font-family:Arial,sans-serif;margin-top:4px;">&#128197; Due: {item["deadline"]}</div>'

        badges = badge(p.title(), color)
        if item.get("action_type"):
            badges += badge(item["action_type"])

        content += f'''<div style="border-left:4px solid {color};background:{SAGE_GREEN_BG};border-radius:4px;padding:12px 14px;margin:10px 0;">
            <div style="font-size:15px;font-weight:bold;color:{TEXT_DARK};font-family:Arial,sans-serif;margin-bottom:4px;">{title}</div>
            <div style="font-size:13px;color:{TEXT_MUTED};font-family:Arial,sans-serif;line-height:1.4;margin-bottom:6px;">{description}</div>
            <div>{badges}</div>
            {deadline_html}
        </div>'''

    if platform_url:
        content += button("View All Actions &rarr;", f"{platform_url}/actions")

    return wrap_email(content, subject=f"Action Items ({total} pending)", preheader=f"You have {total} action items pending", platform_url=platform_url)


def app_invite(
    recipient_name: str,
    recipient_email: str,
    org_name: str,
    inviter_name: str = "",
    role: str = "",
    platform_url: str = "",
) -> str:
    invited_by = f"<strong>{inviter_name}</strong> has invited you" if inviter_name else "You&#39;ve been invited"
    content = heading(f"You&#39;re Invited to Cadence!")
    content += paragraph(f"{invited_by} to join <strong>{org_name}</strong> on Cadence.")

    rows = [("Organization", org_name)]
    if role:
        rows.append(("Role", role))
    rows.append(("Email", recipient_email))
    content += key_value_table(rows)

    content += divider()
    content += paragraph(
        "Cadence is a next-generation music catalog intelligence platform. "
        "Manage your catalog, track royalties, handle contracts, and collaborate with your team."
    )

    if platform_url:
        content += button("Accept Invitation &rarr;", f"{platform_url}/login")
    else:
        content += paragraph(
            "Cadence is currently in early access. We&#39;ll send you a link to log in when your account is ready."
        )

    content += muted_text("If you didn&#39;t expect this invitation, you can safely ignore this email.")

    return wrap_email(content, subject=f"Invitation to join {org_name} on Cadence", preheader=f"You've been invited to {org_name}", platform_url=platform_url)


def merge_verification(
    recipient_email: str,
    client_username: str,
    org_name: str,
    code: str,
) -> str:
    content = heading("Account Merge Verification")
    content += paragraph(
        f"A client account (<strong>{client_username}</strong>) from <strong>{org_name}</strong> "
        f"has requested to merge with your Cadence account."
    )
    content += paragraph(
        "If you initiated this request, enter the verification code below in the merge request form:"
    )
    content += f"""
    <div style="text-align:center;margin:24px 0;">
      <div style="display:inline-block;background:{SAGE_GREEN_BG};border:2px solid {SAGE_GREEN};
        border-radius:12px;padding:16px 32px;font-size:32px;font-weight:bold;
        letter-spacing:8px;color:{SAGE_GREEN};font-family:monospace;">
        {code}
      </div>
    </div>
    """
    content += muted_text("This code expires in 15 minutes.")
    content += divider()
    content += paragraph(
        "Once verified, your merge request will be reviewed by an administrator. "
        "After approval, your client access will be transferred to this account."
    )
    content += muted_text("If you did not request this, you can safely ignore this email. No changes will be made to your account.")

    return wrap_email(content, subject="Account Merge Verification Code — Cadence", preheader=f"Your verification code is {code}")


def document_shared_email(
    sender_name: str,
    item_name: str,
    item_type: str = "DOCUMENT",
    message: str = "",
    platform_url: str = "",
) -> str:
    type_labels = {
        "DOCUMENT": "Document",
        "AUDIO": "Audio File",
        "STATEMENT": "Royalty Statement",
        "CONTACT_CARD": "Contact Card",
    }
    type_label = type_labels.get(item_type, "Item")

    content = heading(f"{type_label} Shared With You")
    content += paragraph(f"<strong>{sender_name}</strong> shared a {type_label.lower()} with you from Cadence.")

    if message:
        content += f'''<div style="background:{SAGE_GREEN_BG};border-left:4px solid {SAGE_GREEN};padding:12px 16px;margin:16px 0;border-radius:4px;">
            <p style="margin:0;font-size:14px;color:{TEXT_DARK};font-family:Arial,sans-serif;font-style:italic;">"{message}"</p>
        </div>'''

    content += divider()

    rows = [
        ("Item", f"<strong>{item_name}</strong>"),
        ("Type", type_label),
        ("Shared By", sender_name),
    ]
    content += key_value_table(rows)

    if platform_url:
        content += button("View in Cadence &rarr;", platform_url)
    else:
        content += paragraph("Log in to Cadence to view this shared item.")

    content += muted_text("If you don&#39;t recognize the sender, you can safely ignore this email.")

    return wrap_email(content, subject=f"{type_label} Shared: {item_name}", preheader=f"{sender_name} shared {item_name} with you", platform_url=platform_url)

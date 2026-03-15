import io
import logging
from datetime import datetime

logger = logging.getLogger("cadence")

FEATURE_LABELS = {
    "contract_parsing": "AI Contract Parsing",
    "audio_analysis": "AI Audio Analysis",
    "brief_builder": "Brief Builder",
    "csv_mapping": "CSV Column Mapping",
    "royalty_pdf_parsing": "Royalty PDF Parsing",
}

INFRASTRUCTURE_SERVICES = [
    {
        "category": "AI & Intelligence",
        "services": [
            {
                "name": "OpenAI (GPT-4o-mini)",
                "tier": "Pay-per-use",
                "base_cost": "$0 base",
                "usage_notes": "~$0.015/1K input, $0.060/1K output tokens",
                "features": ["Contract Parsing", "Audio Analysis", "Brief Builder", "CSV Mapping", "Royalty PDF Parsing"],
                "scaling": {"10": "$5-15/mo", "100": "$25-75/mo", "1000": "$150-500/mo"},
            },
        ],
    },
    {
        "category": "Email & Communications",
        "services": [
            {
                "name": "Resend",
                "tier": "Free tier (100 emails/day)",
                "base_cost": "$0/mo",
                "usage_notes": "Notifications, digests, sharing invitations, registration reports",
                "features": ["Transactional Email", "Branded Templates", "Digest Notifications"],
                "scaling": {"10": "$0/mo", "100": "$0-20/mo", "1000": "$20-50/mo"},
            },
        ],
    },
    {
        "category": "Cloud Storage",
        "services": [
            {
                "name": "Dropbox API",
                "tier": "App access (free)",
                "base_cost": "$0/mo",
                "usage_notes": "Audio file linking, org-wide scanning, creator folder linking",
                "features": ["Audio File Linking", "Org-wide Scan", "Creator Storage"],
                "scaling": {"10": "$0/mo", "100": "$0/mo", "1000": "$0/mo"},
            },
            {
                "name": "Google Drive API",
                "tier": "Free tier",
                "base_cost": "$0/mo",
                "usage_notes": "Audio file browsing and linking",
                "features": ["File Browsing", "Audio Linking"],
                "scaling": {"10": "$0/mo", "100": "$0/mo", "1000": "$0/mo"},
            },
        ],
    },
    {
        "category": "Music APIs",
        "services": [
            {
                "name": "Spotify Web API",
                "tier": "Free tier",
                "base_cost": "$0/mo",
                "usage_notes": "Playlist import, track search, release metadata lookup",
                "features": ["Playlist Import", "Track Search", "Release Lookup"],
                "scaling": {"10": "$0/mo", "100": "$0/mo", "1000": "$0/mo"},
            },
            {
                "name": "YouTube Data API",
                "tier": "Free tier (10K units/day)",
                "base_cost": "$0/mo",
                "usage_notes": "Streaming credits chart data ingestion",
                "features": ["Chart Data"],
                "scaling": {"10": "$0/mo", "100": "$0/mo", "1000": "$0/mo"},
            },
            {
                "name": "Last.fm API",
                "tier": "Free tier",
                "base_cost": "$0/mo",
                "usage_notes": "Streaming credits and chart data",
                "features": ["Chart Data"],
                "scaling": {"10": "$0/mo", "100": "$0/mo", "1000": "$0/mo"},
            },
        ],
    },
    {
        "category": "Infrastructure",
        "services": [
            {
                "name": "PostgreSQL (Replit)",
                "tier": "Included with Replit plan",
                "base_cost": "Included",
                "usage_notes": "Primary database for all application data",
                "features": ["Data Storage", "Full-text Search", "Indexing"],
                "scaling": {"10": "Included", "100": "Included", "1000": "$20-50/mo (external)"},
            },
            {
                "name": "Replit Hosting",
                "tier": "Replit Deployments",
                "base_cost": "Included",
                "usage_notes": "Application hosting with auto-scaling",
                "features": ["App Hosting", "SSL", "Custom Domain"],
                "scaling": {"10": "Included", "100": "Included", "1000": "$25-50/mo"},
            },
            {
                "name": "Domain (cadence-ci.com)",
                "tier": "Annual registration",
                "base_cost": "~$12/yr",
                "usage_notes": "Primary domain for the platform",
                "features": ["Custom Domain", "Email Routing"],
                "scaling": {"10": "$12/yr", "100": "$12/yr", "1000": "$12/yr"},
            },
        ],
    },
    {
        "category": "Push Notifications",
        "services": [
            {
                "name": "Web Push (VAPID)",
                "tier": "Free (self-hosted)",
                "base_cost": "$0/mo",
                "usage_notes": "Browser push notifications via pywebpush",
                "features": ["Push Notifications", "PWA Support"],
                "scaling": {"10": "$0/mo", "100": "$0/mo", "1000": "$0/mo"},
            },
        ],
    },
]


def generate_cost_report_pdf(ai_usage_data: dict, platform_stats: dict) -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
    )

    styles = getSampleStyleSheet()
    sage = colors.HexColor("#5B8A72")
    dark = colors.HexColor("#3D4A44")
    gray = colors.HexColor("#7A8580")
    light_bg = colors.HexColor("#F5F7F4")

    title_style = ParagraphStyle(
        "CadenceTitle",
        parent=styles["Title"],
        fontSize=24,
        textColor=sage,
        spaceAfter=4,
    )
    subtitle_style = ParagraphStyle(
        "CadenceSubtitle",
        parent=styles["Normal"],
        fontSize=11,
        textColor=gray,
        spaceAfter=20,
    )
    heading_style = ParagraphStyle(
        "CadenceHeading",
        parent=styles["Heading2"],
        fontSize=14,
        textColor=dark,
        spaceBefore=16,
        spaceAfter=8,
    )
    body_style = ParagraphStyle(
        "CadenceBody",
        parent=styles["Normal"],
        fontSize=10,
        textColor=dark,
        spaceAfter=6,
    )
    small_style = ParagraphStyle(
        "CadenceSmall",
        parent=styles["Normal"],
        fontSize=8,
        textColor=gray,
        spaceAfter=4,
    )

    elements = []

    now = datetime.utcnow()

    elements.append(Paragraph("Cadence — Catalog Intelligence", title_style))
    elements.append(Paragraph("Infrastructure Cost Report", subtitle_style))
    elements.append(Paragraph(f"Generated: {now.strftime('%B %d, %Y')}", small_style))
    elements.append(HRFlowable(width="100%", thickness=1, color=sage, spaceAfter=16))

    elements.append(Paragraph("Executive Summary", heading_style))
    total_monthly = _estimate_total_monthly(ai_usage_data)
    elements.append(Paragraph(
        f"Cadence currently serves <b>{platform_stats['total_orgs']}</b> organizations, "
        f"<b>{platform_stats['total_users']}</b> users, and manages "
        f"<b>{platform_stats['total_songs']:,}</b> catalog entries with "
        f"<b>{platform_stats['total_creators']}</b> creators.",
        body_style,
    ))
    elements.append(Paragraph(
        f"Estimated total monthly infrastructure cost: <b>${total_monthly}</b>. "
        f"The platform leverages free tiers for most external services, with AI (OpenAI) "
        f"being the primary variable cost.",
        body_style,
    ))
    elements.append(Spacer(1, 12))

    ai_total_cost = ai_usage_data["totals"]["total_cost_cents"] / 100.0
    ai_total_calls = ai_usage_data["totals"]["call_count"]
    ai_total_tokens = ai_usage_data["totals"]["total_tokens"]

    elements.append(Paragraph("AI Usage — Current Month", heading_style))

    ai_summary_data = [
        ["Metric", "Value"],
        ["Total API Calls", str(ai_total_calls)],
        ["Total Tokens", f"{ai_total_tokens:,}"],
        ["Estimated Cost", f"${ai_total_cost:.2f}"],
    ]
    ai_summary_table = Table(ai_summary_data, colWidths=[3 * inch, 3 * inch])
    ai_summary_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), sage),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("BACKGROUND", (0, 1), (-1, -1), light_bg),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#D0D5D1")),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
    ]))
    elements.append(ai_summary_table)
    elements.append(Spacer(1, 8))

    if ai_usage_data["by_feature"]:
        feature_data = [["Feature", "Calls", "Tokens", "Est. Cost"]]
        for f in ai_usage_data["by_feature"]:
            label = FEATURE_LABELS.get(f["feature"], f["feature"])
            feature_data.append([
                label,
                str(f["call_count"]),
                f"{f['total_tokens']:,}",
                f"${f['total_cost_cents'] / 100.0:.2f}",
            ])
        feature_table = Table(feature_data, colWidths=[2.5 * inch, 1.2 * inch, 1.5 * inch, 1.3 * inch])
        feature_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), sage),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("BACKGROUND", (0, 1), (-1, -1), light_bg),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#D0D5D1")),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("ALIGN", (1, 0), (-1, -1), "CENTER"),
        ]))
        elements.append(feature_table)
    elements.append(Spacer(1, 12))

    elements.append(Paragraph("Service-by-Service Breakdown", heading_style))

    for category in INFRASTRUCTURE_SERVICES:
        elements.append(Paragraph(f"<b>{category['category']}</b>", body_style))
        for svc in category["services"]:
            svc_data = [
                ["Service", "Tier", "Base Cost"],
                [svc["name"], svc["tier"], svc["base_cost"]],
            ]
            svc_table = Table(svc_data, colWidths=[2.5 * inch, 2.5 * inch, 1.5 * inch])
            svc_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E8ECE6")),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#D0D5D1")),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ]))
            elements.append(svc_table)
            elements.append(Paragraph(f"<i>{svc['usage_notes']}</i>", small_style))
        elements.append(Spacer(1, 8))

    elements.append(Paragraph("Scaling Projections", heading_style))
    elements.append(Paragraph(
        "Estimated monthly costs as the platform grows to different organization tiers.",
        body_style,
    ))

    scaling_data = [["Service", "10 Orgs", "100 Orgs", "1,000 Orgs"]]
    for category in INFRASTRUCTURE_SERVICES:
        for svc in category["services"]:
            scaling_data.append([
                svc["name"],
                svc["scaling"]["10"],
                svc["scaling"]["100"],
                svc["scaling"]["1000"],
            ])

    scaling_table = Table(scaling_data, colWidths=[2.5 * inch, 1.3 * inch, 1.3 * inch, 1.4 * inch])
    scaling_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), sage),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("BACKGROUND", (0, 1), (-1, -1), light_bg),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#D0D5D1")),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [light_bg, colors.white]),
    ]))
    elements.append(scaling_table)
    elements.append(Spacer(1, 16))

    elements.append(Paragraph("Infrastructure Recommendations", heading_style))

    rec_style = ParagraphStyle(
        "CadenceRec",
        parent=body_style,
        fontSize=9,
        leftIndent=12,
        spaceAfter=4,
    )

    total_orgs = platform_stats.get("total_orgs", 1)
    if total_orgs < 10:
        elements.append(Paragraph(
            "<b>Current Scale (1-10 orgs):</b> The platform is well-served by free tiers across all services. "
            "No immediate infrastructure changes are required. Focus on monitoring AI usage patterns to "
            "identify optimization opportunities before scaling.",
            rec_style,
        ))
        elements.append(Paragraph(
            "- Keep OpenAI usage efficient by caching common parsing templates and limiting token input length.",
            rec_style,
        ))
        elements.append(Paragraph(
            "- Resend free tier (100 emails/day) is sufficient. Monitor daily volume as org count grows.",
            rec_style,
        ))
        elements.append(Paragraph(
            "- Consider implementing AI response caching for repeated contract/CSV structures to reduce API calls.",
            rec_style,
        ))
    elif total_orgs < 100:
        elements.append(Paragraph(
            "<b>Growth Scale (10-100 orgs):</b> Begin planning for paid tiers on select services.",
            rec_style,
        ))
        elements.append(Paragraph(
            "- Upgrade Resend to a paid plan if email volume exceeds 100/day.",
            rec_style,
        ))
        elements.append(Paragraph(
            "- Implement AI request batching and caching to keep OpenAI costs under $75/mo.",
            rec_style,
        ))
        elements.append(Paragraph(
            "- Evaluate PostgreSQL performance and consider connection pooling or read replicas.",
            rec_style,
        ))
    else:
        elements.append(Paragraph(
            "<b>Enterprise Scale (100+ orgs):</b> Transition to dedicated infrastructure.",
            rec_style,
        ))
        elements.append(Paragraph(
            "- Migrate to a managed PostgreSQL provider with dedicated resources and automated backups.",
            rec_style,
        ))
        elements.append(Paragraph(
            "- Implement AI model fine-tuning on common document structures to reduce token usage by 40-60%.",
            rec_style,
        ))
        elements.append(Paragraph(
            "- Add request queuing (Redis/Celery) for AI-heavy operations to manage burst load.",
            rec_style,
        ))
        elements.append(Paragraph(
            "- Consider dedicated hosting with auto-scaling for predictable performance.",
            rec_style,
        ))
    elements.append(Spacer(1, 16))

    elements.append(HRFlowable(width="100%", thickness=0.5, color=gray, spaceAfter=8))
    elements.append(Paragraph(
        "This report was generated by Cadence — Catalog Intelligence. "
        "Cost estimates are based on published pricing as of the report date and actual tracked API usage. "
        "Actual costs may vary based on usage patterns.",
        small_style,
    ))

    doc.build(elements)
    return buffer.getvalue()


def _estimate_total_monthly(ai_usage_data: dict) -> str:
    ai_cost = ai_usage_data["totals"]["total_cost_cents"] / 100.0
    base_costs = 1.0
    total = ai_cost + base_costs
    if total < 1:
        return "<$1"
    return f"{total:.2f}"

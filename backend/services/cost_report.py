import logging
from datetime import datetime

from .branding import OrgTheme
from .pdf_engine import BrandedPDF

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
                "name": "Google Workspace",
                "tier": "$84/yr per mailbox",
                "base_cost": "$7/mo",
                "usage_notes": "Domain email hosting (communication@cadence-ci.com)",
                "features": ["Domain Email", "Email Routing", "Workspace Admin"],
                "scaling": {"10": "$7/mo", "100": "$7/mo", "1000": "$7/mo"},
            },
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
                "tier": "Premium account (required)",
                "base_cost": "~$10.99/mo",
                "usage_notes": "Playlist import, track search, release metadata lookup",
                "features": ["Playlist Import", "Track Search", "Release Lookup"],
                "scaling": {"10": "~$10.99/mo", "100": "~$10.99/mo", "1000": "~$10.99/mo"},
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
                "name": "PostgreSQL (Managed)",
                "tier": "Included with hosting plan",
                "base_cost": "Included",
                "usage_notes": "Primary database for all application data",
                "features": ["Data Storage", "Full-text Search", "Indexing"],
                "scaling": {"10": "Included", "100": "Included", "1000": "$20-50/mo (dedicated)"},
            },
            {
                "name": "Cloud Hosting",
                "tier": "Managed Deployments",
                "base_cost": "~$25/mo",
                "usage_notes": "Application hosting with auto-scaling",
                "features": ["App Hosting", "SSL", "Custom Domain"],
                "scaling": {"10": "~$25/mo", "100": "~$25/mo", "1000": "$50-100/mo"},
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
    """Render the platform-level infrastructure cost report.

    This is a Cadence-internal report, so it always uses the default Cadence
    theme (no per-org branding). It runs through the unified PDF engine so it
    automatically gets the branded header line, footer, and "Powered by
    Cadence" mark like every other Cadence PDF.
    """
    theme = OrgTheme()  # Default Cadence theme
    now = datetime.utcnow()

    pdf = BrandedPDF(
        theme,
        title="Cadence — Catalog Intelligence",
        subtitle="Infrastructure Cost Report",
    )
    pdf.cover()

    pdf.small(f"Generated: {now.strftime('%B %d, %Y')}")

    pdf.section("Executive Summary")
    total_monthly = _estimate_total_monthly(ai_usage_data)
    pdf.text(
        f"Cadence currently serves <b>{platform_stats['total_orgs']}</b> organizations, "
        f"<b>{platform_stats['total_users']}</b> users, and manages "
        f"<b>{platform_stats['total_songs']:,}</b> catalog entries with "
        f"<b>{platform_stats['total_creators']}</b> creators."
    )
    pdf.text(
        f"Estimated total monthly infrastructure cost: <b>${total_monthly}</b>. "
        f"Fixed monthly costs include Cloud Hosting, Google Workspace, and Spotify Premium. "
        f"AI (OpenAI) is the primary variable cost, scaling with catalog processing activity."
    )
    pdf.spacer(8)

    ai_total_cost = ai_usage_data["totals"]["total_cost_cents"] / 100.0
    ai_total_calls = ai_usage_data["totals"]["call_count"]
    ai_total_tokens = ai_usage_data["totals"]["total_tokens"]

    pdf.section("AI Usage — Current Month")
    pdf.kpi_row([
        {"label": "Total API Calls", "value": str(ai_total_calls)},
        {"label": "Total Tokens", "value": f"{ai_total_tokens:,}"},
        {"label": "Estimated Cost", "value": f"${ai_total_cost:.2f}"},
    ])

    if ai_usage_data["by_feature"]:
        feat_rows = []
        for f in ai_usage_data["by_feature"]:
            label = FEATURE_LABELS.get(f["feature"], f["feature"])
            feat_rows.append([
                label,
                str(f["call_count"]),
                f"{f['total_tokens']:,}",
                f"${f['total_cost_cents'] / 100.0:.2f}",
            ])
        pdf.table(
            headers=["Feature", "Calls", "Tokens", "Est. Cost"],
            rows=feat_rows,
            align=["LEFT", "CENTER", "CENTER", "RIGHT"],
        )

    pdf.section("Service-by-Service Breakdown")
    for category in INFRASTRUCTURE_SERVICES:
        pdf.subsection(category["category"])
        svc_rows = []
        for svc in category["services"]:
            svc_rows.append([svc["name"], svc["tier"], svc["base_cost"]])
        pdf.table(
            headers=["Service", "Tier", "Base Cost"],
            rows=svc_rows,
            align=["LEFT", "LEFT", "RIGHT"],
            wrap_cells=True,
        )
        for svc in category["services"]:
            pdf.small(f"<i>{svc['name']}: {svc['usage_notes']}</i>")
        pdf.spacer(4)

    pdf.section("Scaling Projections")
    pdf.text("Estimated monthly costs as the platform grows to different organization tiers.")
    scaling_rows = []
    for category in INFRASTRUCTURE_SERVICES:
        for svc in category["services"]:
            scaling_rows.append([
                svc["name"],
                svc["scaling"]["10"],
                svc["scaling"]["100"],
                svc["scaling"]["1000"],
            ])
    pdf.table(
        headers=["Service", "10 Orgs", "100 Orgs", "1,000 Orgs"],
        rows=scaling_rows,
        align=["LEFT", "CENTER", "CENTER", "CENTER"],
        wrap_cells=True,
    )

    pdf.section("Infrastructure Recommendations")
    total_orgs = platform_stats.get("total_orgs", 1)
    if total_orgs < 10:
        pdf.text(
            "<b>Current Scale (1-10 orgs):</b> The platform is well-served by free tiers across all services. "
            "No immediate infrastructure changes are required. Focus on monitoring AI usage patterns to "
            "identify optimization opportunities before scaling."
        )
        pdf.text("- Keep OpenAI usage efficient by caching common parsing templates and limiting token input length.")
        pdf.text("- Resend free tier (100 emails/day) is sufficient. Monitor daily volume as org count grows.")
        pdf.text("- Consider implementing AI response caching for repeated contract/CSV structures to reduce API calls.")
    elif total_orgs < 100:
        pdf.text("<b>Growth Scale (10-100 orgs):</b> Begin planning for paid tiers on select services.")
        pdf.text("- Upgrade Resend to a paid plan if email volume exceeds 100/day.")
        pdf.text("- Implement AI request batching and caching to keep OpenAI costs under $75/mo.")
        pdf.text("- Evaluate PostgreSQL performance and consider connection pooling or read replicas.")
    else:
        pdf.text("<b>Enterprise Scale (100+ orgs):</b> Transition to dedicated infrastructure.")
        pdf.text("- Migrate to a managed PostgreSQL provider with dedicated resources and automated backups.")
        pdf.text("- Implement AI model fine-tuning on common document structures to reduce token usage by 40-60%.")
        pdf.text("- Add request queuing (Redis/Celery) for AI-heavy operations to manage burst load.")
        pdf.text("- Consider dedicated hosting with auto-scaling for predictable performance.")

    pdf.hr()
    pdf.small(
        "This report was generated by Cadence — Catalog Intelligence. "
        "Cost estimates are based on published pricing as of the report date and actual tracked API usage. "
        "Actual costs may vary based on usage patterns."
    )

    return pdf.build()


def _estimate_total_monthly(ai_usage_data: dict) -> str:
    ai_cost = ai_usage_data["totals"]["total_cost_cents"] / 100.0
    base_costs = 25.0 + 7.0 + 10.99 + 1.0
    total = ai_cost + base_costs
    return f"{total:.2f}"

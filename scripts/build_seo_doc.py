"""Generate the SEO Launch Plan PDF for the Cadence team."""
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle,
    KeepTogether, ListFlowable, ListItem,
)

OUT = "docs/seo-launch-plan.pdf"

SAGE = colors.HexColor("#5B8A72")
INK = colors.HexColor("#3D4A44")
MUTED = colors.HexColor("#7A8580")
LIGHT_BG = colors.HexColor("#F5F7F4")
TECH_BG = colors.HexColor("#FFF8E7")
TECH_BORDER = colors.HexColor("#E0C97A")

styles = getSampleStyleSheet()

H1 = ParagraphStyle("H1", parent=styles["Heading1"], fontName="Helvetica-Bold",
                   fontSize=22, leading=26, textColor=INK, spaceAfter=10, spaceBefore=4)
H2 = ParagraphStyle("H2", parent=styles["Heading2"], fontName="Helvetica-Bold",
                   fontSize=15, leading=19, textColor=SAGE, spaceAfter=6, spaceBefore=14)
H3 = ParagraphStyle("H3", parent=styles["Heading3"], fontName="Helvetica-Bold",
                   fontSize=12, leading=15, textColor=INK, spaceAfter=4, spaceBefore=10)
BODY = ParagraphStyle("Body", parent=styles["BodyText"], fontName="Helvetica",
                     fontSize=10.5, leading=15, textColor=INK, spaceAfter=6, alignment=TA_LEFT)
MUTED_P = ParagraphStyle("Muted", parent=BODY, textColor=MUTED, fontSize=9.5, leading=13)
TECH = ParagraphStyle("Tech", parent=BODY, fontName="Courier", fontSize=9, leading=12,
                     leftIndent=8, textColor=INK)
COVER_TITLE = ParagraphStyle("CoverTitle", parent=H1, fontSize=30, leading=36, alignment=1, spaceAfter=14)
COVER_SUB = ParagraphStyle("CoverSub", parent=BODY, fontSize=14, leading=20, alignment=1, textColor=MUTED)
NOTE = ParagraphStyle("Note", parent=BODY, fontSize=9.5, leading=13, leftIndent=12,
                     textColor=INK, backColor=LIGHT_BG, borderPadding=8)
TECH_NOTE = ParagraphStyle("TechNote", parent=BODY, fontSize=9.5, leading=13, leftIndent=12,
                          textColor=INK, backColor=TECH_BG, borderPadding=8,
                          borderColor=TECH_BORDER, borderWidth=0.5)


def bullets(items, style=BODY):
    return ListFlowable(
        [ListItem(Paragraph(it, style), leftIndent=14, value="\u2022") for it in items],
        bulletType="bullet", bulletFontSize=9, bulletColor=SAGE, leftIndent=14,
    )


def numbered(items, style=BODY):
    return ListFlowable(
        [ListItem(Paragraph(it, style), leftIndent=18) for it in items],
        bulletType="1", bulletFontSize=10, bulletColor=SAGE, leftIndent=18,
    )


def table_box(rows, col_widths, header=True):
    t = Table(rows, colWidths=col_widths, hAlign="LEFT")
    style = [
        ("FONT", (0, 0), (-1, -1), "Helvetica", 9.5),
        ("TEXTCOLOR", (0, 0), (-1, -1), INK),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOX", (0, 0), (-1, -1), 0.4, colors.HexColor("#D5DDD7")),
        ("INNERGRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#E5EBE7")),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]
    if header:
        style += [
            ("BACKGROUND", (0, 0), (-1, 0), SAGE),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 9.5),
        ]
    t.setStyle(TableStyle(style))
    return t


def tech_block(title, body_html):
    """A boxed call-out marked 'Technical — skip if you're not technical'."""
    rows = [
        [Paragraph(f"<b>TECHNICAL — {title}</b>", ParagraphStyle(
            "TechHead", parent=BODY, fontSize=9, textColor=colors.white,
            fontName="Helvetica-Bold"))],
        [Paragraph(body_html, BODY)],
    ]
    t = Table(rows, colWidths=[6.5 * inch])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, 0), TECH_BORDER),
        ("BACKGROUND", (0, 1), (0, 1), TECH_BG),
        ("BOX", (0, 0), (-1, -1), 0.6, TECH_BORDER),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    return t


def hr(space=6):
    return Spacer(1, space)


story = []

# ============== COVER ==============
story.append(Spacer(1, 1.6 * inch))
story.append(Paragraph("Cadence Catalog Intelligence", COVER_SUB))
story.append(Spacer(1, 0.15 * inch))
story.append(Paragraph("SEO &amp; AI Search<br/>Launch Plan", COVER_TITLE))
story.append(Spacer(1, 0.2 * inch))
story.append(Paragraph(
    "What we shipped, what to expect, and the step-by-step playbook<br/>"
    "for getting cadence-ci.com indexed by Google, Bing, ChatGPT, and Perplexity.",
    COVER_SUB))
story.append(Spacer(1, 1.5 * inch))
story.append(Paragraph("Prepared for the Cadence team &middot; May 2026", MUTED_P))
story.append(PageBreak())

# ============== SECTION 1: WHAT WE SHIPPED ==============
story.append(Paragraph("1. What we just shipped", H1))
story.append(Paragraph(
    "We rolled out the technical foundation that lets search engines and AI assistants "
    "(Google, Bing, ChatGPT, Perplexity, Claude) actually find, understand, and recommend "
    "cadence-ci.com when people search for music catalog software, publisher analytics, "
    "or rights management tools.", BODY))
story.append(Paragraph("Plain-English summary", H2))
story.append(bullets([
    "<b>Title &amp; description tags</b> on every public page so search results show a clean, "
    "branded preview that says <i>Cadence Catalog Intelligence</i> (not just &ldquo;Cadence&rdquo; — "
    "important because Cadence Design Systems is a different, much larger company).",
    "<b>Open Graph &amp; Twitter cards</b> so when anyone shares a Cadence link on LinkedIn, "
    "X, iMessage, or Slack, it expands into a polished card with our logo, tagline, and image.",
    "<b>A purpose-built share image</b> (1200&times;630 PNG) that appears as the preview thumbnail.",
    "<b>Structured data (JSON-LD)</b> describing Cadence as an Organization and a "
    "SoftwareApplication with three pricing tiers (Basic $29.99, Pro $99.99, Enterprise $499.99). "
    "This is what AI assistants read when someone asks ChatGPT or Perplexity &ldquo;what does "
    "Cadence Catalog Intelligence do?&rdquo;",
    "<b>sitemap.xml</b> listing every public URL so Google can crawl them efficiently.",
    "<b>robots.txt</b> telling crawlers which areas to index (public pages) and which to ignore "
    "(login pages, dashboards, internal admin).",
    "<b>A hidden long-form page</b> at <font face='Courier'>/what-is-cadence</font> with the full keyword-rich "
    "product description &mdash; visible to Google &amp; AI crawlers but <b>not linked anywhere</b> on "
    "the visible site, so competitors don&rsquo;t see our roadmap when they scroll the homepage.",
]))
story.append(Paragraph("Why we hid the long-form page", H2))
story.append(Paragraph(
    "Originally we put the full feature breakdown (catalog management, valuation, royalty processing, "
    "rights administration, sync placements, creator portals, streaming intelligence) right on the "
    "homepage so search engines could crawl it. The team flagged that this also exposed our entire "
    "product strategy to anyone who scrolled &mdash; competitors included. The fix: move that content "
    "to a dedicated page (<font face='Courier'>/what-is-cadence</font>) that&rsquo;s listed in the "
    "sitemap (so Google, ChatGPT, Perplexity, etc. find and index it) but isn&rsquo;t linked from the "
    "homepage, footer, or nav. The walk-in visitor sees the vague positioning we want; the AI search "
    "engines get the full picture.",
    BODY))
story.append(tech_block("Implementation files", (
    "<font face='Courier'>frontend/index.html</font> — base meta tags + JSON-LD blocks (Organization, "
    "SoftwareApplication with 3 offers).<br/>"
    "<font face='Courier'>frontend/src/components/SEO.jsx</font> — react-helmet-async per-route "
    "title/description/canonical override component.<br/>"
    "<font face='Courier'>frontend/src/pages/WhatIsCadencePage.jsx</font> — hidden long-form page "
    "(unlinked, sitemap-only).<br/>"
    "<font face='Courier'>frontend/src/App.jsx</font> — route definition for "
    "<font face='Courier'>/what-is-cadence</font>.<br/>"
    "<font face='Courier'>frontend/public/sitemap.xml</font>, "
    "<font face='Courier'>robots.txt</font>, <font face='Courier'>og-image.png</font> &mdash; static SEO assets.")))
story.append(PageBreak())

# ============== SECTION 2: TIMELINE ==============
story.append(Paragraph("2. What to expect &mdash; the realistic timeline", H1))
story.append(Paragraph(
    "SEO is not instant. Here&rsquo;s what actually happens after we publish:", BODY))
timeline_rows = [
    ["What", "When", "Notes"],
    ["Pages live &amp; crawlable", "Immediately", "As soon as the deploy finishes (~1&ndash;2 min)."],
    ["Google discovers /what-is-cadence", "1&ndash;7 days", "Faster if you submit the sitemap manually (Step 3 below)."],
    ["Google indexes &amp; starts ranking", "1&ndash;4 weeks", "Use Search Console &ldquo;Request Indexing&rdquo; to fast-track to 24&ndash;48 hours."],
    ["Bing / DuckDuckGo indexing", "3&ndash;14 days", "Bing Webmaster Tools speeds this up."],
    ["Perplexity surfacing the site", "1&ndash;2 weeks", "Perplexity uses Bing&rsquo;s index, so once Bing has it, Perplexity does too."],
    ["GPTBot / ChatGPT picking it up", "2&ndash;8 weeks", "OpenAI&rsquo;s crawler has its own slower cadence; nothing you can do to speed it up."],
    ["Meaningful organic traffic", "2&ndash;3 months", "Once Google has crawled, indexed, and started ranking pages."],
]
parsed_rows = [[Paragraph(c, BODY if i > 0 else ParagraphStyle("th", parent=BODY,
              fontName="Helvetica-Bold", textColor=colors.white)) for i, c in enumerate([row[0], row[1], row[2]])] for row in timeline_rows]
# Re-build with proper header coloring
parsed_rows = []
for ri, row in enumerate(timeline_rows):
    if ri == 0:
        parsed_rows.append([Paragraph(c, ParagraphStyle("th", parent=BODY,
                          fontName="Helvetica-Bold", textColor=colors.white)) for c in row])
    else:
        parsed_rows.append([Paragraph(row[0], BODY),
                          Paragraph(f"<b>{row[1]}</b>", BODY),
                          Paragraph(row[2], MUTED_P)])
story.append(table_box(parsed_rows, [2.0 * inch, 1.3 * inch, 3.2 * inch]))
story.append(hr(8))
story.append(Paragraph(
    "<b>Bottom line:</b> Plan for ~2 weeks before you start seeing search results, "
    "~6 weeks before AI assistants reliably mention us, and ~3 months before SEO becomes "
    "a meaningful traffic channel. The work below is what cuts those timelines in half.", NOTE))
story.append(PageBreak())

# ============== SECTION 3: GOOGLE SEARCH CONSOLE ==============
story.append(Paragraph("3. Google Search Console &mdash; step by step", H1))
story.append(Paragraph(
    "Search Console is Google&rsquo;s free tool for telling them &ldquo;this site exists, "
    "please crawl it.&rdquo; It also shows you exactly which search queries are bringing "
    "people to the site once you start ranking. Total setup time: ~10 minutes.", BODY))

story.append(Paragraph("3.1 &mdash; Set up the property (one-time, ~5 min)", H2))
story.append(numbered([
    "Go to <b>search.google.com/search-console</b> and sign in with a Google account. "
    "Use a business account if possible &mdash; whoever owns this account owns the SEO data.",
    "Click <b>Add Property</b> &rarr; choose <b>Domain</b> (preferred &mdash; it covers "
    "cadence-ci.com plus all subdomains and both http/https).",
    "Google will give you a <b>TXT record</b> that looks like "
    "<font face='Courier' size='9'>google-site-verification=AbCdEf1234...</font>",
    "Add that TXT record in your DNS provider&rsquo;s control panel (Cloudflare, Namecheap, "
    "GoDaddy, Replit Domains, wherever cadence-ci.com is registered). The exact path is "
    "usually <i>DNS &rarr; Add Record &rarr; Type: TXT &rarr; Name: @ (or blank) &rarr; "
    "Value: paste the string Google gave you</i>.",
    "Wait 5&ndash;15 minutes for DNS to propagate, then click <b>Verify</b> in Search Console.",
]))
story.append(Paragraph(
    "If you can&rsquo;t do the Domain verification (some registrars make it tricky), the easier "
    "fallback is the <b>URL prefix</b> option using HTML file upload &mdash; but Domain is better "
    "long-term because it captures every variant of the URL.", MUTED_P))

story.append(Paragraph("3.2 &mdash; Submit the sitemap (one-time, 30 sec)", H2))
story.append(numbered([
    "In Search Console&rsquo;s left sidebar, click <b>Sitemaps</b>.",
    "In the &ldquo;Add a new sitemap&rdquo; box, type just: <font face='Courier'>sitemap.xml</font>",
    "Click <b>Submit</b>. Done.",
]))
story.append(Paragraph(
    "Google will now check that file regularly and discover all 11 URLs we listed there &mdash; "
    "including the hidden /what-is-cadence page.", BODY))

story.append(Paragraph("3.3 &mdash; Request indexing for each important URL", H2))
story.append(Paragraph(
    "This is the highest-leverage step. Without it, Google may take weeks to crawl a new page; "
    "<b>with it, usually within 24&ndash;48 hours.</b>", BODY))
story.append(numbered([
    "At the very top of Search Console there&rsquo;s a search bar that says "
    "&ldquo;Inspect any URL in cadence-ci.com&rdquo;.",
    "Paste the full URL, e.g. <font face='Courier'>https://cadence-ci.com/what-is-cadence</font>",
    "Press Enter. Google fetches the URL live (takes ~30 sec).",
    "If it says &ldquo;URL is not on Google&rdquo; (expected for a brand-new page), click "
    "<b>Request Indexing</b>.",
    "Google queues a priority crawl. Repeat for each URL on the checklist below.",
]))
story.append(Paragraph(
    "There&rsquo;s a daily quota of ~10&ndash;12 indexing requests, so spread the list "
    "below across two days if you hit the limit.", MUTED_P))

story.append(Paragraph("URL checklist &mdash; submit these in this priority order", H3))
story.append(bullets([
    "<font face='Courier'>https://cadence-ci.com/</font> &mdash; the homepage",
    "<font face='Courier'>https://cadence-ci.com/what-is-cadence</font> &mdash; the hidden SEO page (most important)",
    "<font face='Courier'>https://cadence-ci.com/about</font>",
    "<font face='Courier'>https://cadence-ci.com/help</font>",
    "<font face='Courier'>https://cadence-ci.com/careers</font>",
    "<font face='Courier'>https://cadence-ci.com/investors</font>",
]))
story.append(PageBreak())

# ============== SECTION 4: BING + AI ==============
story.append(Paragraph("4. Bing, DuckDuckGo, Perplexity &amp; ChatGPT", H1))

story.append(Paragraph("4.1 &mdash; Bing Webmaster Tools (10 min, optional but worth it)", H2))
story.append(Paragraph(
    "Bing has its own crawler &mdash; and Bing&rsquo;s index also feeds DuckDuckGo, "
    "Yahoo, Ecosia, and Perplexity. So getting into Bing is essentially &ldquo;getting into "
    "every non-Google search experience.&rdquo;", BODY))
story.append(numbered([
    "Go to <b>bing.com/webmasters</b> and sign in (Microsoft account).",
    "Click <b>Import from Google Search Console</b> &mdash; this is the magic button. It "
    "copies your verified property and sitemap directly from Google so you don&rsquo;t have "
    "to re-do DNS verification.",
    "Once imported, use Bing&rsquo;s <b>URL Submission</b> tool the same way as Google&rsquo;s "
    "Request Indexing. Bing&rsquo;s daily quota is much higher (~10,000) so submit everything "
    "at once.",
]))

story.append(Paragraph("4.2 &mdash; AI assistants (ChatGPT, Claude, Perplexity)", H2))
story.append(Paragraph(
    "There&rsquo;s no &ldquo;submit my site to ChatGPT&rdquo; button. AI assistants surface "
    "Cadence in two ways:", BODY))
story.append(bullets([
    "<b>Live web search</b> (Perplexity always, ChatGPT &amp; Claude when web access is on). "
    "These tools query Google or Bing in real time, so once we&rsquo;re indexed there, "
    "we&rsquo;re reachable here. Perplexity in particular leans heavily on Bing.",
    "<b>Trained-in knowledge</b> (the model &ldquo;knows&rdquo; about Cadence without searching). "
    "This requires the model&rsquo;s training data to include our pages. OpenAI&rsquo;s GPTBot, "
    "Anthropic&rsquo;s ClaudeBot, and Google&rsquo;s extended crawlers all visit indexed sites "
    "on their own schedule (typically every 4&ndash;12 weeks). Our robots.txt does not block "
    "any of these crawlers, so this happens automatically over time.",
]))
story.append(Paragraph(
    "The JSON-LD structured data we shipped is specifically designed for AI consumption &mdash; "
    "it says &ldquo;Cadence Catalog Intelligence is a SoftwareApplication, here&rsquo;s what "
    "category, here&rsquo;s the pricing&rdquo; in machine-readable form. This is the single "
    "biggest thing you can do to help AI assistants describe us correctly.", BODY))
story.append(tech_block("How AI crawlers see the site", (
    "Both static meta tags (rendered server-side in <font face='Courier'>frontend/index.html</font>) "
    "and per-route tags (rendered client-side via <font face='Courier'>react-helmet-async</font>) "
    "are visible to modern crawlers. Google, Bing, GPTBot, and ClaudeBot all execute JavaScript "
    "before extracting content, so the SPA architecture is not a blocker. The "
    "<font face='Courier'>SoftwareApplication</font> JSON-LD with three <font face='Courier'>Offer</font> "
    "objects (Basic/Pro/Enterprise pricing) is the canonical schema for AI assistants asked "
    "&ldquo;how much does X cost?&rdquo; Keep it accurate &mdash; if pricing changes, update "
    "<font face='Courier'>frontend/index.html</font>.")))
story.append(PageBreak())

# ============== SECTION 5: VERIFICATION ==============
story.append(Paragraph("5. How to verify it&rsquo;s working", H1))

story.append(Paragraph("5.1 &mdash; Right now (before any indexing)", H2))
story.append(numbered([
    "Visit <font face='Courier'>https://cadence-ci.com/what-is-cadence</font> directly &mdash; "
    "confirm the rich descriptive copy renders.",
    "Open <font face='Courier'>https://cadence-ci.com/</font>, scroll the entire homepage, "
    "click around the footer. Confirm <b>nothing links to /what-is-cadence</b>. (That&rsquo;s "
    "the whole point &mdash; it&rsquo;s for crawlers, not visitors.)",
    "Visit <font face='Courier'>https://cadence-ci.com/sitemap.xml</font> &mdash; confirm "
    "/what-is-cadence is listed.",
    "Visit <font face='Courier'>https://cadence-ci.com/robots.txt</font> &mdash; confirm it&rsquo;s not blocked.",
    "Paste the URL into Google&rsquo;s free <b>Rich Results Test</b> (search.google.com/test/rich-results) "
    "&mdash; should show the Organization and SoftwareApplication structured data parsing correctly.",
]))

story.append(Paragraph("5.2 &mdash; Weekly, in Search Console", H2))
story.append(bullets([
    "<b>Pages report</b> &mdash; how many of our URLs Google has indexed. Should grow from 1 &rarr; 6 &rarr; 11+ over 2&ndash;3 weeks.",
    "<b>Performance tab</b> &mdash; once we have impressions, this shows the actual queries people typed to find us, our average position, and click-through rate.",
    "<b>Coverage / Errors</b> &mdash; flags any pages Google couldn&rsquo;t crawl. Address these promptly.",
]))

story.append(Paragraph("5.3 &mdash; The smell test (3&ndash;4 weeks after publishing)", H2))
story.append(Paragraph(
    "Open Google in an incognito window and try these searches. If we&rsquo;re showing up, SEO is working:", BODY))
story.append(bullets([
    "<i>cadence catalog intelligence</i> &mdash; should be result #1 within a week.",
    "<i>cadence-ci.com</i> &mdash; should return our pages.",
    "<i>music catalog management software</i>",
    "<i>publisher analytics platform</i>",
    "<i>music catalog valuation tool</i>",
    "<i>rights management software for music publishers</i>",
]))
story.append(Paragraph(
    "Then ask the same questions to ChatGPT, Claude, and Perplexity. Within 4&ndash;6 weeks "
    "they should be able to describe Cadence Catalog Intelligence (what it does, who it&rsquo;s "
    "for, the pricing tiers) without us being explicitly mentioned in the prompt.", BODY))
story.append(PageBreak())

# ============== SECTION 6: OWNER CHECKLIST ==============
story.append(Paragraph("6. Owner checklist", H1))
story.append(Paragraph(
    "Suggested division of labor &mdash; assign one owner per item.", MUTED_P))

story.append(Paragraph("This week", H2))
story.append(bullets([
    "[ ] Set up Google Search Console (Section 3.1)",
    "[ ] Submit sitemap.xml in Search Console (Section 3.2)",
    "[ ] Request indexing for all 6 URLs in the checklist (Section 3.3)",
    "[ ] Set up Bing Webmaster Tools via the Import-from-Google button (Section 4.1)",
    "[ ] Run the 5 verification checks in Section 5.1",
]))

story.append(Paragraph("Within 30 days", H2))
story.append(bullets([
    "[ ] Check Search Console weekly &mdash; track Pages indexed and impressions",
    "[ ] Run the &ldquo;smell test&rdquo; searches in Section 5.3",
    "[ ] Ask ChatGPT &amp; Perplexity &ldquo;what is Cadence Catalog Intelligence?&rdquo; &mdash; track answer quality",
    "[ ] If a key URL still isn&rsquo;t indexed after 14 days, re-request indexing",
]))

story.append(Paragraph("Quarterly", H2))
story.append(bullets([
    "[ ] Review which queries are bringing the most impressions/clicks (Search Console &rarr; Performance)",
    "[ ] Update sitemap.xml lastmod dates if any pages have been substantively rewritten",
    "[ ] Refresh JSON-LD pricing in frontend/index.html if tier prices have changed",
    "[ ] Consider adding 1&ndash;2 new content pages (use cases, customer stories) to the sitemap as the product matures",
]))
story.append(PageBreak())

# ============== APPENDIX ==============
story.append(Paragraph("Appendix &mdash; Technical reference", H1))
story.append(Paragraph(
    "For developers maintaining the SEO setup. Skip this section if you&rsquo;re not "
    "working with the codebase.", MUTED_P))

story.append(Paragraph("File map", H2))
appendix_rows = [
    ["File", "Purpose"],
    ["frontend/index.html", "Base meta tags, OG/Twitter cards, JSON-LD (Organization + SoftwareApplication w/ 3 offers). Loaded for every route."],
    ["frontend/src/components/SEO.jsx", "react-helmet-async wrapper. Per-route override of &lt;title&gt;, meta description, canonical URL, OG/Twitter tags."],
    ["frontend/src/main.jsx", "Mounts &lt;HelmetProvider&gt; so per-route SEO components work."],
    ["frontend/src/pages/WhatIsCadencePage.jsx", "Hidden long-form SEO page. Unlinked. Discoverable only via direct URL or sitemap."],
    ["frontend/src/App.jsx", "Route definition for /what-is-cadence in the unauthenticated routes block."],
    ["frontend/public/sitemap.xml", "Static sitemap listing 11 public URLs. Update lastmod when pages change."],
    ["frontend/public/robots.txt", "Allow public, disallow authenticated app surfaces. References sitemap."],
    ["frontend/public/og-image.png", "1200x630 share preview image. Referenced from index.html OG/Twitter blocks."],
]
parsed_app = []
for ri, row in enumerate(appendix_rows):
    if ri == 0:
        parsed_app.append([Paragraph(c, ParagraphStyle("th", parent=BODY,
                          fontName="Helvetica-Bold", textColor=colors.white)) for c in row])
    else:
        parsed_app.append([Paragraph(f"<font face='Courier' size='8.5'>{row[0]}</font>", BODY),
                          Paragraph(row[1], BODY)])
story.append(table_box(parsed_app, [2.6 * inch, 3.9 * inch]))

story.append(Paragraph("Key architectural decisions", H2))
story.append(bullets([
    "<b>Brand-leading titles.</b> Every &lt;title&gt; begins with &ldquo;Cadence Catalog Intelligence&rdquo; "
    "to disambiguate from Cadence Design Systems (a much larger company) in search results.",
    "<b>Hardcoded fallback in index.html.</b> Static title/description/JSON-LD are present in "
    "the served HTML so crawlers without JS execution still see canonical metadata. Per-route "
    "react-helmet-async tags override at runtime.",
    "<b>Hidden page architecture for /what-is-cadence.</b> The page is publicly accessible "
    "(not gated, not cloaked, not user-agent-sniffed &mdash; that would violate Google&rsquo;s "
    "quality guidelines). It is simply unlinked from the visible UI. Discoverability comes "
    "from sitemap.xml inclusion. This satisfies SEO/AI discoverability without exposing the "
    "full feature breakdown to walk-in visitors.",
    "<b>JSON-LD pricing.</b> Three Offer objects (Basic 29.99, Pro 99.99, Enterprise 499.99 USD) "
    "in the SoftwareApplication block. Update these in frontend/index.html when pricing changes; "
    "this is the canonical answer AI assistants give when asked about cost.",
    "<b>Disallow authenticated routes.</b> robots.txt blocks /dashboard, /catalog, /roster, "
    "/contracts, /admin, /internal, etc. so private app surfaces never appear in search results.",
]))

story.append(Paragraph("Maintenance triggers", H2))
story.append(bullets([
    "<b>Pricing change</b> &rarr; update Offer prices in JSON-LD inside frontend/index.html.",
    "<b>New public page</b> &rarr; add &lt;Route&gt; in App.jsx, mount &lt;SEO&gt; component on the page, "
    "add &lt;url&gt; entry to sitemap.xml.",
    "<b>Brand or tagline change</b> &rarr; update the static &lt;title&gt;, meta description, OG tags "
    "in frontend/index.html, plus the default fullTitle in SEO.jsx.",
    "<b>Pricing tier added/removed</b> &rarr; sync both the JSON-LD offers and any pricing "
    "page copy (currently no pricing page is built &mdash; flagged for a future task).",
]))
story.append(Spacer(1, 0.4 * inch))
story.append(Paragraph(
    "Questions? See replit.md (&ldquo;SEO &amp; AI Search Visibility&rdquo; section) for the "
    "current architectural summary, or check the commit history on Tasks #202 and #203 for "
    "context on why each piece was built the way it was.", MUTED_P))


def header_footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 8.5)
    canvas.setFillColor(MUTED)
    if doc.page > 1:
        canvas.drawString(0.75 * inch, 0.55 * inch,
                         "Cadence Catalog Intelligence  -  SEO & AI Search Launch Plan")
        canvas.drawRightString(LETTER[0] - 0.75 * inch, 0.55 * inch, f"Page {doc.page}")
    canvas.restoreState()


doc = SimpleDocTemplate(
    OUT, pagesize=LETTER,
    leftMargin=0.85 * inch, rightMargin=0.85 * inch,
    topMargin=0.85 * inch, bottomMargin=0.85 * inch,
    title="Cadence — SEO & AI Search Launch Plan",
    author="Cadence Catalog Intelligence",
)
doc.build(story, onFirstPage=header_footer, onLaterPages=header_footer)
print(f"Wrote {OUT}")

# Music Industry Knowledge Base

Use this to answer industry-concept questions and to translate between platform UI labels and the underlying real-world concepts. Be concise; prefer plain English over jargon. **Never** invent dollar amounts, percentages, stream counts, or row counts — call a tool and quote the tool's result instead.

---

## 1. RECORDING vs COMPOSITION (the two copyrights)

A song is two separate copyrights, owned and paid out independently.

| | Recording (master) | Composition (work) |
|---|---|---|
| Identifier | **ISRC** | **ISWC** |
| Owners | Label / artist / producer (master holders) | Songwriters + publishers |
| What it is | A specific recorded performance | The underlying lyrics + melody |
| Cadence section | **Catalog** (songs) | **Works** |
| Linkage | Many recordings can share one composition (covers, remixes, re-records) | One composition can map to many recordings |

**Worked example.** "Yesterday" by The Beatles has *one* composition (Lennon/McCartney, ISWC T-…) but hundreds of recordings (each a distinct ISRC). A sync that licenses Aretha Franklin's recording must clear *both* her recording (master licence from her label) *and* the Lennon/McCartney composition (sync licence from the publisher).

---

## 2. SPLITS — ownership math

Splits express percentage ownership and **must total 100% per side** (master and publishing). Cadence enforces this in the Rights tab.

- **Master split** — % of recording revenue. Usually flows to the label and/or featured artists. Producers commonly get 3–5 master "points".
- **Publishing split** — % of composition revenue. Always conceptually two halves:
  - **Writer's share** = 50% of publishing — goes directly to songwriters, *cannot be assigned away* in most jurisdictions.
  - **Publisher's share** = 50% of publishing — paid to publishers / co-publishers / administrators.

**Worked example — co-publishing deal.** A songwriter signs a 50/50 co-pub with a publisher.
- Writer's share: 50% (untouched, all to writer)
- Publisher's share: 50% — split 50/50 between writer and publisher → 25% each
- **Net:** writer 75% / publisher 25% of total publishing revenue.

**Worked example — admin deal.** Songwriter keeps 100% of both halves but pays the admin a 15% commission off the top of collected income. The admin owns no copyright.

When Cadence shows a `pub_share` of 50 on a credit, that means 50% of the *publishing side* — i.e. 50% of half of the song's total earnings, before any other adjustments.

---

## 3. PROs AND COLLECTION SOCIETIES

A song must be **registered with each relevant society** before that society will pay out. Cadence tracks per-society registration on every Song via `SongRegistration` rows (one row per `(song, registry_type)`). The seven registries Cadence supports are:

| Registry | Side | Pays for |
|---|---|---|
| **ASCAP** | Composition | US performance |
| **BMI** | Composition | US performance |
| **SESAC** | Composition | US performance (invite-only) |
| **GMR** | Composition | US performance (boutique) |
| **MLC** (Mechanical Licensing Collective) | Composition | US blanket mechanicals from interactive streaming |
| **HFA** (Harry Fox Agency) | Composition | US mechanical licences |
| **SoundExchange** | Master | Digital + satellite performance of the *recording* |

International equivalents to mention when relevant: **PRS for Music** (UK), **SOCAN** (Canada), **GEMA** (Germany), **SACEM** (France), **JASRAC** (Japan).

**Routing rule of thumb.** A US writer typically picks one PRO (ASCAP *or* BMI *or* SESAC *or* GMR — they're mutually exclusive) **and** registers the work with the MLC for streaming mechanicals. A US-released recording also needs a SoundExchange registration to collect digital-performance master royalties. HFA is used for one-off compulsory mechanical licences (NOIs) and for some publisher administration.

---

## 4. THE 6 REVENUE TYPES

Where the money in a royalty statement comes from:

1. **Mechanical** — per-stream / per-download payment owed to the **composition** holder. US statutory rate is set by the **CRB** (Copyright Royalty Board). Streaming mechanicals in the US flow through **MLC**.
2. **Performance** — every public performance (radio, streaming, TV, venues). Owed to the **composition** holder, paid via **PROs** (ASCAP/BMI/SESAC/GMR + foreign sister societies).
3. **Sync** — one-time licence fee for placement in film, TV, ads, games, trailers. Negotiated case-by-case. Two licences are usually required: master sync (recording) + sync (composition).
4. **Master / Neighbouring rights** — payment for the **recording** itself: digital performance via SoundExchange in the US; "neighbouring rights" overseas via PPL (UK) and equivalents.
5. **Direct DSP** — distributor pays the master holder per stream/download (Spotify, Apple, Amazon, etc.). This is the *master-side* counterpart to MLC mechanicals.
6. **Print** — sheet music. Small, mostly legacy.

**Worked example — what gets paid for one Spotify stream of a US recording in the US.**
- Master side: Spotify pays the distributor → distributor pays the label/master-holder per the **direct DSP** rate. Cadence sees this in the *master* royalty statement.
- Composition side, mechanical: Spotify pays the **MLC** at the CRB rate; MLC routes to the publisher / writer.
- Composition side, performance: Spotify pays the **PROs** at the agreed performance rate; PRO routes to writer + publisher.
- Net: every stream produces three small payments to two different sides of the catalogue. SoundExchange does **not** apply to interactive streaming — that's non-interactive only (Pandora ad-supported, satellite, webcasting).

---

## 5. STATEMENTS, MATCHING, AND ALLOCATION

A **royalty statement** is a periodic report from a payer (label, PRO, distributor, sub-publisher, MLC, SoundExchange) listing earnings line-by-line. Each line typically has: `period`, `song / ISRC / ISWC`, `source` (DSP), `units`, `gross`, `fees`, `net`.

Cadence's pipeline:
1. **Ingest** — parse the file (PDF / CSV / Excel) into raw `RoyaltyStatementLine` rows.
2. **Match** — link each line to a Song. Match priority is **ISRC → ISWC → fuzzy(title + artist)**.
3. **Allocate** — fan the matched net out across creators using the song's **RightsSplit**.
4. **Ledger** — write `Earnings` rows per creator/period and roll into the Payables view.

**Match-rate guidance for the user:**
- Match rate **≥ 95%** — green; the statement is healthy, allocations are trustworthy.
- Match rate **80–95%** — yellow; review the unmatched lines tab to fix ISRC typos or add missing songs.
- Match rate **< 80%** — red; the file likely has the wrong column mapping or is for a catalogue you don't represent. Re-check the column-mapping step.

---

## 6. CONTRACTS

- **Recording / Master agreement** — between artist and label. Defines master ownership, royalty rate, advance, recoupment.
- **Publishing agreement** — between songwriter and publisher. Defines publishing share, advance, term, recoupment.
- **Co-publishing** — see §2 worked example. Net commonly 75/25 in the writer's favour.
- **Administration deal** — admin collects worldwide on writer's behalf for a fee (10–25%). Writer keeps copyright.
- **Sub-publishing** — territory-specific rep for a publisher abroad.
- **Sync licence** — one-shot licence for a recording + composition pair to be used in a specific media production.
- **Distribution agreement** — distributor delivers masters to DSPs, takes a fee/percentage.

Common terms: **advance**, **recoupment**, **term**, **territory**, **option period**, **reversion**, **MFN** (most-favoured nation), **cross-collateralisation**.

Cadence's `ContractStatus` enum covers the lifecycle: **DRAFT → PENDING → ACTIVE → EXPIRED** (or **TERMINATED** as a side branch).

---

## 7. SYNC PIPELINE

A sync placement moves through Cadence's `Placement.status` field:

`PITCHED → IN_REVIEW → IN_NEGOTIATION → SECURED → DELIVERED → AIRED → PAID`

Side branches (terminal): **DECLINED**, **CANCELLED**.

Use the `update_placement_status` write tool to move a placement; the platform will write an audit-log entry on confirm.

---

## 8. VALUATION

Cadence's Valuation page supports four methodologies and a **Blended** view that defaults to **40% Income / 30% Market Comparable / 30% DCF**.

| Method | Core idea | When to trust it |
|---|---|---|
| **Income** | Project forward existing royalty streams, discount to present value. | Stable catalogues with ≥ 12 months of clean statements. |
| **Market Comparable** | Apply a per-stream or per-revenue **multiple** observed in recent catalogue sale comps. | New catalogues with little statement history but strong streaming volume. |
| **DCF (Discounted Cash Flow)** | Explicit yearly revenue model with a **decay rate** and **discount rate**. | Heritage catalogues where decay is well-modelled; institutional underwriting. |
| **Blended** | 40/30/30 weighted average of the three above. | The default Cadence shows on the Valuation summary card. |

**Confidence < 50%** on a valuation means there isn't enough clean royalty data to underwrite it — tell the user to upload more recent statements, fix unmatched lines, or accept a wider valuation range. Don't quote a precise dollar figure when confidence is below 50% — quote the range instead.

**Multiplier intuition.** Streaming-heavy contemporary catalogues tend to comp at **5–8x** annual net royalties; heritage / sync-heavy catalogues at **10–20x**; legacy publishing standards even higher. These are *general* market signals, not Cadence-specific quotes — always defer to the actual `Valuation.amount` returned by the tool when answering about a real catalogue.

---

## 9. ROYALTY AUDIT ENGINE — THE 4 CHECKS

Cadence's Royalty Audit page runs four checks against ingested statements + contract rate cards. Each finding has a severity (CRITICAL / HIGH / MEDIUM / LOW).

| Check | What it flags | Typical severity |
|---|---|---|
| **CROSS_STATEMENT** | The same `(period, song, source)` reports different `net` amounts across two statements (e.g. distributor vs PRO vs sub-publisher). | HIGH–CRITICAL when delta > $100 or > 10%. |
| **RATE_CHECK** | The effective per-stream / per-unit rate on a statement is below the contract rate-card minimum or below the period-over-period mean by > 30%. | HIGH when below contract; MEDIUM on statistical drop. |
| **MISSING_PERIOD** | A payer that historically reports monthly/quarterly is missing an expected period. | HIGH if > 60 days late, MEDIUM otherwise. |
| **DECAY_ANOMALY** | Month-over-month earnings on a song decline more steeply than the catalogue's modelled decay curve. | MEDIUM by default; HIGH when the song is also in a Top-50 contract. |

**Severity bands** map to action: CRITICAL = open finding now and stop payouts on the affected line; HIGH = open finding, investigate within the period; MEDIUM = batch into the monthly review; LOW = trend-watch.

---

## 10. CREATOR / RIGHTS-HOLDER ROLES (credit roles)

- **Primary Artist** — the artist of record on the recording.
- **Featured Artist** — guest performer (split-eligible).
- **Songwriter / Composer / Lyricist** — composition author(s).
- **Producer** — producer points (typically 3–5% of master).
- **Publisher / Sub-publisher / Administrator** — collect on the composition side.
- **Mixer / Engineer** — typically work-for-hire, no ongoing royalties.

---

## 11. QUICK GLOSSARY

- **ISRC** — International Standard Recording Code (per recording).
- **ISWC** — International Standard Musical Work Code (per composition).
- **IPI / CAE** — Interested Parties Information; songwriter/publisher PRO ID.
- **DSP** — Digital Service Provider (Spotify, Apple Music, YouTube Music, Amazon, Tidal, etc.).
- **NOI** — Notice of Intent (compulsory mechanical licence).
- **CRB** — Copyright Royalty Board (sets US statutory rates).
- **MFN** — Most-Favoured Nation clause; ties one party's terms to the best terms given to another.
- **Recoupment** — the advance is paid back from the artist's earnings before the artist sees further checks.
- **Cross-collateralisation** — earnings from one project can recoup an advance from another.
- **UPC** — Universal Product Code, the release-level identifier (album / EP / single).

---

## 12. COMMON Q&A — pattern-match these before answering

When the user's question matches one of the patterns below, lean on the answer pattern (and back it with a tool call if a real number is involved).

**"Why isn't this song earning?"** → check (a) registration completeness via `get_song_health` (any registry stuck in NOT_STARTED?), (b) statement match rate (was it matched?), (c) is it `is_released = true`? Walk the user through the three.

**"How much is my catalogue worth?"** → never guess. Direct them to the **Valuation** page; if they ask in chat, surface the platform's current Blended figure and call out confidence < 50% explicitly if applicable.

**"Should I register with both ASCAP and BMI?"** → no — they're mutually exclusive PROs. A US writer picks one. They *should* additionally register with **MLC** (mechanical streaming) and **SoundExchange** (digital master performance).

**"What does an X% publishing split mean for me?"** → see §2 — it's a percentage of the *publishing side*, which is itself half of the song's total earnings unless a co-pub or admin reshapes it.

**"What's the difference between MLC and HFA?"** → MLC = blanket licence + payout for **streaming** mechanicals (post-MMA). HFA = traditional mechanical licensing house, primarily one-off NOIs and publisher admin.

**"My audit shows a CROSS_STATEMENT critical — what now?"** → quote both statements side-by-side, flag the larger delta, and direct the user to the **Royalty Audit** page → click the finding → either resolve (if the discrepancy is explained) or open a payer dispute.

**"Can you mark this as registered with MLC for me?"** → use the `mark_song_registered` write tool with `registry="MLC"` and `status="REGISTERED"` (or whichever status the user named). Tell the user what they're confirming; the platform will show the Confirm button.

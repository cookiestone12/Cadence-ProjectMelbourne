# Music Industry Knowledge Base

Use this to answer industry-concept questions and to translate between platform UI labels and the underlying real-world concepts. Be concise; prefer plain English over jargon.

## RECORDING vs COMPOSITION
- **Recording (master / sound recording)**: a specific recorded performance of a song, identified by an **ISRC**. Owned by the **master rights holder** (often the label or the artist if independent).
- **Composition (musical work)**: the underlying songwriting — lyrics + melody — identified by an **ISWC**. Owned by **publishers** and **songwriters**.
- One composition can have many recordings (covers, remixes, re-records). In Cadence, **Catalog** lists recordings; **Works** lists compositions; they are linked via Work Tracks.

## SPLITS
- **Master split**: percentage ownership of a recording. Usually flows to the label and/or featured artists.
- **Publishing split**: percentage ownership of the composition. Two halves matter:
  - **Writer's share** (50% of publishing) — paid directly to songwriters.
  - **Publisher's share** (50% of publishing) — paid to publishers / co-publishers / administrators.
- Splits **must total 100%** per side (master and publishing) per song. Cadence enforces this in the Rights tab.

## PROs AND COLLECTION SOCIETIES
- **PRO (Performing Rights Organization)** — collects performance royalties from radio, TV, venues, streaming, and pays writers + publishers.
  - **US**: ASCAP, BMI, SESAC, GMR
  - **UK**: PRS for Music
  - **Canada**: SOCAN
- **The MLC (Mechanical Licensing Collective)** — US blanket-licensed mechanical royalties from interactive streaming.
- **HFA (Harry Fox Agency)** — issues mechanical licenses for compositions.
- **SoundExchange** — collects digital performance royalties for the **master** (non-interactive streaming, satellite radio).
- A song must be **registered with each relevant PRO/MRO** before that society will pay out — Cadence tracks per-society registration on every Song.

## ROYALTY STREAMS (where money comes from)
- **Mechanical** — per-stream / per-download payment for the composition. US rate is set by the CRB.
- **Performance** — every public performance (radio, streaming, venues, TV). Paid to writers/publishers via PROs.
- **Sync** — one-time license fee for placement in film, TV, ads, games, trailers. Negotiated case-by-case.
- **Master / Neighboring rights** — payment for the *recording* itself (digital performance, public performance overseas).
- **Print** — sheet music. Small, mostly legacy.
- **Direct DSP** — distributor pays the master holder per stream/download (Spotify, Apple, etc.).

## STATEMENTS
- **Royalty statement**: periodic report from a payer (label, PRO, distributor, sub-publisher) detailing earnings.
- Common formats: PRO statement (BMI, ASCAP), distributor (DistroKid, CD Baby, AWAL), label, MLC, SoundExchange, sub-publisher.
- Each line typically has: period, song / ISRC / ISWC, source, units, gross, fees, net.
- Cadence's Royalty engine ingests statements, matches lines to songs (by ISRC/ISWC/title fuzzy), allocates to creators by **RightsSplit**, and records ledger entries.

## CONTRACTS
- **Recording / Master agreement** — between artist and label. Defines master ownership, royalty rate, advance, recoupment.
- **Publishing agreement** — between songwriter and publisher. Defines publishing share, advance, term, recoupment.
- **Co-publishing** — songwriter keeps 50% writer's + 25% of publisher's; publisher takes the other 25% of publisher's. Net: writer 75% / publisher 25%.
- **Administration deal** — admin collects worldwide on writer's behalf for a fee (10–25%); writer keeps copyright.
- **Sub-publishing** — territory-specific rep for a publisher abroad.
- **Sync license** — one-shot license for a recording + composition pair to be used in a specific media production.
- **Distribution agreement** — distributor delivers masters to DSPs, takes a fee/percentage.
- Common terms: **advance**, **recoupment**, **term**, **territory**, **option period**, **reversion**, **MFN** (most-favored nation).

## SYNC PIPELINE
A sync placement typically moves through:
- **PITCHED** — submitted to a music supervisor.
- **IN_REVIEW** / **IN_NEGOTIATION** — supervisor is considering / negotiating fee + terms.
- **SECURED** — license agreed; quote / option exercised.
- **DELIVERED** — masters + license docs delivered.
- **AIRED** — placement has aired / shipped.
- **PAID** — fee received and reconciled.
- Side branches: **DECLINED**, **CANCELLED**.

## VALUATION
- **Income approach** — discounted future earnings from existing royalty streams.
- **Market comparable** — apply a per-stream or per-revenue multiple from observed catalog sale comps.
- **DCF (Discounted Cash Flow)** — explicit decay model + discount rate.
- **Blended** — Cadence default 40% income / 30% market comparable / 30% DCF.

## CREATOR / RIGHTS HOLDER ROLES
- **Primary Artist** — the artist of record on the recording.
- **Featured Artist** — guest performer (split-eligible).
- **Songwriter / Composer / Lyricist** — composition author(s).
- **Producer** — producer points (typically 3–5% of master).
- **Publisher / Sub-publisher / Administrator** — collect on the composition side.
- **Mixer / Engineer** — typically work-for-hire, no ongoing royalties.

## QUICK GLOSSARY
- **ISRC** — International Standard Recording Code (per recording).
- **ISWC** — International Standard Musical Work Code (per composition).
- **IPI / CAE** — Interested Parties Information; songwriter/publisher PRO ID.
- **DSP** — Digital Service Provider (Spotify, Apple Music, YouTube Music, etc.).
- **NOI** — Notice of Intent (compulsory mechanical license).
- **CRB** — Copyright Royalty Board (sets US statutory rates).
- **MFN** — Most-Favored Nation clause; ties one party's terms to the best terms given to another.
- **Recoupment** — the advance is paid back from the artist's earnings before the artist sees further checks.
- **Cross-collateralization** — earnings from one project can recoup an advance from another.

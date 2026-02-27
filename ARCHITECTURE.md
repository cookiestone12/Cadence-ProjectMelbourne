# Cadence — Catalog Intelligence

## Full Architecture & Feature Breakdown

---

## 1. System Overview

Cadence is a multi-tenant SaaS platform for music labels, publishers, production companies, and independent creators to manage music catalogs, rights, royalties, and sync placements. It provides end-to-end tools from catalog ingestion through royalty accounting, with a client portal for external collaborators.

### Tech Stack

| Layer | Technology |
|:---|:---|
| **Frontend** | React 18, Vite, Tailwind CSS, Recharts, Heroicons |
| **Backend** | Python, FastAPI, SQLAlchemy ORM, Gunicorn/Uvicorn |
| **Database** | PostgreSQL (66+ tables) |
| **Auth** | JWT (PyJWT) + bcrypt password hashing |
| **Email** | Resend API with branded HTML templates |
| **AI** | OpenAI (gpt-4o-mini) for document parsing, column mapping, audio analysis, brief matching |
| **Integrations** | Spotify Web API, Dropbox SDK, Google Drive |
| **Background Jobs** | APScheduler (email digests, storage scans) |
| **PWA** | Service worker, web manifest, push notifications (pywebpush) |

### Deployment

- **Runtime**: Gunicorn with Uvicorn workers serving FastAPI
- **Static Assets**: Frontend built by Vite, served by FastAPI's StaticFiles mount
- **Entry Point**: `run_backend.sh` handles DB setup, then starts the server
- **Boot Sequence**: `db_setup.py` runs schema migrations and seed data before the app starts

---

## 2. Project Structure

```
/
├── backend/
│   ├── main.py                 # FastAPI app, middleware, router registration
│   ├── db_setup.py             # Schema creation, migrations, seed data
│   ├── models/
│   │   ├── __init__.py         # Re-exports all models and get_db
│   │   └── models.py           # All SQLAlchemy models (66+ tables)
│   ├── routes/                 # API route handlers (30+ files)
│   ├── services/               # Business logic, external integrations
│   ├── templates/              # Email HTML templates
│   └── utils/                  # Auth, logging, parsing helpers
├── frontend/
│   ├── src/
│   │   ├── App.jsx             # Root component, routing
│   │   ├── pages/              # Page-level components (32 files)
│   │   └── components/         # Reusable UI components (16 files)
│   ├── public/                 # Static assets, SW, manifest
│   └── index.html              # Entry HTML
├── run_backend.sh              # Production startup script
├── replit.md                   # Project summary (auto-loaded)
└── ARCHITECTURE.md             # This file
```

---

## 3. Authentication & Multi-Tenancy

### Authentication Flow
1. User submits credentials to `POST /api/auth/login`
2. Backend validates password hash (bcrypt) and returns a JWT token
3. Frontend stores token and sends it as `Authorization: Bearer <token>` on all requests
4. `get_current_user` dependency extracts and validates the JWT on protected routes

### Multi-Tenant Architecture
- Every data entity is scoped to an `organization_id`
- Users belong to organizations via `OrganizationMember` (with roles: OWNER, ADMIN, MEMBER, CLIENT)
- `verify_org_access()` checks membership before allowing data access
- Super admins (`is_super_admin=True`) bypass org checks
- Client users have restricted access via the client portal

### User Roles
| Role | Scope |
|:---|:---|
| **Super Admin** | Platform-wide access, all orgs |
| **Owner** | Full org control, billing, member management |
| **Admin** | Full feature access within org |
| **Member** | Standard access within org |
| **Client** | External creator access via client portal |

---

## 4. Backend Routes (API)

### Core Management

| File | Prefix | Purpose |
|:---|:---|:---|
| `auth.py` | `/api/auth` | Registration, login, password changes |
| `organizations.py` | `/api/organizations` | Org CRUD, membership, access codes |
| `tenant_admin.py` | `/api/tenant-admin` | User management, branding, permissions, creator linking |
| `settings.py` | `/api/settings` | User/app preferences |
| `audit_log.py` | `/api/audit-log` | Activity history with action/type/user filtering |

### Catalog & Content

| File | Prefix | Purpose |
|:---|:---|:---|
| `catalog.py` | `/api/catalog` | Bulk upload, summary stats, search, Schedule A export |
| `songs.py` | `/api/songs` | Song CRUD, duplicate detection, merging, bulk delete |
| `creators.py` | `/api/creators` | Creator/artist roster management, images, contacts |
| `works.py` | `/api/works` | Musical works (compositions), folder organization |
| `releases.py` | `/api/releases` | Albums/EPs/singles, track ordering, distribution readiness |
| `credits.py` | `/api/songs` | Contributor credits (writers, producers, etc.) |
| `checklist.py` | `/api/songs` | Metadata completeness tracking per song |

### Rights & Contracts

| File | Prefix | Purpose |
|:---|:---|:---|
| `contracts_mgmt.py` | `/api/rights` | Contract CRUD, parties, song splits, AI parsing |
| `contracts.py` | `/api/contracts` | Legacy contract file uploads |
| `contract_docs.py` | `/api/rights` | Document attachment to contracts |
| `account_links.py` | `/api/account-links` | Cross-org data sharing consent |

### Financial & Royalties

| File | Prefix | Purpose |
|:---|:---|:---|
| `royalties.py` | `/api/royalties` | Statement upload, transaction matching, fee management |
| `royalty_processing.py` | `/api/royalty-processing` | Advanced pipeline: line reconciliation, ledger, payees, advances |
| `expenses.py` | `/api/expenses` | Recoupable expense tracking |
| `valuations.py` | `/api/songs` | Per-song financial valuation |
| `valuation_reports.py` | `/api/valuation` | Catalog-wide valuation reports |

### Integrations & Tools

| File | Prefix | Purpose |
|:---|:---|:---|
| `integrations.py` | `/api/integrations` | Dropbox/Google Drive OAuth, file browsing |
| `spotify_import.py` | `/api/spotify` | Spotify metadata lookup, playlist import |
| `audio.py` | `/api/audio` | Audio file management, AI analysis (BPM, key, mood) |
| `storage_scan.py` | `/api/storage-scan` | Cloud storage scanning for audio files |
| `csv_upload.py` | `/api/csv` | CSV/Excel/PDF ingestion with AI column mapping |
| `brief_builder.py` | `/api/brief-builder` | AI-powered sync brief matching |

### Operational

| File | Prefix | Purpose |
|:---|:---|:---|
| `actions.py` | `/api/actions` | Action items, gap detection, priority scoring |
| `placements.py` | `/api/placements` | Sync placement pipeline (PITCHED → PAID) |
| `notifications.py` | `/api/notifications` | In-app notification management |
| `push.py` | `/api/push` | Web push subscription and delivery |
| `client_portal.py` | `/api/client-portal` | Client-facing API (profile, catalog, contracts, accounting) |
| `client_sharing.py` | `/api/client-sharing` | Passcode-based creator sharing |
| `creative_directory.py` | `/api/creative-directory` | Industry contact management, per-client sharing |

### Reporting

| File | Prefix | Purpose |
|:---|:---|:---|
| `registration_reports.py` | `/api/registration-reports` | PRO registration tracking and PDF generation |
| `schedule_a.py` | `/api/schedule-a` | Schedule A document generation/export |
| `analytics.py` | `/api/analytics` | Growth charts, revenue overview, rights coverage |
| `bulk.py` | `/api/bulk` | Bulk operations across entities |
| `exports.py` | `/api/creators` | Creator-specific Schedule A exports |

---

## 5. Frontend Pages

### Authentication & Landing
| Page | Route | Purpose |
|:---|:---|:---|
| `Login.jsx` | `/` | Sign-in form |
| `Home.jsx` | `/home` | Public landing / Schedule A template download |
| `HomePage.jsx` | `/dashboard` | Main authenticated dashboard with revenue charts, pipeline, action items |

### Catalog Management
| Page | Route | Purpose |
|:---|:---|:---|
| `NewCatalogPage.jsx` | `/catalog` | Primary catalog view: songs list, Spotify import, Schedule A upload, bulk edit, duplicate detection |
| `CatalogPage.jsx` | `/catalog-legacy` | Legacy simplified catalog view |
| `SongDetail.jsx` | `/songs/:id` | Full song detail: metadata, credits, splits, audio, analytics |
| `WorksPage.jsx` | `/works` | Musical works with folder organization, ISWC tracking |
| `ReleasesPage.jsx` | `/releases` | Album/release management, distribution readiness checks |

### People & Contacts
| Page | Route | Purpose |
|:---|:---|:---|
| `RosterPage.jsx` | `/roster` | Creator roster with health scores, status tracking |
| `CreatorDetailPage.jsx` | `/creators/:id` | Creator profile: bio, catalog, accounting, action items |
| `CreativeDirectoryPage.jsx` | `/directory` | Industry contacts: music supervisors, agencies, labels. Multi-select sharing, per-client sharing |

### Rights & Contracts
| Page | Route | Purpose |
|:---|:---|:---|
| `ContractsPage.jsx` | `/contracts` | Contract list, creation, AI parsing, document management, split sheets |

### Financial
| Page | Route | Purpose |
|:---|:---|:---|
| `RoyaltiesPage.jsx` | `/royalties` | Multi-tab hub: Processing (statement ingestion, matching), Payables (payments, advances), Analytics |
| `ValuationPage.jsx` | `/valuation` | Catalog appraisal with multiple valuation methodologies |

### Placements & Sync
| Page | Route | Purpose |
|:---|:---|:---|
| `PlacementsPage.jsx` | `/placements` | Sync pipeline: PITCHED → CONFIRMED → LICENSED → PAID |
| `BriefBuilderPage.jsx` | `/brief-builder` | AI-powered song matching from natural language briefs |
| `SyncReportsPage.jsx` | `/sync-reports` | Client-facing sync activity reports |

### Administration
| Page | Route | Purpose |
|:---|:---|:---|
| `TenantAdminPage.jsx` | `/admin` | Org settings: members, branding, access codes, activity log, client management |
| `AdminDashboard.jsx` | `/super-admin` | Platform-wide admin metrics |
| `Settings.jsx` | `/settings` | User preferences, notification settings, API status |

### Tools & Reports
| Page | Route | Purpose |
|:---|:---|:---|
| `ActionItemsPage.jsx` | `/actions` | Task management with priority scoring and deadlines |
| `RegistrationReportPage.jsx` | `/registration` | PRO registration workflow, PDF/CSV export |
| `ReportsPage.jsx` | `/reports` | Multi-tab reporting with charts |
| `StorageScanPage.jsx` | `/storage-scan` | Cloud storage file scanner with fuzzy matching |
| `SearchPage.jsx` | `/search` | Global search across songs, creators, releases |
| `UserGuidePage.jsx` | `/guide` | Platform documentation (password-protected) |

### External / Shared
| Page | Route | Purpose |
|:---|:---|:---|
| `ClientPortalPage.jsx` | `/client-portal` | Full client interface: Profile, Catalog, Placements, Contracts, Accounting, Directory, Access |
| `SharedContactsPage.jsx` | `/shared/contacts/:token` | Public token-based contact card viewing |

---

## 6. Reusable Components

| Component | Purpose |
|:---|:---|
| `Sidebar.jsx` | Main navigation menu (collapsible, responsive) |
| `Navigation.jsx` | Top bar with user profile and logout |
| `NotificationBell.jsx` | Real-time notification dropdown |
| `AddSongModal.jsx` | Manual song creation form |
| `SongDetailModal.jsx` | Quick-view song editor (metadata, splits, DSP links) |
| `ScheduleAUploadModal.jsx` | Bulk import wizard (CSV/Excel/PDF/Word with AI parsing) |
| `ClientSharingModal.jsx` | Creator sharing link generation |
| `EmailSendModal.jsx` | In-app email composer |
| `FolderPicker.jsx` | Cloud storage folder browser (Dropbox/Google Drive) |
| `ContractAdvancesSection.jsx` | Advance recoupment progress display |
| `CreatorAccountingEnhanced.jsx` | Creator-specific ledger and balance view |
| `PayablesTab.jsx` | Payee list with payment batch management |
| `ProcessingInboxPanel.jsx` | Royalty statement ingestion landing zone |
| `StatementDetailView.jsx` | Granular statement line-item view |
| `RoyaltyAnalyticsDashboard.jsx` | Revenue charts (by channel, territory, right category) |
| `ActionsTab.jsx` | Creator-specific action items list |

---

## 7. Database Schema

### Summary
- **66+ tables** managed by SQLAlchemy ORM
- Schema created/migrated automatically via `db_setup.py` on every boot
- All entities scoped by `organization_id` for multi-tenancy

### Core Entities

**Users & Organizations**
- `users` — Platform accounts (username, email, hashed_password, is_admin, is_super_admin)
- `organizations` — Tenant entities (name, display_name, type, account_type, access_code)
- `organization_members` — User-org membership (role, linked_creator_id, client_access_scope)

**Creators & Contacts**
- `creators` — Artists/writers/producers (display_name, legal_name, email, roles[], IPI, PRO, hero_image_url)
- `creative_contacts` — Industry contacts (name, company, email, phone, role, specialty)
- `creator_contacts` — Links creators to their contacts with roles
- `client_shared_contacts` — Per-client contact sharing (admin shares specific contacts with client users)

**Songs & Works**
- `songs` — Recordings (title, primary_artist, ISRC, ISWC, release_date, BPM, key, mood tags)
- `song_credits` — Creator credits per song (role, share_percentage)
- `song_dsp_links` — Streaming platform links (Spotify, Apple Music, etc.)
- `song_checklist_status` — Metadata completeness tracking
- `works` — Compositions (title, ISWC, work_type, folder_id)
- `work_credits` — Creator credits per work
- `work_tracks` — Links works to song recordings
- `work_folders` — Hierarchical folder organization for works
- `releases` — Albums/EPs/singles (title, UPC, release_date, artwork)
- `release_tracks` — Track listing within releases

### Rights & Contracts

- `contracts` — Legal agreements (title, type, status, dates, territory, advance, payment_direction)
- `contract_parties` — Parties to a contract (name, role, creator link)
- `contract_assets` — Links contracts to songs/works/releases
- `contract_documents` — Uploaded files attached to contracts
- `song_contracts` — Legacy song-contract associations
- `rights_splits` — Per-asset ownership splits (validated to 100%)
- `account_links` — Cross-org data sharing links (individual_org ↔ enterprise_org, consent workflow)

### Royalties & Accounting

- `royalty_statements` — Uploaded earning statements (source, period, status, file_path)
- `royalty_statement_lines` — Individual line items from statements (track, revenue, matching status)
- `royalty_transactions` — Processed transactions linked to songs (revenue_cents, platform, territory)
- `royalty_allocations` — Split allocations per transaction (amount per rights holder)
- `royalty_processing_runs` — Audit trail for processing batches
- `royalty_ledger_entries` — Double-entry accounting ledger
- `payees` — Payment recipients linked to creators
- `payments` — Outbound payments (amount, status, method)
- `advances` / `advance_pools` — Advance tracking with recoupment
- `fees` — Fee deductions (admin fees, distribution fees)
- `expenses` — Recoupable costs (category, status, amount)

### Placements & Sync

- `placements` — Sync deals (title, type: FILM/TV/AD/GAME, status pipeline, fee, licensee)

### Notifications & Tasks

- `notifications` — In-app alerts (type, message, is_read, link)
- `notification_preferences` — Per-user notification settings
- `org_notification_settings` — Org-wide notification config
- `email_digest_preferences` — Digest frequency per user
- `action_items` — Tasks with deadlines, priorities, and cross-module linking
- `audit_logs` — Activity history (action, entity_type, entity_id, details JSON)
- `push_subscriptions` — Web push endpoints per user

### Analytics & Valuation

- `analytics` — Song-level analytics data
- `song_streaming_metrics` — Streaming counts and trends
- `territory_revenue` — Revenue breakdown by geography
- `song_valuation_snapshots` — Point-in-time valuation captures
- `valuation_calculations` — Detailed valuation methodology results

### Integrations & Storage

- `platform_integrations` — Connected third-party services
- `integration_accounts` — OAuth tokens for Dropbox/Google Drive
- `audio_assets` — Audio file references (provider, file_path, song link)
- `creator_storage_links` — Per-creator cloud folder links
- `storage_scan_results` — Scan findings with fuzzy match scores

### Sharing & Access

- `client_shares` — Passcode-based creator sharing invitations
- `shared_contact_links` — Token-based public contact card links (expiring)
- `registration_reports` — PRO registration report records

---

## 8. Backend Services

### Business Logic

| Service | Purpose |
|:---|:---|
| `audit_service.py` | Centralized action logging (`log_action`) |
| `contract_parser.py` | AI-powered contract document parsing (PDF/Word → structured data) |
| `document_parser.py` | General document parsing for Schedule A and catalog imports |
| `royalty_processing_engine.py` | Full royalty pipeline: line parsing, auto-matching, split calculation, ledger entries |
| `reconciliation_engine.py` | Financial reconciliation with control totals and match summaries |
| `classification_engine.py` | Revenue classification (right categories, channels, territories) |
| `scoring_engine.py` | Proprietary health/value scoring |
| `valuation_engine.py` | Catalog financial valuation (streaming multiples, revenue multiples, market comps) |
| `decay_analytics_engine.py` | Revenue trend analysis with exponential decay modeling |
| `schedule_a_ingestion.py` | Schedule A document processing and mapping |
| `schedule_a_service.py` | Schedule A CSV export generation |

### External Integrations

| Service | Purpose |
|:---|:---|
| `spotify_service.py` | Spotify Web API: search, metadata lookup, playlist/album import |
| `storage_service.py` | Dropbox/Google Drive OAuth, file operations, folder browsing |
| `scan_service.py` | Cloud storage scanning with fuzzy filename matching |
| `email_provider.py` | Email delivery abstraction (Resend API) |
| `chartmetric_service.py` | Chartmetric analytics data |
| `luminate_service.py` | Luminate (Nielsen) consumption data |

### Background Jobs

| Service | Purpose |
|:---|:---|
| `email_scheduler.py` | APScheduler setup with two recurring jobs |

**Scheduled Jobs:**
1. **Email Digest** — Every 15 minutes: checks user preferences and sends action item digest emails
2. **Storage Scan** — Every hour: triggers automatic scans of linked cloud storage folders

### Email Templates

| Template | Purpose |
|:---|:---|
| `email_base.py` | Shared HTML layout, CSS, UI components (buttons, badges, tables) |
| `email_digest.py` | Action item digest email template |
| `email_templates.py` | Templates for invites, registration reports, contact sharing, distribution alerts |

---

## 9. Utilities

| Utility | Purpose |
|:---|:---|
| `auth.py` | Password hashing (bcrypt), JWT creation/validation, `get_current_user` dependency |
| `logging_config.py` | Structured JSON logging configuration (logger name: "cadence") |
| `csv_parser.py` | AI-powered CSV column inference and mapping |
| `catalog_gaps.py` | Catalog analysis for missing metadata (ISRC, ISWC, credits) |
| `health_sync.py` | Song health score recalculation |
| `priority_engine.py` | Action item priority scoring and sorting |
| `reminders.py` | Proactive reminder generation for missing data |
| `action_notifications.py` | Notification dispatch for action items and deadlines |
| `cross_module_tasks.py` | Auto-generation of tasks across system modules |

---

## 10. Key Feature Flows

### Catalog Ingestion
1. User uploads CSV/Excel/PDF/Word via Schedule A Upload Modal
2. `csv_upload.py` sends file to AI for column mapping (`csv_parser.py`)
3. Mapped data previewed in UI with suggested field assignments
4. On confirm, `schedule_a_ingestion.py` creates Song records and SongCredits
5. Audit log records the import action

### Royalty Processing Pipeline
1. Admin or client uploads royalty statement (CSV from BMI/ASCAP/Spotify/etc.)
2. `royalties.py` calls preview endpoint for source detection and column mapping
3. Upload creates `RoyaltyStatement` and `RoyaltyTransaction` records
4. Auto-matcher links transactions to songs by ISRC/title/artist
5. Unmatched transactions can be manually matched
6. Processing engine calculates splits based on contracts
7. Ledger entries created for double-entry accounting
8. Payables generated for creator payments

### Contract AI Parsing
1. User uploads a contract PDF/Word document
2. `contract_parser.py` extracts text and sends to OpenAI
3. AI returns structured data: title, type, dates, territory, advance, parties
4. Form fields auto-populated for review
5. On save, parsed document auto-attached to the contract

### Sync Placement Pipeline
```
PITCHED → CONFIRMED → LICENSED → PLACED → AIRED → INVOICED → PAID
```
Each status transition is tracked with timestamps. Financial data (sync fees, license terms) tracked throughout. Automatic accounting integration when status reaches PAID.

### Client Portal Flow
1. Admin creates a client user linked to a Creator
2. Client logs in and sees their portal with tabs: Profile, Catalog, Placements, Contracts, Accounting, Directory, Access
3. Client can edit profile, add/edit songs, import Schedule As, create contracts with AI parsing, upload royalty statements
4. All actions are audit-logged and visible to the org admin
5. Client can grant other companies access using shareable 8-character access codes

### Brief Builder (AI Song Matching)
1. User enters a natural language description of desired music
2. Optional structured filters (BPM range, key, mood, genre)
3. AI parses the description into search parameters
4. Songs ranked by relevance using tag matching and metadata
5. Results returned with match scores and audio preview links

### Cloud Storage Scanning
1. Admin links a creator to a Dropbox or Google Drive folder
2. Scheduled job (hourly) or manual trigger initiates a scan
3. `scan_service.py` recursively reads folder contents
4. Fuzzy matching compares filenames to song titles in catalog
5. Results presented for review: accept to link audio file to song, or dismiss
6. Accepted files create `AudioAsset` records linked to songs

---

## 11. Security Model

### Authentication
- JWT tokens with configurable expiration
- bcrypt password hashing (cost factor 12)
- Case-insensitive username login
- Session secret required via `SESSION_SECRET` env var

### Authorization
- Organization membership checked on every data access
- Role-based access for admin operations
- Client portal restricted to own creator's data
- `client_access_scope` controls cross-client visibility (OWN vs ALL)
- Super admin bypasses all org checks

### Data Isolation
- Every query filtered by `organization_id`
- Cross-org sharing requires explicit `AccountLink` with mutual consent
- Client contact sharing requires explicit admin action (`ClientSharedContact`)

### External Access
- Shared contact links are token-based with expiration
- Client sharing uses 6-digit passcodes
- Company access uses 8-character alphanumeric codes
- Public routes registered separately from authenticated routes

---

## 12. External Integrations

### Spotify
- **Auth**: Client credentials flow (app key/secret)
- **Features**: Track/album/artist search, playlist import, release metadata lookup
- **Data**: Track titles, artists, ISRCs, album art, preview URLs

### Dropbox
- **Auth**: OAuth 2.0 (PKCE flow)
- **Features**: Folder browsing, file linking, per-creator folder association
- **Background**: Scheduled scans with fuzzy filename matching to catalog

### Google Drive
- **Auth**: OAuth 2.0
- **Features**: Folder browsing, file linking (parallel to Dropbox)

### OpenAI (gpt-4o-mini)
- **CSV Column Mapping**: Infers field assignments from sample data
- **Document Parsing**: Extracts song/creator info from Schedule A PDFs
- **Contract Parsing**: Extracts legal terms from contract documents
- **Audio Analysis**: Generates BPM, key, mood, texture, sync tags
- **Brief Builder**: Parses natural language into structured search queries

### Resend
- **Purpose**: Transactional email delivery
- **Templates**: Registration reports, action item digests, contact sharing, invitations

---

## 13. Progressive Web App (PWA)

- **Manifest**: `frontend/public/manifest.json` with app name, icons, theme color
- **Service Worker**: `frontend/public/sw.js` handles offline caching and push notifications
- **Push Notifications**: VAPID-based web push via `pywebpush`
- **Install Prompt**: Native app install banner on supported browsers

---

## 14. Environment Variables

| Variable | Purpose |
|:---|:---|
| `SESSION_SECRET` | JWT signing secret (required) |
| `DATABASE_URL` | PostgreSQL connection string |
| `OPENAI_API_KEY` | OpenAI API access |
| `RESEND_API_KEY` | Email delivery |
| `DROPBOX_APP_KEY` | Dropbox OAuth |
| `DROPBOX_APP_SECRET` | Dropbox OAuth |
| `VAPID_PRIVATE_KEY` | Web push notifications |
| `SPOTIFY_CLIENT_ID` | Spotify API (via integration) |
| `SPOTIFY_CLIENT_SECRET` | Spotify API (via integration) |

import React, { useRef, useState } from 'react'
import { ArrowDownTrayIcon, ChevronRightIcon, LockClosedIcon } from '@heroicons/react/24/outline'

const VERSION = '2.6'
const LAST_UPDATED = 'February 2026'

const sections = [
  { id: 'getting-started', title: '1. Getting Started' },
  { id: 'dashboard', title: '2. Home Dashboard' },
  { id: 'navigation', title: '3. Navigation & Layout' },
  { id: 'search', title: '4. Global Search' },
  { id: 'roster', title: '5. Creator Roster' },
  { id: 'catalog', title: '6. Catalog Management' },
  { id: 'works', title: '7. Works (Compositions)' },
  { id: 'releases', title: '8. Releases' },
  { id: 'contracts', title: '9. Contracts & Rights' },
  { id: 'actions', title: '10. Action Items' },
  { id: 'royalties', title: '11. Royalties' },
  { id: 'placements', title: '12. Placements' },
  { id: 'sync-reports', title: '13. Sync Reports' },
  { id: 'brief-builder', title: '14. Brief Builder' },
  { id: 'directory', title: '15. Creative Directory' },
  { id: 'registration-reports', title: '16. Registration Reports' },
  { id: 'cloud-storage', title: '17. Cloud Storage Integration' },
  { id: 'storage-scan', title: '18. Storage Scan' },
  { id: 'audio-analysis', title: '19. Audio Analysis & Tagging' },
  { id: 'reports', title: '20. Reports & Analytics' },
  { id: 'valuation', title: '21. Catalog Valuation' },
  { id: 'settings', title: '22. Settings & Integrations' },
  { id: 'tips', title: '23. Tips & Best Practices' },
  { id: 'glossary', title: '24. Glossary' },
]

function SectionHeading({ id, children }) {
  return (
    <h2 id={id} className="text-2xl font-bold text-[#3D4A44] mt-12 mb-4 pb-2 border-b-2 border-[#5B8A72] print:break-before-page">
      {children}
    </h2>
  )
}

function SubHeading({ children }) {
  return <h3 className="text-lg font-semibold text-[#3D4A44] mt-6 mb-2">{children}</h3>
}

function Tip({ children }) {
  return (
    <div className="bg-[#EEF6F0] border-l-4 border-[#5B8A72] p-4 my-4 rounded-r-lg">
      <p className="text-sm text-[#3D4A44]"><span className="font-semibold">Tip:</span> {children}</p>
    </div>
  )
}

function FeatureCard({ title, description }) {
  return (
    <div className="bg-white border border-[rgba(59,77,67,0.1)] rounded-xl p-4 shadow-sm">
      <h4 className="font-semibold text-[#3D4A44] mb-1">{title}</h4>
      <p className="text-sm text-[#7A8580]">{description}</p>
    </div>
  )
}

function KeyValue({ label, children }) {
  return (
    <div className="flex items-start gap-2 mb-2">
      <span className="font-medium text-[#3D4A44] min-w-[140px] text-sm">{label}:</span>
      <span className="text-sm text-[#7A8580]">{children}</span>
    </div>
  )
}

function StepList({ steps }) {
  return (
    <ol className="list-decimal list-inside space-y-2 my-3 ml-2">
      {steps.map((step, i) => (
        <li key={i} className="text-sm text-[#3D4A44] leading-relaxed">{step}</li>
      ))}
    </ol>
  )
}

function ButtonRef({ label, color }) {
  const bgColor = color === 'green' ? 'bg-[#5B8A72]' : color === 'red' ? 'bg-red-500' : color === 'blue' ? 'bg-blue-500' : 'bg-[#3D4A44]'
  return (
    <span className={`inline-flex items-center px-2 py-0.5 ${bgColor} text-white text-xs rounded-md font-medium mx-1`}>
      {label}
    </span>
  )
}

const GUIDE_PASSWORD = 'Cadence1225!'

export default function UserGuidePage() {
  const contentRef = useRef(null)
  const [unlocked, setUnlocked] = useState(() => sessionStorage.getItem('guide_unlocked') === 'true')
  const [passwordInput, setPasswordInput] = useState('')
  const [passwordError, setPasswordError] = useState(false)

  const handleUnlock = (e) => {
    e.preventDefault()
    if (passwordInput === GUIDE_PASSWORD) {
      setUnlocked(true)
      sessionStorage.setItem('guide_unlocked', 'true')
      setPasswordError(false)
    } else {
      setPasswordError(true)
    }
  }

  if (!unlocked) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-[#F5F7F5] to-[#EEF6F0] flex items-center justify-center p-4">
        <form onSubmit={handleUnlock} className="bg-white rounded-[20px] shadow-lg p-8 w-full max-w-sm text-center">
          <div className="w-14 h-14 bg-[#EEF6F0] rounded-2xl flex items-center justify-center mx-auto mb-5">
            <LockClosedIcon className="w-7 h-7 text-[#5B8A72]" />
          </div>
          <h2 className="text-xl font-bold text-[#3D4A44] mb-1">User Guide</h2>
          <p className="text-sm text-[#7A8580] mb-6">Enter the password to access the guide</p>
          <input
            type="password"
            value={passwordInput}
            onChange={e => { setPasswordInput(e.target.value); setPasswordError(false) }}
            placeholder="Password"
            className={`w-full px-4 py-3 rounded-xl border ${passwordError ? 'border-red-400 bg-red-50' : 'border-[rgba(59,77,67,0.15)]'} text-[15px] text-[#3D4A44] placeholder-[#B0B8B3] focus:outline-none focus:ring-2 focus:ring-[#5B8A72]/30 focus:border-[#5B8A72] transition-colors mb-3`}
            autoFocus
          />
          {passwordError && (
            <p className="text-red-500 text-sm mb-3">Incorrect password. Please try again.</p>
          )}
          <button
            type="submit"
            className="w-full px-4 py-3 bg-[#5B8A72] text-white font-medium rounded-xl hover:bg-[#4A7862] transition-colors"
          >
            Unlock Guide
          </button>
        </form>
      </div>
    )
  }

  const handlePrint = () => {
    window.print()
  }

  const scrollTo = (id) => {
    const el = document.getElementById(id)
    if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }

  return (
    <div className="min-h-screen bg-[#FAFBF9]">
      <div className="no-print sticky top-0 z-50 bg-white/95 backdrop-blur-md border-b border-[rgba(59,77,67,0.1)] px-6 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <img src="/logo-small.png" alt="Logo" className="h-8 w-auto" />
          <span className="text-lg font-bold text-[#3D4A44]">User Guide</span>
          <span className="text-xs text-[#7A8580] bg-[#EEF1EC] px-2 py-0.5 rounded-full">v{VERSION}</span>
        </div>
        <button
          onClick={handlePrint}
          className="flex items-center gap-2 px-4 py-2 bg-[#5B8A72] text-white rounded-lg hover:bg-[#4A7A62] transition-colors text-sm font-medium shadow-sm"
        >
          <ArrowDownTrayIcon className="w-4 h-4" />
          Save as PDF
        </button>
      </div>

      <div ref={contentRef} className="max-w-4xl mx-auto px-6 py-8 print:max-w-none print:px-12 print:py-8">
        <div className="text-center mb-12 print:mb-16">
          <img src="/cadence-logo.png" alt="Cadence" className="h-24 w-auto mx-auto mb-6" />
          <h1 className="text-2xl sm:text-4xl font-bold text-[#3D4A44] mb-2">Cadence</h1>
          <p className="text-xl text-[#5B8A72] font-medium mb-1">Catalog Intelligence</p>
          <p className="text-lg text-[#7A8580]">User Guide & Reference Manual</p>
          <div className="mt-4 text-sm text-[#7A8580]">
            Version {VERSION} &middot; Last Updated: {LAST_UPDATED}
          </div>
        </div>

        <div className="bg-white rounded-2xl border border-[rgba(59,77,67,0.1)] p-6 mb-10 shadow-sm print:border print:shadow-none">
          <h2 className="text-lg font-bold text-[#3D4A44] mb-4">Table of Contents</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-1">
            {sections.map((s) => (
              <button
                key={s.id}
                onClick={() => scrollTo(s.id)}
                className="flex items-center gap-2 text-left text-sm text-[#5B8A72] hover:text-[#3D4A44] hover:bg-[#EEF1EC] px-3 py-2 rounded-lg transition-colors no-print-link"
              >
                <ChevronRightIcon className="w-3 h-3 flex-shrink-0" />
                {s.title}
              </button>
            ))}
          </div>
        </div>

        {/* ===== 1. GETTING STARTED ===== */}
        <SectionHeading id="getting-started">1. Getting Started</SectionHeading>
        
        <SubHeading>Logging In</SubHeading>
        <p className="text-sm text-[#7A8580] mb-3">
          Navigate to the application URL and you will see the login screen. Enter your username and password provided by your organization administrator, then click <ButtonRef label="Sign In" color="green" />.
        </p>
        <StepList steps={[
          'Open the application in your web browser.',
          'Enter your username in the "Username" field.',
          'Enter your password in the "Password" field.',
          'Click "Sign In" to access your dashboard.',
        ]} />
        <Tip>Your session will remain active until you log out or your token expires. If you are redirected to the login page unexpectedly, simply log in again.</Tip>

        <SubHeading>Understanding Your Organization</SubHeading>
        <p className="text-sm text-[#7A8580] mb-3">
          Cadence is a multi-tenant platform. All your data — songs, creators, contracts, and more — is scoped to your organization. Each user belongs to an organization, and all content you create is visible only to members of that organization.
        </p>

        <SubHeading>User Roles</SubHeading>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 my-4">
          <FeatureCard title="Member" description="Standard access to all catalog management features within your organization." />
          <FeatureCard title="Admin" description="Full access plus organization settings, user management, and team configuration via the Org Admin panel." />
          <FeatureCard title="Owner" description="Highest organization-level role with all Admin capabilities plus the ability to transfer ownership and manage billing." />
          <FeatureCard title="Super Admin" description="Platform-wide access for managing all organizations and users (platform operators only)." />
        </div>

        {/* ===== 2. HOME DASHBOARD ===== */}
        <SectionHeading id="dashboard">2. Home Dashboard</SectionHeading>
        <p className="text-sm text-[#7A8580] mb-4">
          The Home Dashboard is your command center. It provides a real-time overview of your catalog's health and highlights items requiring attention.
        </p>

        <SubHeading>Dashboard Widgets</SubHeading>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 my-4">
          <FeatureCard title="Urgent Action Items" description="Displays overdue and high-priority tasks across all modules. Click any item to navigate directly to the related entity." />
          <FeatureCard title="Recent Notifications" description="Shows your latest notifications including contract alerts, catalog updates, and system events." />
          <FeatureCard title="Needs Attention" description="Songs with low health scores that need metadata completion, missing credits, or other improvements." />
          <FeatureCard title="Top Creators" description="Your highest-performing creators ranked by catalog size and activity." />
          <FeatureCard title="Placement Pipeline" description="Summary of your placement activity including total placements, pipeline value, paid amount, and active pitches." />
          <FeatureCard title="Tasks by Module" description="Breakdown of pending action items organized by module (songs, works, releases, contracts, placements, royalties)." />
        </div>
        <Tip>The dashboard auto-refreshes when you navigate to it. Use it as your starting point each session to quickly identify what needs your attention first.</Tip>

        {/* ===== 3. NAVIGATION ===== */}
        <SectionHeading id="navigation">3. Navigation & Layout</SectionHeading>
        
        <SubHeading>Sidebar</SubHeading>
        <p className="text-sm text-[#7A8580] mb-3">
          The left sidebar is your primary navigation tool. It provides quick access to all major sections of the application:
        </p>
        <div className="bg-white rounded-xl border border-[rgba(59,77,67,0.1)] p-4 my-4">
          <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
            {[
              { icon: '🏠', label: 'Home', desc: 'Dashboard overview' },
              { icon: '🔍', label: 'Search', desc: 'Global search' },
              { icon: '👥', label: 'Roster', desc: 'Creator management' },
              { icon: '📇', label: 'Directory', desc: 'Industry contacts' },
              { icon: '🎵', label: 'Catalog', desc: 'Song management' },
              { icon: '📝', label: 'Works', desc: 'Compositions' },
              { icon: '💿', label: 'Releases', desc: 'Albums & EPs' },
              { icon: '📋', label: 'Contracts', desc: 'Deal management' },
              { icon: '✅', label: 'Actions', desc: 'Task inbox' },
              { icon: '💰', label: 'Royalties', desc: 'Financial engine' },
              { icon: '🎬', label: 'Placements', desc: 'Sync licensing' },
              { icon: '📄', label: 'Sync Reports', desc: 'Placement reports' },
              { icon: '✨', label: 'Brief Builder', desc: 'AI song matching' },
              { icon: '☁️', label: 'Storage Scan', desc: 'File scanning' },
              { icon: '📋', label: 'Reg. Reports', desc: 'PRO registration' },
              { icon: '📊', label: 'Reports', desc: 'Analytics' },
              { icon: '💎', label: 'Valuation', desc: 'Catalog value' },
            ].map(item => (
              <div key={item.label} className="flex items-center gap-2 p-2 rounded-lg bg-[#FAFBF9]">
                <span className="text-lg">{item.icon}</span>
                <div>
                  <div className="text-xs font-semibold text-[#3D4A44]">{item.label}</div>
                  <div className="text-[10px] text-[#7A8580]">{item.desc}</div>
                </div>
              </div>
            ))}
          </div>
        </div>

        <SubHeading>Mobile Navigation</SubHeading>
        <p className="text-sm text-[#7A8580] mb-3">
          On mobile devices and smaller screens, the sidebar is hidden by default. Tap the menu icon (three horizontal lines) in the top-left corner to open the sidebar. Tap any menu item or anywhere outside the sidebar to close it.
        </p>

        <SubHeading>Notification Bell</SubHeading>
        <p className="text-sm text-[#7A8580] mb-3">
          The notification bell icon in the sidebar header shows your unread notification count. Click it to open the notification dropdown where you can view recent notifications, mark them as read, or delete individual notifications. Use <ButtonRef label="Mark All Read" color="green" /> to clear all unread indicators at once.
        </p>

        {/* ===== 4. GLOBAL SEARCH ===== */}
        <SectionHeading id="search">4. Global Search</SectionHeading>
        <p className="text-sm text-[#7A8580] mb-3">
          The Search page provides unified search across your entire catalog. You can search for songs, works, releases, and creators all from one place.
        </p>

        <SubHeading>How to Use Search</SubHeading>
        <StepList steps={[
          'Navigate to the Search page from the sidebar.',
          'Type your search term in the search bar. Results update automatically as you type.',
          'Use the entity type filter buttons (Songs, Works, Releases, Creators) to narrow results to specific categories.',
          'Click any result to navigate directly to that item\'s detail view.',
        ]} />
        <Tip>Search matches against titles, artist names, ISRCs, and other identifying fields. Try searching by partial names or codes for quick lookups.</Tip>

        {/* ===== 5. CREATOR ROSTER ===== */}
        <SectionHeading id="roster">5. Creator Roster</SectionHeading>
        <p className="text-sm text-[#7A8580] mb-3">
          The Creator Roster is your directory of all artists, writers, producers, and other creators in your catalog. Each creator has a visual profile card showing their key statistics.
        </p>

        <SubHeading>Viewing the Roster</SubHeading>
        <p className="text-sm text-[#7A8580] mb-3">
          The Roster page displays creator cards in a grid layout. Each card shows the creator's name, roles, number of songs, and a profile image (if uploaded). Use the search bar at the top to filter creators by name.
        </p>

        <SubHeading>Adding a Creator</SubHeading>
        <StepList steps={[
          'Click the + Add Creator button at the top of the Roster page.',
          'Fill in the creator details: Name (required), roles (Artist, Writer, Producer, etc.), territory, PRO affiliation, and IPI number.',
          'Click Save to create the creator profile.',
        ]} />

        <SubHeading>Creator Profile Image</SubHeading>
        <p className="text-sm text-[#7A8580] mb-3">
          Each creator card has a camera icon overlay on hover. Click the image area to upload a profile photo. Supported formats include JPEG and PNG.
        </p>

        <SubHeading>Creator Detail Page</SubHeading>
        <p className="text-sm text-[#7A8580] mb-3">
          Click any creator card to view their detailed profile. The detail page shows:
        </p>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 my-4">
          <FeatureCard title="Creator Info" description="Name, roles, territory, PRO, IPI number, and profile image. Click Edit to modify details." />
          <FeatureCard title="Song Catalog" description="Complete list of songs credited to this creator with health scores and metadata." />
          <FeatureCard title="Schedule A Export" description="Download a CSV of the creator's full catalog, formatted as a Schedule A document for contracts." />
          <FeatureCard title="Bulk CSV Import" description="Upload a CSV file to bulk-add songs for this creator. Supports AI-powered column mapping." />
        </div>

        <SubHeading>Creator Accounting Tab</SubHeading>
        <p className="text-[#7A8580] mb-3">
          Each creator profile includes an <strong>Accounting</strong> tab showing their complete financial summary:
        </p>
        <ul className="list-disc pl-5 text-[#7A8580] space-y-1 mb-3">
          <li>Royalty earnings from all sources</li>
          <li>Placement revenue from sync deals</li>
          <li>Fees breakdown (management, admin, distribution, sync, legal)</li>
          <li>Advance tracking with recoupment progress</li>
          <li>Payment history and net balance</li>
        </ul>

        <SubHeading>CSV Import with AI Mapping</SubHeading>
        <p className="text-sm text-[#7A8580] mb-3">
          When uploading a CSV for a creator, the system uses AI to automatically map your CSV columns to the correct fields (title, ISRC, release date, etc.). You can review and adjust the mappings before importing. The system also provides fallback pattern matching if AI mapping is unavailable.
        </p>

        {/* ===== 6. CATALOG ===== */}
        <SectionHeading id="catalog">6. Catalog Management</SectionHeading>
        <p className="text-sm text-[#7A8580] mb-3">
          The Catalog page is the heart of your song management. It provides a spreadsheet-style view of all songs in your organization with powerful filtering and bulk operations.
        </p>

        <SubHeading>Catalog View</SubHeading>
        <p className="text-sm text-[#7A8580] mb-3">
          Songs are displayed in a table with columns for title, primary artist, ISRC, release date, health score, and status. The health score is shown as a color-coded badge:
        </p>
        <div className="flex gap-3 my-3 flex-wrap">
          <span className="px-3 py-1 rounded-full text-xs font-medium bg-green-100 text-green-700">80-100% Healthy</span>
          <span className="px-3 py-1 rounded-full text-xs font-medium bg-yellow-100 text-yellow-700">50-79% Needs Work</span>
          <span className="px-3 py-1 rounded-full text-xs font-medium bg-red-100 text-red-700">0-49% Critical</span>
        </div>
        <p className="text-sm text-[#7A8580] mb-3">
          Click any column header to sort the table by that field. Click again to reverse the sort direction. An arrow indicator shows the current sort direction.
        </p>

        <SubHeading>Filtering & Tabs</SubHeading>
        <p className="text-sm text-[#7A8580] mb-3">
          Use the tab bar to filter songs by status: <strong>All</strong>, <strong>Released</strong>, <strong>Unreleased</strong>, or <strong>Needs Attention</strong> (songs with low health scores). The search bar filters songs by title or artist name in real-time.
        </p>

        <SubHeading>Adding Songs</SubHeading>
        <p className="text-sm text-[#7A8580] mb-3">
          There are three ways to add songs to your catalog:
        </p>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 my-4">
          <FeatureCard title="Manual Entry" description="Click + Add Song to open the form. Fill in title, artist, ISRC, release date, and other metadata." />
          <FeatureCard title="CSV Upload" description="Click Upload CSV to bulk-import songs from a spreadsheet. The system uses AI to map your columns automatically." />
          <FeatureCard title="Spotify Import" description="Click Import from Spotify, paste a playlist URL, preview tracks, select which ones to import, and confirm." />
        </div>

        <SubHeading>Song Detail Modal</SubHeading>
        <p className="text-sm text-[#7A8580] mb-3">
          Click any song row to open its detail modal. The modal is organized into tabs:
        </p>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 my-4">
          <FeatureCard title="Details Tab" description="View and edit all song metadata including title, artist, ISRC, UPC, release date, genre, BPM, key, and more." />
          <FeatureCard title="Health Tab" description="Interactive checklist showing what metadata and actions are complete or missing. Check items off to improve the song's health score." />
          <FeatureCard title="Credits Tab" description="Manage songwriter, producer, and performer credits for the song. Add or remove credits and specify roles." />
          <FeatureCard title="DSP Links Tab" description="Add links to the song on streaming platforms (Spotify, Apple Music, YouTube, etc.) for easy reference." />
          <FeatureCard title="Contracts Tab" description="View and upload contract documents (PDF) associated with this song. Download or delete existing contracts." />
          <FeatureCard title="Rights & Splits Tab" description="View and manage rights splits for this song. See who owns what percentage of which rights type." />
        </div>

        <SubHeading>Direct Song Splits</SubHeading>
        <p className="text-[#7A8580] mb-3">
          You can add ownership splits directly to any song without creating a formal contract first. Navigate to a song's <strong>Rights & Splits</strong> tab and click <strong>Add Split</strong>.
        </p>
        <ul className="list-disc pl-5 text-[#7A8580] space-y-1 mb-3">
          <li>Select a rights holder from your roster or type an external contributor's name</li>
          <li>Choose the rights type (Publishing, Master, Performance, Mechanical, Distribution, Sync, or Other)</li>
          <li>Enter the share percentage — the system prevents totals exceeding 100% per rights type</li>
          <li>Optionally add notes for each split entry</li>
          <li>Remove splits at any time using the delete button</li>
        </ul>
        <Tip>Direct splits automatically create a lightweight "Split Sheet" contract behind the scenes, keeping your data organized and exportable.</Tip>

        <SubHeading>Split Sheet PDF Export</SubHeading>
        <p className="text-[#7A8580] mb-3">
          Once splits are defined for a song, a <strong>Split Sheet PDF</strong> button appears in the Rights & Splits tab. Click it to download a branded PDF document containing all ownership information, ready for signing. The PDF includes:
        </p>
        <ul className="list-disc pl-5 text-[#7A8580] space-y-1 mb-3">
          <li>Cadence branding and contract metadata</li>
          <li>Complete split breakdown by rights type with percentage totals</li>
          <li>Rights holder details (PRO affiliation, IPI number, publisher)</li>
          <li>Signature blocks for all parties</li>
        </ul>
        <Tip>You can also download split sheets from the Contracts page — use the download icon on any contract to choose publishing-only, master-only, or combined split sheets.</Tip>

        <SubHeading>Health Score System</SubHeading>
        <p className="text-sm text-[#7A8580] mb-3">
          Every song has a health score calculated from a weighted checklist. Each checklist item (e.g., "ISRC assigned", "Credits added", "Contract uploaded") has a weight, and the health score is the percentage of weighted items that are completed. Improving health scores ensures your catalog data is complete and ready for distribution and licensing.
        </p>

        <SubHeading>Bulk Operations</SubHeading>
        <p className="text-sm text-[#7A8580] mb-3">
          Select multiple songs using the checkboxes and use the bulk action toolbar to update metadata or assign credits across many songs at once.
        </p>

        <SubHeading>Spotify Import</SubHeading>
        <StepList steps={[
          'Click the "Import from Spotify" button on the Catalog page.',
          'Paste a Spotify playlist URL into the input field.',
          'Optionally select a creator to associate imported songs with.',
          'Click "Preview" to load the playlist tracks.',
          'Review the track list — duplicates already in your catalog are flagged.',
          'Select or deselect individual tracks using checkboxes.',
          'Click "Import Selected" to add the chosen tracks to your catalog.',
        ]} />

        {/* ===== 7. WORKS ===== */}
        <SectionHeading id="works">7. Works (Compositions)</SectionHeading>
        <p className="text-sm text-[#7A8580] mb-3">
          Works represent the underlying musical compositions, separate from their recorded versions (songs/tracks). A single work can have multiple recordings. This distinction is important for publishing rights management.
        </p>

        <SubHeading>Work Types</SubHeading>
        <p className="text-sm text-[#7A8580] mb-3">
          Each work has a type that indicates its nature:
        </p>
        <div className="flex gap-3 my-3 flex-wrap">
          <span className="px-3 py-1 rounded-full text-xs font-medium bg-purple-100 text-purple-700">DEMO — Song with lyrics and melodies</span>
          <span className="px-3 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-700">TRACK — Instrumental or beat</span>
        </div>
        <p className="text-sm text-[#7A8580] mb-3">
          Work types appear as color-coded badges in the works list. You can filter works by type using the filter controls on the Works page.
        </p>

        <SubHeading>Managing Works</SubHeading>
        <StepList steps={[
          'Navigate to the Works page from the sidebar.',
          'View all works in a searchable list with title, ISWC, type badge, and associated track count.',
          'Click + Add Work to create a new composition record.',
          'Fill in the work title, type (Demo or Track), ISWC (if available), alternative titles, and other metadata.',
          'Save the work, then link recordings (songs) and add credits.',
        ]} />

        <SubHeading>Work Detail Panel</SubHeading>
        <p className="text-sm text-[#7A8580] mb-3">
          Click any work to open its detail panel. From here you can:
        </p>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 my-4">
          <FeatureCard title="Edit Metadata" description="Update the work title, ISWC, alternative titles, and notes." />
          <FeatureCard title="Link Tracks" description="Associate song recordings with this composition. One work can have multiple recordings." />
          <FeatureCard title="Manage Credits" description="Add songwriter and composer credits specific to the composition." />
          <FeatureCard title="Rights & Splits" description="Define publishing rights splits for the composition." />
        </div>

        {/* ===== 8. RELEASES ===== */}
        <SectionHeading id="releases">8. Releases</SectionHeading>
        <p className="text-sm text-[#7A8580] mb-3">
          Releases represent albums, EPs, singles, compilations, or mixtapes — the packages in which recordings are distributed to the public.
        </p>

        <SubHeading>Release Types</SubHeading>
        <div className="flex gap-3 my-3 flex-wrap">
          <span className="px-3 py-1 rounded-full text-xs font-medium bg-[#EEF1EC] text-[#3D4A44]">Single</span>
          <span className="px-3 py-1 rounded-full text-xs font-medium bg-[#EEF1EC] text-[#3D4A44]">EP</span>
          <span className="px-3 py-1 rounded-full text-xs font-medium bg-[#EEF1EC] text-[#3D4A44]">Album</span>
          <span className="px-3 py-1 rounded-full text-xs font-medium bg-[#EEF1EC] text-[#3D4A44]">Compilation</span>
          <span className="px-3 py-1 rounded-full text-xs font-medium bg-[#EEF1EC] text-[#3D4A44]">Mixtape</span>
        </div>

        <SubHeading>Release Status Workflow</SubHeading>
        <p className="text-sm text-[#7A8580] mb-3">
          Each release moves through a defined workflow with validation gates:
        </p>
        <div className="flex items-center gap-2 my-4 flex-wrap">
          <span className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-gray-100 text-gray-700">Draft</span>
          <span className="text-[#7A8580]">→</span>
          <span className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-blue-100 text-blue-700">Ready</span>
          <span className="text-[#7A8580]">→</span>
          <span className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-amber-100 text-amber-700">Submitted</span>
          <span className="text-[#7A8580]">→</span>
          <span className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-green-100 text-green-700">Released</span>
        </div>
        <Tip>A release can only move to "Submitted" status once it passes all distribution readiness checks. This ensures your metadata is complete before delivery.</Tip>

        <SubHeading>Distribution Readiness</SubHeading>
        <p className="text-sm text-[#7A8580] mb-3">
          The Release Builder includes a comprehensive readiness checker organized into categories:
        </p>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 my-4">
          <FeatureCard title="Identifiers" description="UPC/EAN assigned, all tracks have ISRCs." />
          <FeatureCard title="Metadata" description="Title, artist, genre, release date, and cover art present." />
          <FeatureCard title="Legal" description="All required contracts and licenses in place." />
          <FeatureCard title="Credits" description="All tracks have proper songwriter, producer, and performer credits." />
        </div>

        <SubHeading>Metadata Export</SubHeading>
        <p className="text-sm text-[#7A8580] mb-3">
          Once ready, export your release metadata for submission to distribution partners. Three export formats are available in the Release Builder:
        </p>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 my-4">
          <FeatureCard title="CSV Export" description="Spreadsheet-compatible format for easy editing and distribution system import." />
          <FeatureCard title="JSON Export" description="Structured data format for automated distribution pipelines and API integrations." />
          <FeatureCard title="PDF Export" description="Branded PDF document with full release metadata, track listing with audio links, lyrics, credits, and readiness summary." />
        </div>

        {/* ===== 9. CONTRACTS ===== */}
        <SectionHeading id="contracts">9. Contracts & Rights</SectionHeading>
        <p className="text-sm text-[#7A8580] mb-3">
          The Contracts module provides comprehensive deal management including party tracking, asset linking, territory, advance management, and rights splits.
        </p>

        <SubHeading>Creating a Contract</SubHeading>
        <StepList steps={[
          'Navigate to the Contracts page from the sidebar.',
          'Click + New Contract to create a new deal.',
          'Fill in contract details: title, type, status, effective date, expiry date, territory, and notes.',
          'Add contract parties — specify each party\'s name, role (Licensor, Licensee, Publisher, etc.), and contact info.',
          'Link assets (songs and/or works) to the contract.',
          'Save the contract.',
        ]} />

        <p className="text-[#7A8580] mb-3">
          <strong>Split Sheet Contracts:</strong> When you add splits directly to a song (from the song detail modal), the system automatically creates a SPLIT_SHEET type contract. These appear in your contracts list and can be managed like any other contract.
        </p>

        <SubHeading>Rights Splits</SubHeading>
        <p className="text-sm text-[#7A8580] mb-3">
          For each asset linked to a contract, you can define rights splits:
        </p>
        <StepList steps={[
          'Open a contract and navigate to its assets.',
          'For each asset, click "Manage Splits" to define ownership percentages.',
          'Specify the rights type (Master, Publishing, Mechanical, Performance, Sync, etc.).',
          'Enter the rights holder name and their percentage share.',
          'The system validates that splits for each rights type do not exceed 100%.',
        ]} />
        <Tip>You can also view and manage rights splits from the song detail modal's "Rights & Splits" tab for a song-centric view.</Tip>

        <SubHeading>Contract Documents</SubHeading>
        <p className="text-sm text-[#7A8580] mb-3">
          Upload PDF contract documents to any song via the song detail modal's Contracts tab. These files are securely stored and accessible only to your organization members.
        </p>

        <SubHeading>Advances</SubHeading>
        <p className="text-sm text-[#7A8580] mb-3">
          The Advances tab on each contract detail page lets you create and manage advances tied to that deal. Advances are the basis for automatic recoupment during royalty processing.
        </p>
        <StepList steps={[
          'Open a contract and navigate to the "Advances" tab.',
          'Click "Add Advance" to create a new advance record.',
          'Enter the advance name, date, principal amount, and currency.',
          'Select a recoupment pool: Master (applies to master recordings revenue), Publishing (applies to composition revenue), Both (applies to all revenue types), or Custom.',
          'Set the recoupment priority (1 = highest). When multiple advances exist, lower-priority-number advances are recouped first.',
          'Optionally enable cross-collateralization to allow recoupment across multiple assets under the contract.',
          'Set optional start and end dates for the recoupment window.',
          'The system tracks outstanding balances automatically as statements are processed.',
        ]} />
        <Tip>Always create advances at the contract level rather than relying on negative statement lines. This gives you precise control over recoupment pools, priority ordering, and cross-collateralization rules.</Tip>

        {/* ===== 10. ACTION ITEMS ===== */}
        <SectionHeading id="actions">10. Action Items</SectionHeading>
        <p className="text-sm text-[#7A8580] mb-3">
          The Action Items page serves as your unified task inbox across all modules. It consolidates tasks from songs, works, releases, contracts, placements, and royalties into a single manageable view.
        </p>

        <SubHeading>Task Properties</SubHeading>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 my-4">
          <FeatureCard title="Priority Levels" description="Critical (red), High (orange), Medium (yellow), Low (green). Use these to triage your workload." />
          <FeatureCard title="Due Dates" description="Set deadlines for tasks. Overdue items are highlighted with a warning indicator." />
          <FeatureCard title="Entity Links" description="Each task links to a specific entity (song, work, release, contract, placement). Click the link to navigate directly." />
          <FeatureCard title="Reminders" description="Set reminder dates for important tasks that need follow-up." />
        </div>

        <SubHeading>Auto-Generated Tasks</SubHeading>
        <p className="text-sm text-[#7A8580] mb-3">
          The system automatically creates tasks for:
        </p>
        <StepList steps={[
          'Contracts expiring within 30 days.',
          'Releases with incomplete distribution readiness.',
          'Unmatched royalty transactions that need reconciliation.',
          'Placements that haven\'t been updated in 14+ days since pitch.',
          'Placements that need contract documentation.',
          'Royalty statements with unmatched lines that need review in the Matching Console.',
          'Royalty statements that are ready for processing but have not been processed.',
          'Reprocessed statements that need review to verify corrected allocations.',
        ]} />

        <SubHeading>Filtering & Organization</SubHeading>
        <p className="text-sm text-[#7A8580] mb-3">
          Filter tasks by entity type (songs, works, releases, contracts, placements, royalties) using the filter buttons. The module breakdown widget shows how many tasks exist in each category, helping you prioritize your workflow.
        </p>

        <SubHeading>Reports & Email</SubHeading>
        <p className="text-sm text-[#7A8580] mb-3">
          The Task Inbox header includes reporting tools to share and export action items:
        </p>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 my-4">
          <FeatureCard title="Download Report" description="Downloads a branded, printable HTML report of all action items. Open the file in a browser and use Print > Save as PDF to create a PDF. Available at all times." />
          <FeatureCard title="Email Report" description="Appears when filtering by a specific creator. Sends that creator's action items as a digest email to your own email address for reference or forwarding." />
          <FeatureCard title="Push to Creator" description="Appears when filtering by a creator who has an email address on file. Sends the action items digest directly to the creator's email so they can see what needs attention." />
        </div>
        <StepList steps={[
          'To download a report: Click "Download Report" in the header. The file downloads as HTML — open it and print to PDF.',
          'To email yourself a creator report: Filter by a creator using the dropdown, then click "Email Report".',
          'To send directly to a creator: Filter by a creator who has an email on file, then click "Push to Creator".',
        ]} />
        <Tip>Use the creator filter dropdown to focus your report or email on a single creator. Without a filter, the Download Report button exports all action items.</Tip>

        {/* ===== 11. ROYALTIES ===== */}
        <SectionHeading id="royalties">11. Royalties</SectionHeading>
        <p className="text-sm text-[#7A8580] mb-3">
          The Royalties module is a full financial engine for managing statement ingestion, catalog matching, royalty calculations, advance recoupment, ledger accounting, and payment tracking. It includes a professional processing pipeline with an audit-safe ledger.
        </p>

        <SubHeading>Royalty Dashboard</SubHeading>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 my-4">
          <FeatureCard title="Revenue Charts" description="Visual breakdown of royalty revenue over time with trend analysis." />
          <FeatureCard title="Top Earning Tracks" description="Ranked list of your highest-revenue songs from royalty statements." />
          <FeatureCard title="Processing Inbox" description="Quick overview of statements needing attention: mapping required, matching in progress, ready to process, and review required." />
          <FeatureCard title="Earnings Breakdown" description="View earnings by rights holder, contract, or individual track." />
        </div>

        <SubHeading>Processing Inbox</SubHeading>
        <p className="text-sm text-[#7A8580] mb-3">
          The Processing tab provides a centralized inbox for managing royalty statements through the processing pipeline. Status cards show how many statements are at each stage, letting you quickly identify what needs attention.
        </p>

        <SubHeading>Statement Upload & Mapping</SubHeading>
        <StepList steps={[
          'Navigate to Royalties and click the "Processing" tab.',
          'Use the Enhanced Upload section to import a royalty statement (CSV or Excel).',
          'Enter the provider name, source type (PRO, DSP, Distributor, etc.), statement period, and currency.',
          'The system auto-detects the PRO source and maps columns accordingly. If needed, you can manually adjust column mapping.',
          'Upon upload, statement lines are created and auto-matching begins immediately.',
          'The statement status will update to show how many lines were matched automatically.',
        ]} />
        <Tip>The system supports statements from all major PROs (BMI, ASCAP, SESAC, SoundExchange, SOCAN, PRS) and DSP distributors. Column mapping happens automatically for recognized formats.</Tip>

        <SubHeading>Royalty Statements</SubHeading>
        <p className="text-sm text-[#7A8580] mb-3">
          Each uploaded statement goes through a lifecycle of statuses:
        </p>
        <div className="flex items-center gap-1.5 my-4 flex-wrap text-xs">
          <span className="px-2.5 py-1.5 rounded-lg font-semibold bg-gray-100 text-gray-700">Uploaded</span>
          <span className="text-[#7A8580]">{'→'}</span>
          <span className="px-2.5 py-1.5 rounded-lg font-semibold bg-amber-100 text-amber-700">Mapping Required</span>
          <span className="text-[#7A8580]">{'→'}</span>
          <span className="px-2.5 py-1.5 rounded-lg font-semibold bg-blue-100 text-blue-700">Matching</span>
          <span className="text-[#7A8580]">{'→'}</span>
          <span className="px-2.5 py-1.5 rounded-lg font-semibold bg-teal-100 text-teal-700">Ready to Process</span>
          <span className="text-[#7A8580]">{'→'}</span>
          <span className="px-2.5 py-1.5 rounded-lg font-semibold bg-green-100 text-green-700">Processed</span>
          <span className="text-[#7A8580]">{'→'}</span>
          <span className="px-2.5 py-1.5 rounded-lg font-semibold bg-purple-100 text-purple-700">Locked</span>
        </div>

        <SubHeading>Statement Detail Page</SubHeading>
        <p className="text-sm text-[#7A8580] mb-3">
          Click any statement to open its detail page with the following tabs:
        </p>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 my-4">
          <FeatureCard title="Overview" description="Summary metrics, matching progress bar, and status breakdown showing how many lines are matched, unmatched, or need review." />
          <FeatureCard title="Lines" description="Full table of statement lines with filtering by match status, search, and pagination. Each line shows the raw track/artist data, amounts, and match information." />
          <FeatureCard title="Matching" description="The Matching Console — a two-pane interface for reviewing and confirming matches between statement lines and your catalog." />
          <FeatureCard title="Allocation Preview" description="Preview of how earnings will be distributed among payees before processing. Shows earnings, fees, recoupment deductions, and net payable per payee." />
          <FeatureCard title="Run History" description="Log of all processing runs for this statement, with version numbers, status, timing, and the option to reprocess." />
          <FeatureCard title="Exports" description="Download unmatched lines, allocation previews, or payables reports as CSV files." />
        </div>

        <SubHeading>Matching Console</SubHeading>
        <p className="text-sm text-[#7A8580] mb-3">
          The Matching Console is where you review and confirm how statement lines connect to your catalog:
        </p>
        <StepList steps={[
          'The left pane shows a queue of unmatched and review-required lines.',
          'Select a line to see its details and suggested catalog matches on the right.',
          'For each suggestion, you can Confirm (accept the match), Reject (remove the suggestion), or Ignore (skip the line).',
          'Use the search field to find songs/works/releases manually if no suggestions are provided.',
          'Use "Bulk Confirm High-Confidence" to accept all auto-matched lines above a configurable confidence threshold (e.g., 85%).',
        ]} />
        <Tip>Always review matches with confidence below 85% manually. Auto-matched lines with high confidence (85%+) are generally safe to bulk-confirm.</Tip>

        <SubHeading>Processing: What Happens When You Click "Process Statement"</SubHeading>
        <p className="text-sm text-[#7A8580] mb-3">
          When you process a statement, the system performs these steps for each matched line:
        </p>
        <StepList steps={[
          'Identifies the song, work, and/or release from the match.',
          'Finds applicable contracts and rights splits for the revenue type.',
          'Creates EARNING ledger entries for each payee based on their split percentage.',
          'Checks for active advances (from the Advances section on contracts) and applies RECOUPMENT, deducting from outstanding balances in priority order.',
          'Creates PAYABLE_CREATED entries for the remaining amount after recoupment.',
          'Updates the statement status to PROCESSED and eventually LOCKED.',
        ]} />
        <Tip>Use the Allocation Preview tab to sanity-check the distribution before processing. This shows exactly what each payee will receive.</Tip>

        <SubHeading>Locked Statements</SubHeading>
        <p className="text-sm text-[#7A8580] mb-3">
          Once a statement is processed and locked, you cannot edit individual lines or matches. If corrections are needed, use the Reprocess function, which creates reversal entries and re-runs the processing engine. This ensures a complete audit trail.
        </p>

        <SubHeading>Ledger Concepts</SubHeading>
        <p className="text-sm text-[#7A8580] mb-3">
          The ledger is the accounting backbone. Every financial event creates a ledger entry with one of these types:
        </p>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 my-4">
          <FeatureCard title="EARNING" description="Revenue allocated to a payee from a statement line based on their contract split." />
          <FeatureCard title="FEE" description="Management, administration, or distribution fees deducted from earnings." />
          <FeatureCard title="RECOUPMENT_APPLIED" description="Amount deducted from earnings to recover an outstanding advance." />
          <FeatureCard title="PAYABLE_CREATED" description="Net amount owed to a payee after fees and recoupment." />
          <FeatureCard title="PAYMENT" description="Records an actual payment made to a payee through a payout batch." />
          <FeatureCard title="REVERSAL" description="Negates a prior entry when a statement is reprocessed. Preserves audit trail." />
        </div>

        <SubHeading>Payables</SubHeading>
        <p className="text-sm text-[#7A8580] mb-3">
          The Payables tab shows all payees with outstanding balances. For each payee, you can see their payable balance (sum of PAYABLE_CREATED minus PAYMENT entries), outstanding advances, and the last statement they appeared in. Use the "View Ledger" button to drill down into individual ledger entries, or "Add to Payout" to include them in a payout batch.
        </p>

        <SubHeading>Payout Batches</SubHeading>
        <StepList steps={[
          'Create a payout batch from the Payables tab.',
          'Add payees and amounts to the batch.',
          'Review and approve the batch.',
          'Mark the batch as Paid — this automatically creates PAYMENT ledger entries for each item.',
        ]} />

        <SubHeading>Advances & Recoupment</SubHeading>
        <p className="text-sm text-[#7A8580] mb-3">
          Advances are upfront payments to creators that are recovered from future earnings. The system supports:
        </p>
        <ul className="list-disc pl-5 text-[#7A8580] space-y-1 mb-3">
          <li><strong>Recoupment Pools:</strong> Master (applies to master recording revenue), Publishing (composition revenue), Both (all revenue), or Custom.</li>
          <li><strong>Priority Ordering:</strong> When multiple advances exist, lower priority numbers are recouped first.</li>
          <li><strong>Cross-Collateralization:</strong> When enabled, revenue from any asset under the contract can recoup the advance, not just the specific asset.</li>
          <li><strong>Progress Tracking:</strong> Visual progress bars show how much of each advance has been recouped.</li>
        </ul>

        <SubHeading>Reprocessing (Audit-Safe Corrections)</SubHeading>
        <p className="text-sm text-[#7A8580] mb-3">
          If you need to correct a processed statement (e.g., after fixing matches or updating contract splits), use the Reprocess function:
        </p>
        <StepList steps={[
          'Go to the statement\'s Run History tab.',
          'Click "Reprocess" and provide a reason for the correction.',
          'The system creates REVERSAL entries that negate all prior ledger entries from the last run.',
          'Advance balances are restored to their pre-processing state.',
          'The processing engine runs again with the current data, creating new entries.',
          'Both the original and corrected entries remain in the ledger for a complete audit trail.',
        ]} />
        <Tip>Reprocessing never deletes data. Old entries are reversed (not removed), ensuring you always have a full history of what happened.</Tip>

        <SubHeading>Creator Accounting</SubHeading>
        <p className="text-sm text-[#7A8580] mb-3">
          Each creator's profile includes an enhanced Accounting tab with three sub-sections:
        </p>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 my-4">
          <FeatureCard title="Summary" description="Overview of total royalties, outstanding advances, and net payable amounts." />
          <FeatureCard title="Ledger" description="Full filterable ledger of all entries for this creator, with drill-down by statement, song, or contract." />
          <FeatureCard title="Recoupment" description="List of advances with outstanding balances and visual progress bars showing recoupment status." />
        </div>

        <SubHeading>Fees & Advances (Legacy)</SubHeading>
        <p className="text-[#7A8580] mb-3">
          The <strong>Fees & Advances</strong> tab in the Royalties page provides organization-wide financial tracking:
        </p>
        <ul className="list-disc pl-5 text-[#7A8580] space-y-1 mb-3">
          <li><strong>Fees:</strong> Track management, administration, distribution, sync, and legal fees per creator.</li>
          <li><strong>Advances:</strong> Record advances with amounts, dates, and recoupment tracking.</li>
          <li>View recoupment progress bars showing how much of each advance has been recovered.</li>
          <li>Filter by creator to see individual financial summaries.</li>
        </ul>

        <SubHeading>CSV Exports</SubHeading>
        <p className="text-sm text-[#7A8580] mb-3">
          From any statement detail page, you can export:
        </p>
        <ul className="list-disc pl-5 text-[#7A8580] space-y-1 mb-3">
          <li><strong>Unmatched Lines:</strong> CSV of lines that could not be matched to your catalog.</li>
          <li><strong>Allocation Preview:</strong> CSV showing the projected distribution before processing.</li>
          <li><strong>Payables Report:</strong> CSV of payable amounts per payee after processing.</li>
        </ul>

        {/* ===== 12. PLACEMENTS ===== */}
        <SectionHeading id="placements">12. Placements</SectionHeading>
        <p className="text-sm text-[#7A8580] mb-3">
          The Placements module tracks sync licensing opportunities from initial pitch through to payment. It provides a visual pipeline for managing your placement workflow.
        </p>

        <SubHeading>Placement Pipeline</SubHeading>
        <div className="flex items-center gap-1.5 my-4 flex-wrap text-xs">
          <span className="px-2.5 py-1.5 rounded-lg font-semibold bg-blue-100 text-blue-700">Pitched</span>
          <span className="text-[#7A8580]">→</span>
          <span className="px-2.5 py-1.5 rounded-lg font-semibold bg-purple-100 text-purple-700">In Review</span>
          <span className="text-[#7A8580]">→</span>
          <span className="px-2.5 py-1.5 rounded-lg font-semibold bg-amber-100 text-amber-700">In Negotiation</span>
          <span className="text-[#7A8580]">→</span>
          <span className="px-2.5 py-1.5 rounded-lg font-semibold bg-teal-100 text-teal-700">Secured</span>
          <span className="text-[#7A8580]">→</span>
          <span className="px-2.5 py-1.5 rounded-lg font-semibold bg-indigo-100 text-indigo-700">Delivered</span>
          <span className="text-[#7A8580]">→</span>
          <span className="px-2.5 py-1.5 rounded-lg font-semibold bg-emerald-100 text-emerald-700">Aired</span>
          <span className="text-[#7A8580]">→</span>
          <span className="px-2.5 py-1.5 rounded-lg font-semibold bg-green-100 text-green-700">Paid</span>
        </div>

        <SubHeading>Managing Placements</SubHeading>
        <StepList steps={[
          'Click + New Placement to create a placement entry.',
          'Enter details: song, client/company, project name, placement type, license fee, currency.',
          'Set the initial status (typically "Pitched").',
          'As the opportunity progresses, update the status through the pipeline.',
          'Click any placement to view its detail panel with full history and status transitions.',
          'Link contracts to placements for complete documentation.',
        ]} />

        <SubHeading>Summary Cards</SubHeading>
        <p className="text-sm text-[#7A8580] mb-3">
          The top of the Placements page shows summary cards: total placements, total pipeline value (sum of all active license fees), total paid, and number of active pitches. Use the status filter buttons to view placements at specific pipeline stages.
        </p>

        {/* ===== 13. SYNC REPORTS ===== */}
        <SectionHeading id="sync-reports">13. Sync Reports</SectionHeading>
        <p className="text-sm text-[#7A8580] mb-3">
          The Sync Reports module generates customizable reports for your sync placement activity. Use it to create professional summaries for clients, internal reviews, or stakeholder updates.
        </p>

        <SubHeading>Creating a Sync Report</SubHeading>
        <StepList steps={[
          'Navigate to the Sync Reports page from the sidebar.',
          'Use the filter controls to narrow placements by client, status, and date range.',
          'Preview the filtered results to ensure the report captures the right data.',
          'Choose your export format: PDF for branded, printable reports or CSV for spreadsheet analysis.',
          'Click the export button to download your report.',
        ]} />

        <SubHeading>Report Contents</SubHeading>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 my-4">
          <FeatureCard title="Client Filtering" description="Filter placements by specific clients to create client-facing activity summaries." />
          <FeatureCard title="Status Filtering" description="Include only placements at specific pipeline stages (e.g., Secured and Paid only)." />
          <FeatureCard title="Date Range" description="Narrow the report to a specific time period for quarterly or annual reviews." />
          <FeatureCard title="Branded PDF" description="PDF exports include your organization branding, placement details, and financial summaries." />
        </div>
        <Tip>Create monthly or quarterly sync reports for each client to demonstrate your pitching activity and success rate. Filter by client and date range for targeted summaries.</Tip>

        {/* ===== 14. BRIEF BUILDER ===== */}
        <SectionHeading id="brief-builder">14. Brief Builder</SectionHeading>
        <p className="text-sm text-[#7A8580] mb-3">
          The Brief Builder is an AI-powered tool for matching songs in your catalog to sync briefs. Describe what you're looking for in natural language, add optional structured filters, and the system returns ranked song recommendations.
        </p>

        <SubHeading>How to Use Brief Builder</SubHeading>
        <StepList steps={[
          'Navigate to the Brief Builder page from the sidebar.',
          'Enter a free-text description of the sync brief (e.g., "upbeat indie track with female vocals for a car commercial, summer vibes").',
          'Optionally add structured filters: BPM range, key, mood tags, texture tags, vocal presence, stems availability.',
          'Click Search to run the AI matching engine.',
          'Review the ranked results — each song shows a match score and reasons why it was selected.',
          'Click any result to view the full song details or add it to a pitch list.',
        ]} />

        <SubHeading>Matching Criteria</SubHeading>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 my-4">
          <FeatureCard title="Natural Language" description="Describe the vibe, mood, or use case in plain English. The AI parses your description into search parameters." />
          <FeatureCard title="BPM Range" description="Set minimum and maximum BPM to match tempo requirements." />
          <FeatureCard title="Key Filter" description="Specify a musical key to find songs in compatible keys." />
          <FeatureCard title="Mood & Texture Tags" description="Select from AI-generated tags to filter by emotional qualities and sonic characteristics." />
        </div>
        <Tip>The Brief Builder works best when your catalog has been analyzed with the Audio Analysis tool. Songs with BPM, key, mood, and texture data produce more accurate matches.</Tip>

        {/* ===== 15. CREATIVE DIRECTORY ===== */}
        <SectionHeading id="directory">15. Creative Directory</SectionHeading>
        <p className="text-sm text-[#7A8580] mb-3">
          The Creative Directory is a contact management system for industry collaborators — producers, engineers, mixers, session musicians, A&R contacts, and other professionals you work with regularly.
        </p>

        <SubHeading>Managing Contacts</SubHeading>
        <StepList steps={[
          'Navigate to the Directory page from the sidebar.',
          'Click + Add Contact to create a new directory entry.',
          'Fill in the contact details: name, role/title, company, email, phone, and notes.',
          'Save the contact to your directory.',
          'Use the search bar or role filter to find contacts quickly.',
        ]} />

        <SubHeading>Directory Features</SubHeading>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 my-4">
          <FeatureCard title="Search & Filter" description="Search contacts by name and filter by role for quick lookups." />
          <FeatureCard title="CRUD Operations" description="Create, view, edit, and delete directory entries as needed." />
          <FeatureCard title="PDF Export" description="Export your full directory or filtered contacts as a branded PDF document." />
          <FeatureCard title="Organization Scoped" description="Directory contacts are private to your organization." />
        </div>
        <Tip>Use the Directory to keep track of all collaborators you might need for sync placements, recording sessions, or contract negotiations. It's separate from the Creator Roster, which focuses on your signed artists and writers.</Tip>

        {/* ===== 16. REGISTRATION REPORTS ===== */}
        <SectionHeading id="registration-reports">16. Registration Reports</SectionHeading>
        <p className="text-sm text-[#7A8580] mb-3">
          The Registration Reports module helps you manage PRO (Performing Rights Organization) registrations for your songs and works. Track which assets are registered, generate branded reports, and email them directly to your admin or PRO contacts.
        </p>

        <SubHeading>Registration Workflow</SubHeading>
        <StepList steps={[
          'Navigate to Registration Reports from the sidebar.',
          'View your songs and works organized by creator, with their PRO registration status.',
          'Use the Outstanding/Registered filter tabs to focus on items needing registration.',
          'Select items using checkboxes to aggregate them into a report.',
          'Click Generate Report to create a branded PDF of the selected items.',
          'Download the PDF, export as CSV, or email directly to your admin via the built-in email feature.',
        ]} />

        <SubHeading>Report Features</SubHeading>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 my-4">
          <FeatureCard title="Creator Grouping" description="Items are grouped by creator for organized reporting to PROs." />
          <FeatureCard title="Outstanding Filter" description="Quickly find all songs and works that haven't been registered yet." />
          <FeatureCard title="PDF Reports" description="Branded PDF documents listing selected items with creator info, song details, and PRO data." />
          <FeatureCard title="Email to Admin" description="Send the generated PDF report directly to an admin email address via the built-in email feature." />
          <FeatureCard title="CSV Export" description="Download registration data as a CSV for bulk processing or record keeping." />
          <FeatureCard title="Registration Tracking" description="Mark songs and works as registered once submitted to your PRO." />
        </div>
        <Tip>Run a monthly registration check using the Outstanding filter to catch any new songs or works that haven't been submitted to your PRO yet.</Tip>

        {/* ===== 17. CLOUD STORAGE INTEGRATION ===== */}
        <SectionHeading id="cloud-storage">17. Cloud Storage Integration</SectionHeading>
        <p className="text-sm text-[#7A8580] mb-3">
          Cadence integrates with Dropbox and Google Drive to link audio files to your catalog without hosting files locally. This enables AI audio analysis and file management directly from your existing cloud storage.
        </p>

        <SubHeading>Connecting Dropbox</SubHeading>
        <StepList steps={[
          'Go to Settings and select the Integrations tab.',
          'In the Dropbox section, click Connect.',
          'You will be redirected to Dropbox to authorize the app. Grant all requested permissions.',
          'After authorization, paste the auth code back into the app to complete the connection.',
          'Once connected, you can browse your Dropbox folders and select a default folder.',
        ]} />

        <SubHeading>Dropbox App Permissions</SubHeading>
        <p className="text-sm text-[#7A8580] mb-3">
          For folder browsing and file access to work, the Dropbox app must have the following scopes enabled in the Dropbox Developer Console:
        </p>
        <ul className="list-disc pl-5 text-[#7A8580] space-y-1 mb-3">
          <li><strong>files.metadata.read</strong> — Required to browse and list files and folders</li>
          <li><strong>files.content.read</strong> — Required to download files for AI audio analysis</li>
          <li><strong>account_info.read</strong> — Required to display the connected account name</li>
        </ul>
        <Tip>If you see an authentication error after connecting Dropbox, check that the required scopes are enabled in the Dropbox App Console (Permissions tab). After changing permissions, disconnect and reconnect Dropbox in Settings to get a fresh token with the updated scopes.</Tip>

        <SubHeading>Browsing & Folder Selection</SubHeading>
        <p className="text-sm text-[#7A8580] mb-3">
          Once connected, use the folder picker to browse your cloud storage and select a default folder. The folder picker provides:
        </p>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 my-4">
          <FeatureCard title="Folder Navigation" description="Browse through your folder structure with breadcrumb navigation and back buttons." />
          <FeatureCard title="Default Folder" description="Set a default folder that the system uses as the starting point for file scanning." />
          <FeatureCard title="Test Connection" description="Verify your cloud storage connection is working with the Test Connection button." />
          <FeatureCard title="Disconnect" description="Remove the connection at any time from the Integrations tab in Settings." />
        </div>

        <SubHeading>Google Drive</SubHeading>
        <p className="text-sm text-[#7A8580] mb-3">
          Google Drive integration follows the same connection flow. Once connected, the folder picker uses Google Drive's folder ID system for navigation, with a visual breadcrumb trail showing your current path.
        </p>

        {/* ===== 18. STORAGE SCAN ===== */}
        <SectionHeading id="storage-scan">18. Storage Scan</SectionHeading>
        <p className="text-sm text-[#7A8580] mb-3">
          The Storage Scan module connects individual creators to specific folders in your cloud storage, then uses AI to scan files, match them to catalog entries, and link audio files to songs automatically.
        </p>

        <SubHeading>Per-Creator Storage Linking</SubHeading>
        <StepList steps={[
          'Navigate to the Storage Scan page from the sidebar.',
          'Select a creator from your roster.',
          'Use the folder picker to browse and select a cloud storage folder for that creator.',
          'The folder is linked to the creator — this tells the system where to find their audio files.',
        ]} />

        <SubHeading>AI-Powered File Scanning</SubHeading>
        <p className="text-sm text-[#7A8580] mb-3">
          Once a folder is linked, trigger a scan to analyze the files:
        </p>
        <StepList steps={[
          'Click "Scan" on a creator\'s linked folder to start the AI scanning process.',
          'The system recursively scans the folder for audio files.',
          'AI-powered fuzzy matching compares filenames against your catalog entries.',
          'Each match is assigned a confidence level: HIGH (85%+), MEDIUM (60-84%), LOW (40-59%), or NONE (below 40%).',
          'Review the scan results in the review workflow.',
        ]} />

        <SubHeading>Review Workflow</SubHeading>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 my-4">
          <FeatureCard title="Approve" description="Accept a match to link the audio file to the catalog song." />
          <FeatureCard title="Reject" description="Dismiss incorrect matches that don't belong." />
          <FeatureCard title="Reassign" description="Manually assign a file to a different song if the AI match was close but wrong." />
          <FeatureCard title="Bulk Approve" description="Accept all high-confidence matches at once to speed up the review process." />
        </div>

        <SubHeading>Scheduled Scans</SubHeading>
        <p className="text-sm text-[#7A8580] mb-3">
          Set up automatic recurring scans per creator folder link. Choose a frequency (daily, weekly, etc.) and the system will scan for new files on schedule, automatically flagging new matches for your review.
        </p>
        <Tip>Start by scanning your most active creators' folders first. Use Bulk Approve for high-confidence matches, then manually review medium and low confidence results.</Tip>

        {/* ===== 19. AUDIO ANALYSIS & TAGGING ===== */}
        <SectionHeading id="audio-analysis">19. Audio Analysis & Tagging</SectionHeading>
        <p className="text-sm text-[#7A8580] mb-3">
          The Audio Analysis system uses AI to analyze your linked audio files and generate detailed metadata tags. This enriches your catalog with searchable attributes that power the Brief Builder and catalog filtering.
        </p>

        <SubHeading>What Gets Analyzed</SubHeading>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 my-4">
          <FeatureCard title="BPM" description="Beats per minute — the tempo of the song." />
          <FeatureCard title="Key" description="The musical key of the song (e.g., C Major, A Minor)." />
          <FeatureCard title="Loudness" description="Overall loudness level of the audio." />
          <FeatureCard title="Mood Tags" description="Emotional qualities like 'uplifting', 'melancholic', 'aggressive', 'dreamy'." />
          <FeatureCard title="Texture Tags" description="Sonic characteristics like 'atmospheric', 'gritty', 'lush', 'sparse'." />
          <FeatureCard title="Sync Tags" description="Use-case descriptors like 'cinematic', 'commercial-friendly', 'trailer', 'underscore'." />
          <FeatureCard title="Genre Tags" description="Genre classifications derived from audio characteristics." />
        </div>

        <SubHeading>Running Analysis</SubHeading>
        <StepList steps={[
          'Ensure the song has an audio file linked via cloud storage.',
          'Click the Analyze button on a song to run AI analysis.',
          'The analysis runs in the background — results typically appear within a few seconds.',
          'View the generated tags in the song detail modal.',
          'Use Bulk Analyze to process multiple songs at once.',
        ]} />

        <SubHeading>Tag Management</SubHeading>
        <p className="text-sm text-[#7A8580] mb-3">
          AI-generated tags include confidence scores. You can also manually add, edit, or override tags. Tag types include MOOD, TEXTURE, SYNC, GENRE, and USER (manually added). Tags power the catalog's audio filters and the Brief Builder's matching engine.
        </p>
        <Tip>Run audio analysis on your entire catalog to unlock the full power of the Brief Builder. Songs with complete audio metadata produce significantly better match results for sync briefs.</Tip>

        {/* ===== 20. REPORTS ===== */}
        <SectionHeading id="reports">20. Reports & Analytics</SectionHeading>
        <p className="text-sm text-[#7A8580] mb-3">
          The Reports page provides comprehensive analytics across your entire catalog through a tabbed dashboard with interactive visualizations.
        </p>

        <SubHeading>Report Tabs</SubHeading>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 my-4">
          <FeatureCard title="Overview" description="High-level summary statistics including total songs, creators, average health score, and key metrics." />
          <FeatureCard title="Catalog Health" description="Distribution of health scores across your catalog with trend charts showing improvement over time." />
          <FeatureCard title="Revenue" description="Revenue analysis with area charts, territory breakdowns, and growth rate indicators." />
          <FeatureCard title="Creators" description="Creator performance rankings, contribution analysis, and activity metrics." />
          <FeatureCard title="Placements" description="Placement pipeline analysis with funnel views, conversion rates, and revenue by placement type." />
          <FeatureCard title="Rights Coverage" description="Coverage progress bars showing what percentage of your catalog has complete rights documentation, gap analysis, and top earners." />
        </div>

        <SubHeading>Chart Types</SubHeading>
        <p className="text-sm text-[#7A8580] mb-3">
          Reports use a variety of visualizations including area charts, pie charts, bar charts, line charts, funnel views, progress bars, and data tables. All charts are interactive — hover for details and tooltips.
        </p>

        {/* ===== 21. VALUATION ===== */}
        <SectionHeading id="valuation">21. Catalog Valuation</SectionHeading>
        <p className="text-sm text-[#7A8580] mb-3">
          The Catalog Valuation page provides both traditional valuation estimates and an institutional-grade Underwriting Engine powered by your ingested royalty statement data. It offers actionable insights for business planning, investment discussions, and catalog transactions.
        </p>

        <SubHeading>Traditional Valuation Methodologies</SubHeading>
        <p className="text-sm text-[#7A8580] mb-3">
          Before running an underwriting analysis, the page displays catalog value estimates using four established methodologies:
        </p>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 my-4">
          <FeatureCard title="Streaming Multiple" description="Calculates value based on annual streaming revenue multiplied by an industry-standard factor." />
          <FeatureCard title="Revenue Multiple" description="Applies a multiple to total annual revenue across all sources (streaming, sync, mechanical, etc.)." />
          <FeatureCard title="Market Comparables" description="Benchmarks your catalog against recent market transactions for similar catalogs." />
          <FeatureCard title="Black Box Algorithm" description="Proprietary weighted calculation considering streaming data, revenue, growth rates, territory diversification, and catalog depth." />
        </div>

        <SubHeading>Institutional Underwriting Engine</SubHeading>
        <p className="text-sm text-[#7A8580] mb-3">
          The Underwriting Engine is a statement-driven analytics layer that sits on top of your ingested royalty data. It produces institutional-grade valuations by building a song-by-period revenue spine, fitting exponential decay curves, computing concentration metrics, and generating forward projections with valuation bands. Click the "Run Underwriting" button to trigger a new analysis.
        </p>

        <SubHeading>Running an Underwriting Analysis</SubHeading>
        <StepList steps={[
          'Navigate to the Catalog Valuation page from the sidebar.',
          'Click the "Run Underwriting" button in the top-right corner.',
          'Configure the analysis options in the modal: Periodization Mode (Activity or Statement period), Granularity (Semi-Annual or Quarterly), whether to include Sync & Print revenue, and whether to use Gross or Net amounts.',
          'Click "Run Analysis" to start. The engine will process all matched royalty statement lines for your organization.',
          'Once complete, the dashboard will update with the full underwriting results across all tabs.',
        ]} />
        <Tip>You need processed royalty statements with matched assets before running an underwriting analysis. Ingest and match your statements in the Royalties section first.</Tip>

        <SubHeading>Dashboard Tabs</SubHeading>
        <p className="text-sm text-[#7A8580] mb-3">
          Once an underwriting analysis has been run, the dashboard displays results across six tabs:
        </p>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 my-4">
          <FeatureCard title="Overview" description="Summary cards showing catalog value (low/base/high bands), annual revenue with publisher/master split, portfolio half-life, and HHI concentration. Includes side-by-side Multiplier and DCF valuation panels plus stability signals." />
          <FeatureCard title="Revenue Spine" description="A pivoted song-by-period table showing the top 25 songs across all time periods with per-period net revenue and totals. This is the foundational data table that drives all downstream analytics." />
          <FeatureCard title="Decay Analytics" description="Portfolio-level decay rate and half-life, a half-life distribution chart showing how songs cluster by decay speed, and a per-song table with decay rate (k), half-life, R-squared fit quality, volatility, and CAGR." />
          <FeatureCard title="Concentration" description="Trend charts showing Top-1, Top-3, Top-5 revenue share and HHI (Herfindahl-Hirschman Index) over time periods. High concentration indicates catalog revenue depends heavily on a few songs." />
          <FeatureCard title="Projections" description="Forward revenue projections across three scenarios (Downside, Base, Upside) displayed as an area chart and a year-by-year table. Scenarios apply different decay rate multipliers to model optimistic and pessimistic outcomes." />
          <FeatureCard title="Run History" description="A list of all past underwriting runs with timestamps, status indicators, KB version, and blended valuations. Click any run to load its full results into the dashboard." />
        </div>

        <SubHeading>Valuation Methods</SubHeading>
        <p className="text-sm text-[#7A8580] mb-3">
          The underwriting engine produces valuations using two institutional methods, then blends them:
        </p>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 my-4">
          <FeatureCard title="Multiplier Valuation" description="Applies industry-standard multiplier bands to annual revenue: Publishing at 10x/13x/16x and Masters at 6x/9x/12x. Adjusted for concentration risk, volatility, and catalog stability signals." />
          <FeatureCard title="DCF Valuation" description="Discounted Cash Flow analysis using a 10-year projection horizon with three discount rates (9%, 11%, 14%). Projects forward using fitted decay parameters from your actual revenue history." />
        </div>
        <p className="text-sm text-[#7A8580] mb-3">
          The final Blended Valuation is the average of the Multiplier and DCF methods, presented as low/base/high bands to reflect the range of reasonable values.
        </p>

        <SubHeading>Key Metrics Explained</SubHeading>
        <KeyValue label="Half-Life">The number of periods it takes for a song's revenue to decline to 50% of its peak. Longer half-lives indicate more durable catalog value.</KeyValue>
        <KeyValue label="Decay Rate (k)">The exponential decay constant. A higher k means faster revenue decline. Fitted using the formula y(t) = y0 * exp(-k*t).</KeyValue>
        <KeyValue label="R-Squared">How well the exponential decay curve fits the actual data. Values above 0.7 indicate a strong fit; below 0.4 suggests irregular revenue patterns.</KeyValue>
        <KeyValue label="HHI">Herfindahl-Hirschman Index measuring revenue concentration. Values above 0.25 (25%) indicate high concentration risk where a few songs dominate earnings.</KeyValue>
        <KeyValue label="CAGR">Compound Annual Growth Rate of a song's revenue. Positive values indicate growing revenue; negative values indicate decline.</KeyValue>
        <KeyValue label="Volatility">Standard deviation of period-over-period revenue changes. High volatility can indicate inconsistent or sync-driven revenue.</KeyValue>

        <SubHeading>Stability Signals</SubHeading>
        <p className="text-sm text-[#7A8580] mb-3">
          The Overview tab displays stability signal badges that flag potential risks in your catalog. Green badges indicate healthy signals, while red badges flag issues like high concentration, revenue volatility, or rapid decay that may affect valuation multiples.
        </p>

        <SubHeading>Valuation Report</SubHeading>
        <p className="text-sm text-[#7A8580] mb-3">
          You can download a branded Excel report containing the full valuation breakdown, methodology details, and supporting data for use in presentations and negotiations. Click the "Export" button in the top-right corner.
        </p>
        <Tip>Run underwriting analyses periodically to track how your catalog's estimated value and decay characteristics change over time as you add new content and process new royalty statements.</Tip>

        {/* ===== 22. SETTINGS ===== */}
        <SectionHeading id="settings">22. Settings & Integrations</SectionHeading>
        <p className="text-sm text-[#7A8580] mb-3">
          The Settings page allows you to configure your account, organization preferences, and third-party integrations.
        </p>

        <SubHeading>Integrations Tab</SubHeading>
        <p className="text-sm text-[#7A8580] mb-3">
          The Integrations tab manages connections to external services like Dropbox and Google Drive. From here you can:
        </p>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 my-4">
          <FeatureCard title="Connect Dropbox" description="Link your Dropbox account to enable file browsing, audio linking, and AI analysis of your stored music files." />
          <FeatureCard title="Connect Google Drive" description="Link your Google Drive account for the same cloud storage features (coming soon for some providers)." />
          <FeatureCard title="Set Default Folder" description="Use the folder picker to browse and select the default folder the system starts from when scanning." />
          <FeatureCard title="Test / Disconnect" description="Verify the connection is working or remove it entirely. Disconnecting revokes access." />
        </div>
        <Tip>After connecting Dropbox, always use the folder picker to set a default folder. This saves time when browsing files and sets the starting point for storage scans.</Tip>

        <SubHeading>Notification Preferences</SubHeading>
        <p className="text-sm text-[#7A8580] mb-3">
          Customize which events trigger notifications. You can enable or disable notifications for various event types at both the user level (your personal preferences) and the organization level (defaults for all members). Available notification channels include in-app notifications and email.
        </p>

        <SubHeading>Email Digest</SubHeading>
        <p className="text-sm text-[#7A8580] mb-3">
          The Email Digest tab lets you configure automated email summaries of your action items. When enabled, the system sends branded HTML emails to your registered email address on a schedule you choose.
        </p>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 my-4">
          <FeatureCard title="Toggle On/Off" description="Enable or disable email digest notifications with a single click." />
          <FeatureCard title="Frequency" description="Choose how often you receive digests: Daily, Every 3 Days, Weekly, Biweekly, or Monthly." />
          <FeatureCard title="Priority Threshold" description="Filter which action items appear in your digest: Critical Only, High & Above, Medium & Above, or All priorities." />
          <FeatureCard title="Delivery Time" description="Set your preferred hour of the day (in UTC) for receiving digest emails." />
        </div>
        <p className="text-sm text-[#7A8580] mb-3">
          Each digest email groups your pending action items by priority level (Critical, High, Medium, Low), includes overdue warnings, and provides a summary of total items, overdue counts, and priority breakdowns. Use the <ButtonRef label="Send Test Email" color="green" /> button to preview what your digest will look like with your current settings and filters.
        </p>
        <Tip>Set your digest frequency to match your workflow. Daily digests work well for active catalog managers, while weekly digests suit periodic reviewers. The priority threshold filter helps you focus only on what matters most.</Tip>

        <SubHeading>Push Notifications</SubHeading>
        <p className="text-sm text-[#7A8580] mb-3">
          Cadence supports push notifications so you can receive instant alerts on your device, even when the app isn't open. Push notifications appear as native system notifications on desktop and mobile.
        </p>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 my-4">
          <FeatureCard title="Enable/Disable" description="Toggle push notifications on or off per device using the switch in the Notifications tab of Settings." />
          <FeatureCard title="Browser Permission" description="When you enable push for the first time, your browser will ask for notification permission. You must allow it for push to work." />
          <FeatureCard title="Test Notification" description="Once enabled, use the Send Test button to verify push notifications are reaching your device correctly." />
          <FeatureCard title="Multi-Device" description="Push subscriptions are per-device. Enable push on each device where you want to receive alerts (desktop, phone, tablet)." />
        </div>
        <Tip>Push notifications are great for time-sensitive alerts like placement status changes and contract expirations. Combine them with email digests for full coverage — push for urgent items, email for daily summaries.</Tip>

        <SubHeading>Install App</SubHeading>
        <p className="text-sm text-[#7A8580] mb-3">
          Cadence works as a Progressive Web App (PWA), meaning you can install it directly to your home screen or desktop for a native app-like experience. When installed, Cadence launches in its own window without browser chrome and supports offline access for previously loaded pages.
        </p>
        <StepList steps={[
          'Go to Settings > Notifications.',
          'If your browser supports installation, you\'ll see an "Install App" card with an Install button.',
          'Click Install and follow the browser prompt to add Cadence to your device.',
          'Once installed, the card will show a green "Installed" badge.',
          'You can also install from your browser\'s menu (e.g., Chrome: "Install Cadence..." in the address bar or three-dot menu).',
        ]} />
        <Tip>Installing Cadence as an app gives you faster access, a dedicated window, and offline support for previously cached pages. It works on Chrome, Edge, Safari (iOS), and most Chromium-based browsers.</Tip>

        <SubHeading>Organization Admin Panel</SubHeading>
        <p className="text-sm text-[#7A8580] mb-3">
          Users with Owner or Admin roles can access the Organization Admin panel from the sidebar. This panel provides team and branding management:
        </p>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 my-4">
          <FeatureCard title="Team Management" description="Invite new members, assign roles (Member, Admin, Owner), and remove users from your organization." />
          <FeatureCard title="Password Resets" description="Reset passwords for team members who are locked out of their accounts." />
          <FeatureCard title="Client/Creator Assignment" description="Assign specific clients or creators to individual team members for workload management." />
          <FeatureCard title="Organization Branding" description="Customize your organization's logo, display name, and primary color theme." />
        </div>

        <SubHeading>Account Linking</SubHeading>
        <p className="text-sm text-[#7A8580] mb-3">
          Link Individual accounts to Enterprise organizations for creators who work across multiple labels or publishers. Account linking requires mutual consent from both parties and enables cross-organization visibility where permitted.
        </p>

        {/* ===== 23. TIPS ===== */}
        <SectionHeading id="tips">23. Tips & Best Practices</SectionHeading>

        <SubHeading>Catalog Health</SubHeading>
        <div className="space-y-3 my-4">
          <Tip>Start by getting all songs to at least 60% health. Focus on ISRCs, credits, and contract uploads first — these have the highest impact on health scores.</Tip>
          <Tip>Use the "Needs Attention" tab on the Catalog page to quickly find songs that need the most work.</Tip>
          <Tip>Check the Home Dashboard daily for auto-generated action items that highlight urgent catalog gaps.</Tip>
        </div>

        <SubHeading>Data Entry Efficiency</SubHeading>
        <div className="space-y-3 my-4">
          <Tip>Use CSV bulk upload for large catalogs instead of adding songs one by one. The AI column mapping makes it easy to import from any spreadsheet format.</Tip>
          <Tip>Use Spotify Import to quickly populate track metadata (title, artist, ISRC, release date) from existing Spotify playlists.</Tip>
          <Tip>Assign bulk credits and metadata using the bulk operations feature on the Catalog page — select multiple songs and apply changes at once.</Tip>
        </div>

        <SubHeading>Rights & Contracts</SubHeading>
        <div className="space-y-3 my-4">
          <Tip>Always link contracts to their associated songs and works. This ensures the Rights Coverage report accurately reflects your catalog's documentation status.</Tip>
          <Tip>Set up rights splits as early as possible. This enables accurate royalty calculations when you start processing statements.</Tip>
          <Tip>Pay attention to contract expiration alerts in your Action Items — renewing or renegotiating deals on time protects your catalog.</Tip>
        </div>

        <SubHeading>Cloud Storage & Audio</SubHeading>
        <div className="space-y-3 my-4">
          <Tip>Connect Dropbox early and run AI audio analysis on your entire catalog. This enriches your songs with BPM, key, and mood tags that power the Brief Builder.</Tip>
          <Tip>Use per-creator folder linking in Storage Scan to organize your audio files. Set up weekly scheduled scans to automatically detect new files as creators deliver content.</Tip>
          <Tip>After changing Dropbox app permissions, always disconnect and reconnect in Settings to pick up the new scopes.</Tip>
        </div>

        <SubHeading>Sync & Placements</SubHeading>
        <div className="space-y-3 my-4">
          <Tip>Use the Brief Builder to quickly find songs matching sync briefs. The more analyzed songs in your catalog, the better the AI matching results.</Tip>
          <Tip>Generate Sync Reports monthly for each client to showcase your pitching activity and placement wins.</Tip>
          <Tip>Keep placement statuses up to date as they progress through the pipeline — this powers accurate dashboard metrics and automated action items.</Tip>
        </div>

        <SubHeading>Workflow</SubHeading>
        <div className="space-y-3 my-4">
          <Tip>Use the Home Dashboard as your daily starting point. It surfaces the most urgent items across all modules.</Tip>
          <Tip>Keep the Action Items inbox clean by completing or updating tasks regularly. Use priority and due date to triage effectively.</Tip>
          <Tip>Run the Catalog Valuation tool quarterly to track your catalog's value growth and build a data-driven case for investment.</Tip>
          <Tip>Enable Email Digests in Settings to receive scheduled summaries of your action items. Set the priority threshold to "High & Above" to focus on critical tasks without inbox overload.</Tip>
          <Tip>Run a monthly PRO registration check using the Registration Reports Outstanding filter to catch any unregistered songs.</Tip>
        </div>

        {/* ===== 24. GLOSSARY ===== */}
        <SectionHeading id="glossary">24. Glossary</SectionHeading>
        <div className="space-y-4 my-4">
          {[
            ['Audio Analysis', 'AI-powered processing of audio files to extract BPM, key, loudness, and mood/texture/sync tags for catalog enrichment.'],
            ['Advance', 'An upfront payment to a creator or rights holder, recouped from future royalty earnings before additional payments are made.'],
            ['CAGR', 'Compound Annual Growth Rate — the annualized rate of revenue change for a song, accounting for compounding over multiple periods.'],
            ['Brief Builder', 'An AI-powered tool that matches songs in your catalog to sync brief descriptions using natural language and structured filters.'],
            ['Cloud Storage Integration', 'Connections to Dropbox or Google Drive that allow linking audio files to catalog entries without hosting files locally.'],
            ['Creative Directory', 'A contact management system for industry collaborators (producers, engineers, A&R, etc.) separate from the Creator Roster.'],
            ['Cross-Collateralization', 'A contract provision allowing revenue from multiple assets to be combined for the purpose of recouping a single advance.'],
            ['DCF Valuation', 'Discounted Cash Flow — a valuation method that projects future revenue using decay parameters and discounts it back to present value at rates of 9%, 11%, or 14%.'],
            ['Decay Rate (k)', 'The exponential decay constant measuring how quickly a song\'s revenue declines over time. Fitted from the formula y(t) = y0 * exp(-k*t).'],
            ['Demo', 'A work type indicating a song with lyrics and melodies, as opposed to a purely instrumental track.'],
            ['Distribution Readiness', 'A validation status indicating whether a release has all required metadata, identifiers, artwork, and legal clearances for distribution.'],
            ['Email Digest', 'An automated, scheduled email summarizing your pending action items, grouped by priority level, sent at your chosen frequency.'],
            ['Fee', 'A charge deducted from earnings for services such as management, administration, distribution, sync licensing, or legal representation.'],
            ['Fuzzy Matching', 'AI-powered comparison of file names against catalog entries, assigning confidence levels (HIGH, MEDIUM, LOW, NONE) based on similarity.'],
            ['Half-Life', 'The number of periods it takes for a song\'s revenue to decline to 50% of its peak value. Calculated as ln(2)/k from the fitted decay curve.'],
            ['Health Score', 'A percentage score indicating how complete a song\'s metadata and documentation is, calculated from a weighted checklist.'],
            ['HHI', 'Herfindahl-Hirschman Index — a concentration metric calculated by summing squared revenue shares. Values above 0.25 indicate high concentration risk.'],
            ['IPI', 'Interested Party Information — a unique number identifying a rights holder in royalty collection systems.'],
            ['ISRC', 'International Standard Recording Code — a unique identifier for a specific recording of a song.'],
            ['ISWC', 'International Standard Musical Work Code — a unique identifier for a musical composition (work).'],
            ['Ledger Entry', 'An individual accounting record in the royalty ledger, tracking earnings, fees, recoupment, payables, payments, and reversals.'],
            ['Master Rights', 'Rights to the sound recording itself (as opposed to the underlying composition).'],
            ['Matching Console', 'The two-pane interface for reviewing and confirming how statement lines connect to catalog assets (songs, works, releases).'],
            ['Mechanical Rights', 'Rights related to the reproduction of a musical composition (e.g., physical copies, downloads, interactive streams).'],
            ['Multi-Tenant', 'An architecture where one instance of the software serves multiple organizations, with complete data isolation between them.'],
            ['Multiplier Valuation', 'A valuation method that applies industry-standard revenue multiples (publishing: 10/13/16x, masters: 6/9/12x) to annual earnings, adjusted for catalog risk factors.'],
            ['Payable', 'The net amount owed to a payee after earnings have been reduced by fees and advance recoupment.'],
            ['Payout Batch', 'A grouped set of payment items that can be reviewed, approved, and marked as paid together.'],
            ['Performance Rights', 'Rights related to the public performance of a musical composition (radio, live venues, streaming).'],
            ['Placement', 'A sync licensing opportunity where a song is used in visual media such as TV shows, films, advertisements, or video games.'],
            ['PRO', 'Performing Rights Organization — an organization that collects performance royalties on behalf of songwriters and publishers (e.g., ASCAP, BMI, SESAC, PRS).'],
            ['Processing Run', 'A single execution of the processing engine against a statement, producing ledger entries and updating advance balances.'],
            ['Publishing Rights', 'Rights to the underlying musical composition, including mechanical, performance, and sync rights.'],
            ['Recoupment', 'The process of recovering an advance paid to an artist or rights holder from subsequent royalty earnings.'],
            ['Recoupment Pool', 'The category of revenue from which an advance can be recouped: Master, Publishing, Both, or Custom.'],
            ['Registration Report', 'A branded report listing songs and works for PRO registration, exportable as PDF or CSV and emailable to administrators.'],
            ['Release', 'A package of recordings (single, EP, album, compilation) delivered to streaming platforms and retailers.'],
            ['Reprocessing', 'The act of re-running the processing engine on a previously processed statement, creating reversal entries first to maintain audit integrity.'],
            ['Revenue Spine', 'The foundational song-by-period revenue table produced by the underwriting engine, showing net revenue for each song across each time period.'],
            ['Reversal Entry', 'A ledger entry that negates a prior entry, created during reprocessing to correct allocations while preserving the full audit trail.'],
            ['Rights Split', 'The percentage allocation of specific rights types (master, publishing, sync, etc.) among rights holders for a given asset.'],
            ['Royalty Statement', 'A financial report from a PRO, DSP, or distributor detailing royalty earnings for a specific period.'],
            ['Schedule A', 'A document listing all compositions or recordings covered by a contract, typically attached as an exhibit.'],
            ['Split Sheet', 'A document that records the ownership percentages of a song among its creators, typically signed by all parties before release.'],
            ['Statement Line', 'A single row within a royalty statement representing earnings for one track/territory/store combination.'],
            ['Storage Scan', 'Per-creator folder linking and AI-powered recursive file scanning that matches audio files to catalog entries using fuzzy matching.'],
            ['Sync Report', 'A customizable report summarizing sync placement activity, filterable by client, status, and date range, exportable as PDF or CSV.'],
            ['Sync Rights', 'Synchronization rights — the right to use a musical composition in timed relation to visual media (film, TV, ads, games).'],
            ['Stability Signals', 'Risk indicators flagged by the underwriting engine, such as high concentration, rapid decay, or revenue volatility, which may adjust valuation multiples.'],
            ['Underwriting Engine', 'An institutional-grade analytics engine that builds a revenue spine from royalty statements, fits decay curves, computes concentration metrics, and produces DCF and multiplier valuations.'],
            ['Underwriting Run', 'A single execution of the underwriting engine with a specific configuration, producing a snapshot of the catalog\'s valuation and analytics.'],
            ['UPC/EAN', 'Universal Product Code / European Article Number — a barcode identifier for a release (album, EP, single).'],
            ['Volatility', 'A measure of revenue inconsistency, calculated as the standard deviation of period-over-period log revenue ratios for a song.'],
            ['Work', 'A musical composition — the underlying song as written, separate from any particular recording of it.'],
          ].map(([term, definition]) => (
            <div key={term} className="flex gap-3">
              <span className="font-semibold text-[#3D4A44] min-w-[160px] text-sm">{term}</span>
              <span className="text-sm text-[#7A8580]">{definition}</span>
            </div>
          ))}
        </div>

        <div className="mt-16 pt-8 border-t border-[rgba(59,77,67,0.1)] text-center text-sm text-[#7A8580] print:mt-12">
          <img src="/logo-small.png" alt="Logo" className="h-8 w-auto mx-auto mb-3 opacity-60" />
          <p className="font-medium text-[#3D4A44]">Cadence — Catalog Intelligence</p>
          <p>Version {VERSION} &middot; {LAST_UPDATED}</p>
          <p className="mt-2">For support, contact your organization administrator.</p>
        </div>
      </div>
    </div>
  )
}

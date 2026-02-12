import React, { useRef } from 'react'
import { ArrowDownTrayIcon, ChevronRightIcon } from '@heroicons/react/24/outline'

const VERSION = '2.0'
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
  { id: 'reports', title: '13. Reports & Analytics' },
  { id: 'valuation', title: '14. Catalog Valuation' },
  { id: 'settings', title: '15. Settings' },
  { id: 'tips', title: '16. Tips & Best Practices' },
  { id: 'glossary', title: '17. Glossary' },
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

export default function UserGuidePage() {
  const contentRef = useRef(null)

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
          <img src="/rythm-logo.png" alt="Rythm" className="h-24 w-auto mx-auto mb-6" />
          <h1 className="text-2xl sm:text-4xl font-bold text-[#3D4A44] mb-2">Rythm</h1>
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
          Rythm is a multi-tenant platform. All your data — songs, creators, contracts, and more — is scoped to your organization. Each user belongs to an organization, and all content you create is visible only to members of that organization.
        </p>

        <SubHeading>User Roles</SubHeading>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 my-4">
          <FeatureCard title="Member" description="Standard access to all catalog management features within your organization." />
          <FeatureCard title="Admin" description="Full access plus organization settings, user management, and configuration." />
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
              { icon: '🎵', label: 'Catalog', desc: 'Song management' },
              { icon: '📝', label: 'Works', desc: 'Compositions' },
              { icon: '💿', label: 'Releases', desc: 'Albums & EPs' },
              { icon: '📋', label: 'Contracts', desc: 'Deal management' },
              { icon: '✅', label: 'Actions', desc: 'Task inbox' },
              { icon: '💰', label: 'Royalties', desc: 'Financial engine' },
              { icon: '🎬', label: 'Placements', desc: 'Sync licensing' },
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
          <li>Rythm branding and contract metadata</li>
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

        <SubHeading>Managing Works</SubHeading>
        <StepList steps={[
          'Navigate to the Works page from the sidebar.',
          'View all works in a searchable list with title, ISWC, and associated track count.',
          'Click + Add Work to create a new composition record.',
          'Fill in the work title, ISWC (if available), alternative titles, and other metadata.',
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
          Once ready, export your release metadata in CSV or JSON format for submission to distribution partners. Use the export buttons in the Release Builder view.
        </p>

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
        ]} />

        <SubHeading>Filtering & Organization</SubHeading>
        <p className="text-sm text-[#7A8580] mb-3">
          Filter tasks by entity type (songs, works, releases, contracts, placements, royalties) using the filter buttons. The module breakdown widget shows how many tasks exist in each category, helping you prioritize your workflow.
        </p>

        {/* ===== 11. ROYALTIES ===== */}
        <SectionHeading id="royalties">11. Royalties</SectionHeading>
        <p className="text-sm text-[#7A8580] mb-3">
          The Royalties module is a full financial engine for managing statement ingestion, asset matching, royalty calculations, advance recoupment, and payment tracking.
        </p>

        <SubHeading>Royalty Dashboard</SubHeading>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 my-4">
          <FeatureCard title="Revenue Charts" description="Visual breakdown of royalty revenue over time with trend analysis." />
          <FeatureCard title="Top Earning Tracks" description="Ranked list of your highest-revenue songs from royalty statements." />
          <FeatureCard title="Recoupment Progress" description="Progress bars showing advance recoupment status for each contract/deal." />
          <FeatureCard title="Earnings Breakdown" description="View earnings by rights holder, contract, or individual track." />
        </div>

        <SubHeading>Statement Upload</SubHeading>
        <StepList steps={[
          'Navigate to the Royalties page.',
          'Click "Upload Statement" to import a royalty statement.',
          'Upload a CSV or Excel file containing transaction data.',
          'The system automatically matches transactions to your catalog using ISRC, title, and artist name (fuzzy matching).',
          'Review matches and resolve any unmatched transactions.',
          'Confirmed transactions are processed through the calculation engine.',
        ]} />

        <SubHeading>Royalty Calculation</SubHeading>
        <p className="text-sm text-[#7A8580] mb-3">
          The calculation engine applies contract splits to matched transactions, handles advance recoupment, and generates per-holder allocations. Multi-currency support with exchange rate conversion is included.
        </p>

        <SubHeading>Fees & Advances</SubHeading>
        <p className="text-[#7A8580] mb-3">
          The <strong>Fees & Advances</strong> tab in the Royalties page provides organization-wide financial tracking:
        </p>
        <ul className="list-disc pl-5 text-[#7A8580] space-y-1 mb-3">
          <li><strong>Fees:</strong> Track management, administration, distribution, sync, and legal fees per creator</li>
          <li><strong>Advances:</strong> Record advances with amounts, dates, and recoupment tracking</li>
          <li>View recoupment progress bars showing how much of each advance has been recovered</li>
          <li>Filter by creator to see individual financial summaries</li>
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

        {/* ===== 13. REPORTS ===== */}
        <SectionHeading id="reports">13. Reports & Analytics</SectionHeading>
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

        {/* ===== 14. VALUATION ===== */}
        <SectionHeading id="valuation">14. Catalog Valuation</SectionHeading>
        <p className="text-sm text-[#7A8580] mb-3">
          The Catalog Valuation tool estimates your catalog's financial value using industry-standard methodologies. It provides actionable insights for business planning, investment discussions, and catalog transactions.
        </p>

        <SubHeading>Valuation Methodologies</SubHeading>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 my-4">
          <FeatureCard title="Streaming Multiple" description="Calculates value based on annual streaming revenue multiplied by an industry-standard factor." />
          <FeatureCard title="Revenue Multiple" description="Applies a multiple to total annual revenue across all sources (streaming, sync, mechanical, etc.)." />
          <FeatureCard title="Market Comparables" description="Benchmarks your catalog against recent market transactions for similar catalogs." />
          <FeatureCard title="Black Box Algorithm" description="Proprietary weighted calculation considering streaming data, revenue, growth rates, territory diversification, and catalog depth." />
        </div>

        <SubHeading>Valuation Report</SubHeading>
        <p className="text-sm text-[#7A8580] mb-3">
          The final valuation is a weighted average of all four methodologies. You can download a branded Excel report containing the full valuation breakdown, methodology details, and supporting data for use in presentations and negotiations.
        </p>
        <Tip>Run valuations periodically to track how your catalog's estimated value changes over time as you add new content and grow revenue.</Tip>

        {/* ===== 15. SETTINGS ===== */}
        <SectionHeading id="settings">15. Settings</SectionHeading>
        <p className="text-sm text-[#7A8580] mb-3">
          The Settings page allows you to configure your account and organization preferences.
        </p>

        <SubHeading>Notification Preferences</SubHeading>
        <p className="text-sm text-[#7A8580] mb-3">
          Customize which events trigger notifications. You can enable or disable notifications for various event types at both the user level (your personal preferences) and the organization level (defaults for all members). Available notification channels include in-app notifications and email.
        </p>

        <SubHeading>Account Linking</SubHeading>
        <p className="text-sm text-[#7A8580] mb-3">
          Link Individual accounts to Enterprise organizations for creators who work across multiple labels or publishers. Account linking requires mutual consent from both parties and enables cross-organization visibility where permitted.
        </p>

        {/* ===== 16. TIPS ===== */}
        <SectionHeading id="tips">16. Tips & Best Practices</SectionHeading>

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

        <SubHeading>Workflow</SubHeading>
        <div className="space-y-3 my-4">
          <Tip>Use the Home Dashboard as your daily starting point. It surfaces the most urgent items across all modules.</Tip>
          <Tip>Keep the Action Items inbox clean by completing or updating tasks regularly. Use priority and due date to triage effectively.</Tip>
          <Tip>Run the Catalog Valuation tool quarterly to track your catalog's value growth and build a data-driven case for investment.</Tip>
        </div>

        {/* ===== 17. GLOSSARY ===== */}
        <SectionHeading id="glossary">17. Glossary</SectionHeading>
        <div className="space-y-4 my-4">
          {[
            ['ISRC', 'International Standard Recording Code — a unique identifier for a specific recording of a song.'],
            ['ISWC', 'International Standard Musical Work Code — a unique identifier for a musical composition (work).'],
            ['UPC/EAN', 'Universal Product Code / European Article Number — a barcode identifier for a release (album, EP, single).'],
            ['IPI', 'Interested Party Information — a unique number identifying a rights holder in royalty collection systems.'],
            ['PRO', 'Performing Rights Organization — an organization that collects performance royalties on behalf of songwriters and publishers (e.g., ASCAP, BMI, SESAC, PRS).'],
            ['Health Score', 'A percentage score indicating how complete a song\'s metadata and documentation is, calculated from a weighted checklist.'],
            ['Master Rights', 'Rights to the sound recording itself (as opposed to the underlying composition).'],
            ['Publishing Rights', 'Rights to the underlying musical composition, including mechanical, performance, and sync rights.'],
            ['Mechanical Rights', 'Rights related to the reproduction of a musical composition (e.g., physical copies, downloads, interactive streams).'],
            ['Performance Rights', 'Rights related to the public performance of a musical composition (radio, live venues, streaming).'],
            ['Sync Rights', 'Synchronization rights — the right to use a musical composition in timed relation to visual media (film, TV, ads, games).'],
            ['Placement', 'A sync licensing opportunity where a song is used in visual media such as TV shows, films, advertisements, or video games.'],
            ['Recoupment', 'The process of recovering an advance paid to an artist or rights holder from subsequent royalty earnings.'],
            ['Schedule A', 'A document listing all compositions or recordings covered by a contract, typically attached as an exhibit.'],
            ['Distribution Readiness', 'A validation status indicating whether a release has all required metadata, identifiers, artwork, and legal clearances for distribution.'],
            ['Multi-Tenant', 'An architecture where one instance of the software serves multiple organizations, with complete data isolation between them.'],
            ['Work', 'A musical composition — the underlying song as written, separate from any particular recording of it.'],
            ['Release', 'A package of recordings (single, EP, album, compilation) delivered to streaming platforms and retailers.'],
            ['Rights Split', 'The percentage allocation of specific rights types (master, publishing, sync, etc.) among rights holders for a given asset.'],
          ].map(([term, definition]) => (
            <div key={term} className="flex gap-3">
              <span className="font-semibold text-[#3D4A44] min-w-[160px] text-sm">{term}</span>
              <span className="text-sm text-[#7A8580]">{definition}</span>
            </div>
          ))}
        </div>

        <div className="mt-16 pt-8 border-t border-[rgba(59,77,67,0.1)] text-center text-sm text-[#7A8580] print:mt-12">
          <img src="/logo-small.png" alt="Logo" className="h-8 w-auto mx-auto mb-3 opacity-60" />
          <p className="font-medium text-[#3D4A44]">Rythm — Catalog Intelligence</p>
          <p>Version {VERSION} &middot; {LAST_UPDATED}</p>
          <p className="mt-2">For support, contact your organization administrator.</p>
        </div>
      </div>
    </div>
  )
}

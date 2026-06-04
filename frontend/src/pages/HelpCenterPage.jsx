import React, { useState } from 'react'
import PublicPageLayout from '../components/PublicPageLayout'
import SEO from '../components/SEO'

const sections = [
  {
    title: 'Getting Started',
    items: [
      {
        q: 'What is Cadence?',
        a: 'Cadence is a platform for managing music catalogs, rights, royalties, and sync placements in one place. Think of it as the operating system for your catalog \u2014 designed to treat every song as the financial asset it is.'
      },
      {
        q: 'Who is Cadence for?',
        a: 'Independent labels, music publishers, production companies, artist managers, catalog investors, and the administrators who support them. If you manage music rights for yourself or others, Cadence is built for you.'
      },
      {
        q: 'How do I create an account?',
        a: 'Go to cadence-ci.com, click "Sign Up," and follow the prompts. You\'ll create an organization, add your first user, and land on the dashboard.'
      },
      {
        q: 'What are the subscription tiers?',
        a: 'Cadence offers a Free plan, Standard ($29/month), Professional ($99/month), Enterprise ($499/month), and Enterprise + Luminate ($699/month). Each tier unlocks additional features, catalog capacity, and integrations. See the pricing page for details.'
      },
      {
        q: 'How do I invite team members?',
        a: 'Go to Settings \u2192 Team \u2192 Invite Member. Enter their email and assign a role (Owner, Admin, Member, or Client). They\'ll receive an email invitation to join your organization.'
      },
    ]
  },
  {
    title: 'Catalog Management',
    items: [
      {
        q: 'How do I add songs to my catalog?',
        a: 'You have several options: (1) Manually \u2014 create a song entry one at a time from the Catalog page. (2) Spotify import \u2014 paste a Spotify playlist or album link to pull songs with metadata already attached. (3) Schedule A upload \u2014 upload a CSV, Excel, PDF, or Word document and let our AI map the columns for you. (4) Dropbox or Google Drive scan \u2014 link a folder and let Cadence scan for audio files and match them to your catalog.'
      },
      {
        q: "What's the difference between Released and Unreleased works?",
        a: "A Released work has an official release date that has already passed. An Unreleased work is anything else \u2014 demos, placed-but-not-yet-released songs, sync pitches, instrumentals. Cadence automatically moves an Unreleased work to Released on its release date if you've set one."
      },
      {
        q: 'How do splits work in Cadence?',
        a: "Splits are entered at the client level. When you create a song, you'll assign a percentage to each contributing writer or producer. If an organization owns a share in the song, create a separate client entry for that organization and assign splits accordingly. Changes to splits are date-stamped in the song's edit history."
      },
      {
        q: "Can I track a song's edit history?",
        a: "Yes. Every change to a song \u2014 splits, contributors, metadata, release status \u2014 is logged in the song's edit history with a timestamp and the user who made the change. This creates a verifiable digital trail of how the song evolved."
      },
      {
        q: 'How do I handle remixes, instrumentals, or alternate versions?',
        a: 'Use the Duplicate feature on the song detail page. It creates a new entry linked to the original, so you can adjust splits and metadata without re-entering everything.'
      },
    ]
  },
  {
    title: 'Royalty Processing',
    items: [
      {
        q: 'How do I upload a royalty statement?',
        a: 'Go to Royalties \u2192 Upload Statement. Select the source (BMI, ASCAP, MLC, distributor, etc.), upload the file, and Cadence will parse it, map columns, and match line items to songs in your catalog.'
      },
      {
        q: 'What file formats are supported?',
        a: "CSV, Excel (XLSX), and PDF. Our AI handles most formats from major performing rights organizations and distributors. If we don't recognize your source, contact support and we'll add it."
      },
      {
        q: "What happens if a line item doesn't match a song?",
        a: 'Unmatched transactions appear in the Unmatched queue. You can manually match them to a song, create a new song entry, or dismiss them. Cadence learns from your matches over time.'
      },
      {
        q: 'How does Cadence handle MLC statements with multiple clients?',
        a: 'MLC statements often contain line items that apply to multiple clients you manage. Cadence detects MLC statements and automatically splits line items across the relevant clients based on their mirrored splits.'
      },
      {
        q: 'Can I see how much each song is earning?',
        a: "Yes. Open any song to see its earnings history, revenue trends, and decay curve based on the statements you've uploaded."
      },
    ]
  },
  {
    title: 'Valuations',
    items: [
      {
        q: 'How does catalog valuation work in Cadence?',
        a: 'Upload several years of royalty statements and Cadence calculates a baseline valuation using historical earnings, decay analysis, and (if enabled) Luminate consumption data. You can apply multiples and export the valuation report.'
      },
      {
        q: 'What data do I need for an accurate valuation?',
        a: 'Ideally three years of royalty statements across all your income sources. The more complete your data, the more defensible the valuation.'
      },
      {
        q: 'What is the Luminate integration?',
        a: "Luminate provides streaming consumption data. When integrated, Cadence cross-references your catalog against Luminate's numbers to give you a more accurate picture of what your catalog is actually generating \u2014 and whether you're being paid for all of it. Available on the Enterprise + Luminate tier."
      },
    ]
  },
  {
    title: 'Contracts',
    items: [
      {
        q: 'How do I upload a contract?',
        a: 'Go to Contracts \u2192 New Contract. Upload a PDF or Word document and our AI will extract the key terms \u2014 title, type, parties, dates, territory, advance \u2014 and pre-fill the form for you to review.'
      },
      {
        q: 'Can I link contracts to specific songs?',
        a: 'Yes. Open a contract and link it to any number of songs in your catalog. The splits on those songs can reference the contract for provenance.'
      },
    ]
  },
  {
    title: 'Sync and Brief Builder',
    items: [
      {
        q: 'How does Brief Builder work?',
        a: 'Enter a natural-language description of what you\'re pitching for (e.g., "upbeat indie track for a car commercial, 120 BPM, major key"). Cadence parses the brief into structured filters and returns ranked matches from your catalog.'
      },
      {
        q: 'How do I improve match quality?',
        a: 'Make sure your songs have complete metadata \u2014 BPM, key, mood, genre, and descriptive tags. The more data, the better the matching.'
      },
    ]
  },
  {
    title: 'Client Portal',
    items: [
      {
        q: 'What is the client portal?',
        a: "It's a restricted view of Cadence that creators you represent can log into. They can see their own catalog, earnings, contracts, and sync placements without seeing other clients' data."
      },
      {
        q: 'How do I give a client access?',
        a: "Create a client user, link them to a creator entity in your roster, and send them an invitation. They'll log in at the same URL and see only their own information."
      },
    ]
  },
  {
    title: 'Integrations',
    items: [
      {
        q: 'What integrations does Cadence support?',
        a: 'Spotify (for metadata and playlist import), Dropbox and Google Drive (for audio file storage and scanning), Luminate (for consumption data, on Enterprise + Luminate), and more on the way.'
      },
      {
        q: 'How do I connect an integration?',
        a: 'Go to Settings \u2192 Integrations and follow the OAuth flow for the service you want to connect.'
      },
    ]
  },
  {
    title: 'Account and Billing',
    items: [
      {
        q: 'How do I upgrade or downgrade my plan?',
        a: 'Go to Settings \u2192 Billing \u2192 Change Plan. Changes take effect immediately and are prorated.'
      },
      {
        q: 'How do I cancel my subscription?',
        a: "Go to Settings \u2192 Billing \u2192 Cancel Subscription. You'll retain access until the end of your current billing period."
      },
      {
        q: 'How do I export my data?',
        a: 'Go to Settings \u2192 Data Export. You can export your full catalog, royalty data, contracts, and contacts as CSV files at any time. Your data is yours.'
      },
      {
        q: 'I forgot my password. How do I reset it?',
        a: "Click \"Forgot Password\" on the login page and enter your email. You'll receive a reset link within a few minutes."
      },
    ]
  },
  {
    title: 'Security',
    items: [
      {
        q: 'How is my data protected?',
        a: "Cadence uses TLS encryption for all data in transit, bcrypt password hashing, JWT-based authentication, and organization-level data isolation. Your data is never mixed with another organization's."
      },
      {
        q: 'Who can see my catalog?',
        a: 'Only authorized members of your organization, and any clients you explicitly grant access to via the client portal. Cadence staff do not access your data except when required to provide support (with your permission) or in response to valid legal process.'
      },
      {
        q: 'Does Cadence sell my data?',
        a: "No. We don't sell your personal information or your catalog data. Ever."
      },
    ]
  },
]

export default function HelpCenterPage() {
  const [openItem, setOpenItem] = useState(null)

  const toggleItem = (key) => {
    setOpenItem(openItem === key ? null : key)
  }

  return (
    <PublicPageLayout>
      <SEO
        path="/help"
        title="Help Center"
        description="Everything you need to get the most out of Cadence Catalog Intelligence — from setting up your first client to processing your first royalty statement, valuing your catalog, and using the AI-powered Brief Builder."
        image="https://cadence-ci.com/help-og.png"
      />
      <div className="text-center mb-12">
        <h1 className="text-[32px] sm:text-[40px] font-bold text-[#3D4A44] mb-3">Help Center</h1>
        <p className="text-[16px] text-[#7A8580] max-w-xl mx-auto leading-relaxed">
          Everything you need to get the most out of Cadence — from setting up your first client to processing your first royalty statement.
        </p>
      </div>

      <div className="bg-gradient-to-br from-[#5B8A72]/5 to-[#7BA594]/5 rounded-2xl p-6 mb-10 text-center">
        <p className="text-[14px] text-[#5A6660]">
          Can't find what you're looking for? Email us at{' '}
          <a href="mailto:communication@cadence-ci.com" className="text-[#5B8A72] font-medium hover:underline">communication@cadence-ci.com</a>{' '}
          and our team will get back to you within one business day.
        </p>
      </div>

      <div className="space-y-8">
        {sections.map((section, si) => (
          <div key={si}>
            <h2 className="text-[20px] font-bold text-[#3D4A44] mb-4 flex items-center gap-2">
              <span className="w-1.5 h-6 rounded-full bg-[#5B8A72]" />
              {section.title}
            </h2>
            <div className="space-y-2">
              {section.items.map((item, ii) => {
                const key = `${si}-${ii}`
                const isOpen = openItem === key
                return (
                  <div
                    key={key}
                    className="bg-white rounded-xl border border-[rgba(59,77,67,0.08)] overflow-hidden"
                  >
                    <button
                      onClick={() => toggleItem(key)}
                      className="w-full flex items-center justify-between gap-3 px-5 py-4 text-left"
                    >
                      <span className="text-[15px] font-medium text-[#3D4A44]">{item.q}</span>
                      <svg
                        className={`w-4 h-4 text-[#7A8580] flex-shrink-0 transition-transform duration-200 ${isOpen ? 'rotate-180' : ''}`}
                        fill="none" stroke="currentColor" viewBox="0 0 24 24"
                      >
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19.5 8.25l-7.5 7.5-7.5-7.5" />
                      </svg>
                    </button>
                    <div className={`transition-all duration-200 ease-in-out overflow-hidden ${isOpen ? 'max-h-[500px] opacity-100' : 'max-h-0 opacity-0'}`}>
                      <div className="px-5 pb-4 pt-0">
                        <p className="text-[14px] text-[#5A6660] leading-relaxed">{item.a}</p>
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        ))}
      </div>

      <div className="mt-12 bg-gradient-to-br from-[#5B8A72]/5 to-[#7BA594]/5 rounded-2xl p-8 text-center">
        <h3 className="text-[18px] font-bold text-[#3D4A44] mb-2">Still Need Help?</h3>
        <p className="text-[14px] text-[#5A6660] leading-relaxed mb-2">
          Email <a href="mailto:communication@cadence-ci.com" className="text-[#5B8A72] font-medium hover:underline">communication@cadence-ci.com</a> and we'll get back to you within one business day.
        </p>
        <p className="text-[13px] text-[#7A8580]">
          For urgent issues on paid plans, mark your email "URGENT" in the subject line.
        </p>
      </div>
    </PublicPageLayout>
  )
}

import React from 'react'
import PublicPageLayout from '../components/PublicPageLayout'

export default function AntiFraudPage() {
  const sectionClass = "mb-8"
  const h2Class = "text-[18px] font-bold text-[#3D4A44] mb-3"
  const h3Class = "text-[15px] font-semibold text-[#3D4A44] mb-2"
  const pClass = "text-[15px] text-[#5A6660] leading-relaxed mb-4"
  const ulClass = "list-disc pl-6 space-y-1.5 text-[15px] text-[#5A6660] leading-relaxed mb-4"

  return (
    <PublicPageLayout>
      <h1 className="text-[32px] sm:text-[40px] font-bold text-[#3D4A44] mb-2">Anti-Fraud Policy</h1>
      <p className="text-[14px] text-[#7A8580] mb-4">Last Updated: April 14, 2026</p>
      <p className={pClass}>
        Cadence Catalog Intelligence Co. ("Cadence") is committed to maintaining the integrity of the music rights ecosystem. This Anti-Fraud Policy explains what we consider fraudulent activity on the Cadence platform and how we respond.
      </p>

      <div className={sectionClass}>
        <h2 className={h2Class}>1. Prohibited Activity</h2>
        <p className={pClass}>
          The following activities are strictly prohibited on Cadence and will result in immediate account suspension or termination, forfeiture of fees, and referral to law enforcement or relevant industry authorities:
        </p>

        <h3 className={h3Class}>Ownership and Rights Fraud</h3>
        <ul className={ulClass}>
          <li>Claiming ownership of songs, recordings, or compositions you do not actually own or control</li>
          <li>Submitting false or forged contracts, split sheets, or Schedule A documents</li>
          <li>Misrepresenting the percentage of ownership you hold in a work</li>
          <li>Registering works under another person's IPI, CAE number, or publisher account without authorization</li>
        </ul>

        <h3 className={h3Class}>Royalty and Statement Fraud</h3>
        <ul className={ulClass}>
          <li>Uploading fabricated or altered royalty statements</li>
          <li>Manipulating royalty data to inflate earnings, valuations, or audit results</li>
          <li>Filing false audit claims against performing rights organizations, publishers, or distributors based on manipulated Cadence reports</li>
          <li>Attempting to double-collect royalties on the same work through multiple accounts</li>
        </ul>

        <h3 className={h3Class}>Identity and Account Fraud</h3>
        <ul className={ulClass}>
          <li>Creating an account using false information</li>
          <li>Impersonating another person, artist, or business entity</li>
          <li>Using stolen payment methods</li>
          <li>Creating multiple accounts to evade suspension or abuse free-tier limits</li>
          <li>Unauthorized access to another user's account</li>
        </ul>

        <h3 className={h3Class}>Platform Abuse</h3>
        <ul className={ulClass}>
          <li>Using Cadence to facilitate money laundering, tax evasion, or other financial crimes</li>
          <li>Reverse engineering the platform to extract data belonging to other users</li>
          <li>Automated scraping of catalog, contact, or royalty data</li>
        </ul>
      </div>

      <div className={sectionClass}>
        <h2 className={h2Class}>2. How We Detect Fraud</h2>
        <p className={pClass}>
          Cadence uses a combination of automated monitoring and manual review to detect suspicious activity, including:
        </p>
        <ul className={ulClass}>
          <li>Automated flagging of unusual upload patterns, duplicate registrations, and conflicting ownership claims</li>
          <li>Cross-referencing of catalog data against publicly available sources</li>
          <li>Manual review of accounts that trigger risk signals</li>
          <li>User reports submitted through the platform</li>
        </ul>
      </div>

      <div className={sectionClass}>
        <h2 className={h2Class}>3. What Happens When Fraud Is Detected</h2>
        <p className={pClass}>
          If we identify suspected fraudulent activity, we may take one or more of the following actions without prior notice:
        </p>
        <ul className={ulClass}>
          <li>Suspend or terminate the account</li>
          <li>Freeze catalog data and royalty processing</li>
          <li>Notify affected parties (including other Cadence users whose rights may be implicated)</li>
          <li>Report the activity to relevant performing rights organizations, publishers, or distributors</li>
          <li>Refer the matter to law enforcement</li>
          <li>Pursue civil remedies, including recovery of damages and legal fees</li>
        </ul>
        <p className={pClass}>
          You agree that Cadence has no liability for any losses you incur as a result of enforcement actions taken under this policy.
        </p>
      </div>

      <div className={sectionClass}>
        <h2 className={h2Class}>4. Reporting Fraud</h2>
        <p className={pClass}>
          If you believe another user is engaged in fraudulent activity on Cadence, or if your rights have been misrepresented on the platform, report it to <a href="mailto:communication@cadence-ci.com" className="text-[#5B8A72] font-medium hover:underline">communication@cadence-ci.com</a>. Please include:
        </p>
        <ul className={ulClass}>
          <li>The name of the user or organization you are reporting</li>
          <li>A description of the suspected fraudulent activity</li>
          <li>Supporting documentation (contracts, registration records, statements)</li>
          <li>Your contact information</li>
        </ul>
        <p className={pClass}>
          All reports are reviewed confidentially. We do not disclose the identity of the reporter to the reported party unless required by law.
        </p>
      </div>

      <div className={sectionClass}>
        <h2 className={h2Class}>5. Cooperation With Authorities</h2>
        <p className={pClass}>
          Cadence cooperates fully with law enforcement, performing rights organizations, and industry bodies investigating fraud. We may share user information and platform data in response to valid legal process or credible fraud investigations.
        </p>
      </div>

      <div className={sectionClass}>
        <h2 className={h2Class}>6. Contact</h2>
        <p className={pClass}>
          Report suspected fraud to <a href="mailto:communication@cadence-ci.com" className="text-[#5B8A72] font-medium hover:underline">communication@cadence-ci.com</a>.
        </p>
      </div>
    </PublicPageLayout>
  )
}

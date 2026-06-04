import React from 'react'
import PublicPageLayout from '../components/PublicPageLayout'
import SEO from '../components/SEO'

export default function PrivacyPolicyPage() {
  const sectionClass = "mb-8"
  const h2Class = "text-[18px] font-bold text-[#3D4A44] mb-3"
  const pClass = "text-[15px] text-[#5A6660] leading-relaxed mb-4"
  const ulClass = "list-disc pl-6 space-y-1.5 text-[15px] text-[#5A6660] leading-relaxed mb-4"

  return (
    <PublicPageLayout>
      <SEO
        path="/privacy"
        title="Privacy Policy"
        description="How Cadence Catalog Intelligence collects, uses, shares, and protects information from music publishers, rights holders, and creators using the Cadence platform."
        image="https://cadence-ci.com/privacy-og.png"
      />
      <h1 className="text-[32px] sm:text-[40px] font-bold text-[#3D4A44] mb-2">Privacy Policy</h1>
      <p className="text-[14px] text-[#7A8580] mb-4">Last Updated: April 14, 2026</p>
      <p className={pClass}>
        Cadence Catalog Intelligence Co. ("Cadence," "we," "us," or "our") respects your privacy. This Privacy Policy explains how we collect, use, share, and protect information when you use the Cadence platform, website, and related services (the "Service").
      </p>

      <div className={sectionClass}>
        <h2 className={h2Class}>1. Information We Collect</h2>

        <h3 className="text-[15px] font-semibold text-[#3D4A44] mb-2">Information You Provide Directly</h3>
        <ul className={ulClass}>
          <li><strong>Account information:</strong> name, email address, password (hashed), phone number, organization name, role</li>
          <li><strong>Billing information:</strong> payment card details (processed by our payment provider), billing address</li>
          <li><strong>Catalog data:</strong> music catalog records, metadata, splits, credits, ISRCs, ISWCs, contracts, royalty statements, contact directories, and other content you upload</li>
          <li><strong>Communications:</strong> messages you send to our support team, feedback, survey responses</li>
        </ul>

        <h3 className="text-[15px] font-semibold text-[#3D4A44] mb-2">Information Collected Automatically</h3>
        <ul className={ulClass}>
          <li><strong>Usage data:</strong> pages viewed, features used, time spent on the Service, actions taken</li>
          <li><strong>Device and technical data:</strong> IP address, browser type, operating system, device identifiers, referring URLs</li>
          <li><strong>Cookies and similar technologies:</strong> session tokens, authentication cookies, analytics identifiers</li>
        </ul>

        <h3 className="text-[15px] font-semibold text-[#3D4A44] mb-2">Information From Third Parties</h3>
        <ul className={ulClass}>
          <li><strong>Integration data:</strong> when you connect Spotify, Dropbox, Google Drive, Luminate, or other third-party services, we receive data from those services as authorized by you</li>
          <li><strong>Analytics providers:</strong> aggregated usage statistics</li>
        </ul>
      </div>

      <div className={sectionClass}>
        <h2 className={h2Class}>2. How We Use Your Information</h2>
        <p className={pClass}>We use your information to:</p>
        <ul className={ulClass}>
          <li>Provide, maintain, and improve the Service</li>
          <li>Process your royalty statements, catalog data, and valuations</li>
          <li>Authenticate your account and secure the platform</li>
          <li>Communicate with you about your account, updates, and support requests</li>
          <li>Send transactional emails (digests, notifications, receipts)</li>
          <li>Detect and prevent fraud, abuse, and security incidents</li>
          <li>Comply with legal obligations</li>
          <li>Analyze usage patterns to improve product design (in aggregate and de-identified form where possible)</li>
        </ul>
        <p className={pClass}>We do not sell your personal information or Your Content to third parties.</p>
      </div>

      <div className={sectionClass}>
        <h2 className={h2Class}>3. How We Share Information</h2>
        <p className={pClass}>We share information only in the following circumstances:</p>
        <ul className={ulClass}>
          <li><strong>With your organization:</strong> data you upload is shared with other authorized members of your organization based on role-based permissions</li>
          <li><strong>With clients you grant access to:</strong> if you use the client portal feature, the creators you represent can see their own data</li>
          <li><strong>With service providers:</strong> we use trusted third parties (hosting, email delivery, payment processing, analytics, AI processing) that are bound by confidentiality obligations</li>
          <li><strong>With integration partners:</strong> when you authorize a connection to Spotify, Dropbox, Google Drive, Luminate, or other services</li>
          <li><strong>For legal reasons:</strong> to comply with a court order, subpoena, or other legal process, or to protect the rights, property, or safety of Cadence, our users, or the public</li>
          <li><strong>In a business transfer:</strong> if Cadence is involved in a merger, acquisition, or sale of assets, your information may be transferred as part of that transaction</li>
        </ul>
      </div>

      <div className={sectionClass}>
        <h2 className={h2Class}>4. Data Security</h2>
        <p className={pClass}>We implement industry-standard security measures to protect your information, including:</p>
        <ul className={ulClass}>
          <li>Encrypted data transmission (TLS/HTTPS)</li>
          <li>Password hashing with bcrypt</li>
          <li>JWT-based authentication with session expiration</li>
          <li>Role-based access controls</li>
          <li>Organization-level data isolation</li>
          <li>Regular security reviews</li>
        </ul>
        <p className={pClass}>
          No system is perfectly secure. You are responsible for keeping your account credentials confidential and notifying us immediately if you suspect unauthorized access.
        </p>
      </div>

      <div className={sectionClass}>
        <h2 className={h2Class}>5. Data Retention</h2>
        <p className={pClass}>
          We retain your information for as long as your account is active and as needed to provide the Service. When you delete your account, we will delete or anonymize your personal information within 30 days, except for:
        </p>
        <ul className={ulClass}>
          <li>Information we are legally required to retain (tax records, audit logs, etc.)</li>
          <li>Information retained in routine backups, which will be deleted within 90 days</li>
          <li>Aggregated or de-identified data that can no longer be linked to you</li>
        </ul>
      </div>

      <div className={sectionClass}>
        <h2 className={h2Class}>6. Your Rights</h2>
        <p className={pClass}>Depending on your jurisdiction, you may have the following rights:</p>
        <ul className={ulClass}>
          <li><strong>Access:</strong> request a copy of the personal information we hold about you</li>
          <li><strong>Correction:</strong> request that we correct inaccurate information</li>
          <li><strong>Deletion:</strong> request that we delete your personal information</li>
          <li><strong>Portability:</strong> request an export of Your Content in a machine-readable format</li>
          <li><strong>Objection:</strong> object to certain processing of your information</li>
          <li><strong>Withdraw consent:</strong> withdraw consent for processing that requires your consent</li>
        </ul>
        <p className={pClass}>
          To exercise these rights, contact <a href="mailto:communication@cadence-ci.com" className="text-[#5B8A72] font-medium hover:underline">communication@cadence-ci.com</a>. We will respond within 30 days.
        </p>
      </div>

      <div className={sectionClass}>
        <h2 className={h2Class}>7. Cookies</h2>
        <p className={pClass}>
          We use cookies and similar technologies to authenticate users, remember preferences, and analyze usage. You can control cookies through your browser settings, but disabling cookies may affect your ability to use the Service.
        </p>
      </div>

      <div className={sectionClass}>
        <h2 className={h2Class}>8. International Users</h2>
        <p className={pClass}>
          Cadence is based in the United States. If you access the Service from outside the U.S., you acknowledge that your information will be transferred to and processed in the United States, which may have different data protection laws than your country.
        </p>
      </div>

      <div className={sectionClass}>
        <h2 className={h2Class}>9. Children's Privacy</h2>
        <p className={pClass}>
          The Service is not intended for children under 18. We do not knowingly collect personal information from children. If you believe a child has provided us with personal information, contact us at <a href="mailto:communication@cadence-ci.com" className="text-[#5B8A72] font-medium hover:underline">communication@cadence-ci.com</a> and we will delete it.
        </p>
      </div>

      <div className={sectionClass}>
        <h2 className={h2Class}>10. California Residents (CCPA/CPRA)</h2>
        <p className={pClass}>
          If you are a California resident, you have additional rights under the California Consumer Privacy Act, including the right to know what personal information we collect, the right to delete it, the right to opt out of any sale of personal information (we do not sell personal information), and the right to non-discrimination for exercising your rights.
        </p>
      </div>

      <div className={sectionClass}>
        <h2 className={h2Class}>11. Changes to This Policy</h2>
        <p className={pClass}>
          We may update this Privacy Policy periodically. Material changes will be communicated by email or through the Service at least 30 days before they take effect.
        </p>
      </div>

      <div className={sectionClass}>
        <h2 className={h2Class}>12. Contact</h2>
        <p className={pClass}>
          Questions about this Privacy Policy? Contact <a href="mailto:communication@cadence-ci.com" className="text-[#5B8A72] font-medium hover:underline">communication@cadence-ci.com</a>.
        </p>
      </div>
    </PublicPageLayout>
  )
}

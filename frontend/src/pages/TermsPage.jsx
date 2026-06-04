import React from 'react'
import PublicPageLayout from '../components/PublicPageLayout'
import SEO from '../components/SEO'

export default function TermsPage() {
  const sectionClass = "mb-8"
  const h2Class = "text-[18px] font-bold text-[#3D4A44] mb-3"
  const pClass = "text-[15px] text-[#5A6660] leading-relaxed mb-4"
  const ulClass = "list-disc pl-6 space-y-1.5 text-[15px] text-[#5A6660] leading-relaxed mb-4"

  return (
    <PublicPageLayout>
      <SEO
        path="/terms"
        title="Terms & Conditions"
        description="Cadence Catalog Intelligence Terms & Conditions governing use of the Cadence music catalog management and royalty intelligence platform."
        image="https://cadence-ci.com/terms-og.png"
      />
      <h1 className="text-[32px] sm:text-[40px] font-bold text-[#3D4A44] mb-2">Terms & Conditions</h1>
      <p className="text-[14px] text-[#7A8580] mb-10">Last Updated: April 14, 2026</p>

      <div className={sectionClass}>
        <h2 className={h2Class}>1. Introduction</h2>
        <p className={pClass}>
          Welcome to Cadence. These Terms and Conditions ("Terms") govern your access to and use of the Cadence platform, website, mobile applications, and related services (collectively, the "Service") provided by Cadence Catalog Intelligence Co., a Delaware corporation ("Cadence," "we," "us," or "our").
        </p>
        <p className={pClass}>
          By creating an account, accessing, or using the Service, you agree to be bound by these Terms. If you do not agree, do not use the Service.
        </p>
      </div>

      <div className={sectionClass}>
        <h2 className={h2Class}>2. Eligibility</h2>
        <p className={pClass}>
          You must be at least 18 years of age and have the legal capacity to enter into a binding contract. If you are using the Service on behalf of an organization, you represent that you have the authority to bind that organization to these Terms, and "you" will refer to both you individually and that organization.
        </p>
      </div>

      <div className={sectionClass}>
        <h2 className={h2Class}>3. Account Registration</h2>
        <p className={pClass}>To access most features, you must create an account. You agree to:</p>
        <ul className={ulClass}>
          <li>Provide accurate, current, and complete information during registration</li>
          <li>Maintain and promptly update your account information</li>
          <li>Keep your password secure and confidential</li>
          <li>Notify us immediately of any unauthorized access or security breach</li>
          <li>Accept responsibility for all activity that occurs under your account</li>
        </ul>
      </div>

      <div className={sectionClass}>
        <h2 className={h2Class}>4. Subscription Plans and Payment</h2>
        <p className={pClass}>
          Cadence offers several subscription tiers, including a free plan and paid plans. Current pricing is available at <strong>cadence-ci.com/pricing</strong>.
        </p>
        <p className={pClass}>
          Paid subscriptions are billed in advance on a monthly or annual basis. By subscribing, you authorize Cadence to charge the payment method on file for all applicable fees. Subscription fees are non-refundable except as expressly provided in these Terms or required by applicable law.
        </p>
        <p className={pClass}>
          We reserve the right to modify our pricing with at least 30 days' notice to active subscribers. Continued use of the Service after a price change constitutes acceptance of the new pricing.
        </p>
      </div>

      <div className={sectionClass}>
        <h2 className={h2Class}>5. Your Content and Data</h2>
        <p className={pClass}>
          You retain all ownership rights to the music catalogs, royalty statements, contracts, contact information, and other content you upload to the Service ("Your Content"). By using the Service, you grant Cadence a limited, non-exclusive, worldwide license to host, store, process, display, and transmit Your Content solely for the purpose of providing the Service to you.
        </p>
        <p className={pClass}>You represent and warrant that:</p>
        <ul className={ulClass}>
          <li>You own Your Content or have the necessary rights, licenses, consents, and permissions to upload it</li>
          <li>Your Content does not infringe on any third party's intellectual property, privacy, publicity, or other rights</li>
          <li>Your Content does not violate any applicable law or regulation</li>
          <li>You have the authority to grant the license described above</li>
        </ul>
        <p className={pClass}>
          Cadence does not claim ownership of Your Content. You can export Your Content at any time and delete your account to remove it from our active systems, subject to the backup retention periods described in our Privacy Policy.
        </p>
      </div>

      <div className={sectionClass}>
        <h2 className={h2Class}>6. Acceptable Use</h2>
        <p className={pClass}>You agree not to use the Service to:</p>
        <ul className={ulClass}>
          <li>Upload, store, or transmit content that infringes on the intellectual property rights of others</li>
          <li>Impersonate any person or entity, or misrepresent your affiliation with a person or entity</li>
          <li>Upload malicious code, viruses, or any other harmful software</li>
          <li>Attempt to gain unauthorized access to the Service, other user accounts, or related systems</li>
          <li>Interfere with or disrupt the integrity or performance of the Service</li>
          <li>Use the Service for any illegal, fraudulent, or unauthorized purpose</li>
          <li>Scrape, harvest, or extract data through automated means without our express written permission</li>
          <li>Resell, sublicense, or redistribute the Service without authorization</li>
          <li>Violate the privacy rights of others</li>
        </ul>
        <p className={pClass}>
          Violation of this section may result in immediate suspension or termination of your account.
        </p>
      </div>

      <div className={sectionClass}>
        <h2 className={h2Class}>7. Intellectual Property</h2>
        <p className={pClass}>
          The Service, including all software, design, text, graphics, logos, and other content created by Cadence, is the property of Cadence Catalog Intelligence Co. and is protected by United States and international copyright, trademark, and other intellectual property laws. You may not copy, modify, distribute, sell, or lease any part of the Service without our prior written consent. The "Cadence" name and logo are trademarks of Cadence Catalog Intelligence Co.
        </p>
      </div>

      <div className={sectionClass}>
        <h2 className={h2Class}>8. Third-Party Integrations</h2>
        <p className={pClass}>
          The Service may integrate with third-party services such as Spotify, Dropbox, Google Drive, Luminate, and others. Your use of those third-party services is governed by their own terms of service and privacy policies. Cadence is not responsible for the availability, accuracy, or practices of any third-party service.
        </p>
      </div>

      <div className={sectionClass}>
        <h2 className={h2Class}>9. Service Availability and Modifications</h2>
        <p className={pClass}>
          We strive to provide reliable, continuous access to the Service, but we do not guarantee uninterrupted availability. We may modify, suspend, or discontinue any part of the Service at any time, with or without notice. We are not liable for any loss or damage resulting from such changes.
        </p>
      </div>

      <div className={sectionClass}>
        <h2 className={h2Class}>10. Termination</h2>
        <p className={pClass}>
          You may terminate your account at any time through the Service settings or by contacting support. We may suspend or terminate your access to the Service at any time, with or without cause, if you violate these Terms or if we determine that your use poses a risk to Cadence, other users, or the integrity of the Service.
        </p>
        <p className={pClass}>
          Upon termination, your right to access the Service will cease immediately. You will have 30 days to export Your Content before it is permanently deleted, subject to backup retention periods.
        </p>
      </div>

      <div className={sectionClass}>
        <h2 className={h2Class}>11. Disclaimers</h2>
        <p className={`${pClass} uppercase text-[13px] font-medium`}>
          THE SERVICE IS PROVIDED "AS IS" AND "AS AVAILABLE" WITHOUT WARRANTIES OF ANY KIND, EITHER EXPRESS OR IMPLIED. TO THE FULLEST EXTENT PERMITTED BY LAW, CADENCE DISCLAIMS ALL WARRANTIES, INCLUDING BUT NOT LIMITED TO IMPLIED WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, AND NON-INFRINGEMENT.
        </p>
        <p className={pClass}>
          Cadence does not warrant that the Service will be error-free, secure, or uninterrupted, or that any data produced by the Service (including catalog valuations, royalty calculations, or audit reports) will be accurate or complete. You are responsible for verifying all outputs before relying on them for business decisions.
        </p>
      </div>

      <div className={sectionClass}>
        <h2 className={h2Class}>12. Limitation of Liability</h2>
        <p className={`${pClass} uppercase text-[13px] font-medium`}>
          TO THE FULLEST EXTENT PERMITTED BY LAW, CADENCE AND ITS OFFICERS, DIRECTORS, EMPLOYEES, AND AFFILIATES SHALL NOT BE LIABLE FOR ANY INDIRECT, INCIDENTAL, SPECIAL, CONSEQUENTIAL, OR PUNITIVE DAMAGES ARISING OUT OF OR RELATING TO YOUR USE OF THE SERVICE.
        </p>
        <p className={`${pClass} uppercase text-[13px] font-medium`}>
          OUR TOTAL AGGREGATE LIABILITY FOR ANY CLAIMS ARISING OUT OF OR RELATING TO THESE TERMS OR THE SERVICE SHALL NOT EXCEED THE GREATER OF (A) THE AMOUNT YOU PAID TO CADENCE IN THE TWELVE (12) MONTHS PRECEDING THE CLAIM, OR (B) ONE HUNDRED DOLLARS ($100).
        </p>
      </div>

      <div className={sectionClass}>
        <h2 className={h2Class}>13. Indemnification</h2>
        <p className={pClass}>
          You agree to indemnify, defend, and hold harmless Cadence and its officers, directors, employees, and affiliates from any claims, damages, losses, liabilities, and expenses (including reasonable attorneys' fees) arising out of or relating to (a) your use of the Service, (b) Your Content, (c) your violation of these Terms, or (d) your violation of any third party's rights.
        </p>
      </div>

      <div className={sectionClass}>
        <h2 className={h2Class}>14. Governing Law and Dispute Resolution</h2>
        <p className={pClass}>
          These Terms are governed by the laws of the State of Delaware, without regard to conflict of law principles. Any dispute arising out of or relating to these Terms or the Service shall be resolved through binding arbitration administered by the American Arbitration Association under its Commercial Arbitration Rules, with the arbitration taking place in Wilmington, Delaware.
        </p>
        <p className={pClass}>
          You waive any right to participate in a class action lawsuit or class-wide arbitration against Cadence.
        </p>
      </div>

      <div className={sectionClass}>
        <h2 className={h2Class}>15. Changes to These Terms</h2>
        <p className={pClass}>
          We may update these Terms from time to time. We will notify you of material changes by email or through the Service at least 30 days before they take effect. Your continued use of the Service after the effective date constitutes acceptance of the updated Terms.
        </p>
      </div>

      <div className={sectionClass}>
        <h2 className={h2Class}>16. Contact</h2>
        <p className={pClass}>
          Questions about these Terms? Contact us at{' '}
          <a href="mailto:communication@cadence-ci.com" className="text-[#5B8A72] font-medium hover:underline">communication@cadence-ci.com</a>{' '}
          or write to:
        </p>
        <p className="text-[15px] text-[#5A6660] leading-relaxed">
          Cadence Catalog Intelligence Co.<br />
          c/o Republic Registered Agent LLC<br />
          262 Chapman Rd, Ste 240<br />
          Newark, DE 19702
        </p>
      </div>
    </PublicPageLayout>
  )
}

import React from 'react'
import PublicPageLayout from '../components/PublicPageLayout'

export default function BetaTermsPage() {
  const sectionClass = "mb-8"
  const h2Class = "text-[18px] font-bold text-[#3D4A44] mb-3"
  const pClass = "text-[15px] text-[#5A6660] leading-relaxed mb-4"
  const ulClass = "list-disc pl-6 space-y-1.5 text-[15px] text-[#5A6660] leading-relaxed mb-4"

  return (
    <PublicPageLayout>
      <h1 className="text-[32px] sm:text-[40px] font-bold text-[#3D4A44] mb-2">Beta Terms & Conditions</h1>
      <p className="text-[14px] text-[#7A8580] mb-4">Last Updated: April 14, 2026</p>
      <p className={pClass}>
        These Beta Terms & Conditions ("Beta Terms") govern your access to and use of the Cadence platform during its pre-release beta period. These Beta Terms supplement the main Terms & Conditions and apply specifically to participants in the Cadence Beta Program. If there is any conflict between these Beta Terms and the main Terms & Conditions, these Beta Terms control with respect to beta participation.
      </p>
      <p className={pClass}>
        By accessing Cadence during the beta period, you ("Beta Participant," "you") agree to be bound by these Beta Terms. If you do not agree, do not access the beta.
      </p>

      <div className={sectionClass}>
        <h2 className={h2Class}>1. Nature of the Beta</h2>
        <p className={pClass}>
          Cadence is currently in a pre-release beta phase. The Service is provided for testing, evaluation, and feedback purposes only. You understand and agree that:
        </p>
        <ul className={ulClass}>
          <li>The Service is a work in progress and is not a finished product</li>
          <li>Features may be added, modified, or removed without notice</li>
          <li>The Service may contain bugs, errors, performance issues, or inaccurate results</li>
          <li>Catalog valuations, royalty calculations, audit reports, and other outputs should be treated as experimental and verified independently before being used for any business, financial, or legal decision</li>
          <li>Scheduled and unscheduled downtime may occur</li>
          <li>Data loss is possible, and you should maintain your own backups of anything critical</li>
        </ul>
        <p className={pClass}>
          The beta is not a substitute for production-grade software. Do not rely on Cadence as your sole system of record during the beta period.
        </p>
      </div>

      <div className={sectionClass}>
        <h2 className={h2Class}>2. No Fees During Beta</h2>
        <p className={pClass}>
          Access to Cadence during the beta period is provided free of charge. You will not be billed for beta access. However:
        </p>
        <ul className={ulClass}>
          <li>Free beta access is a courtesy, not an entitlement, and does not grant you any rights to continued free access after the beta period ends</li>
          <li>Free beta access does not grant you a license to, or any right to use, any paid features, tiers, or add-ons of Cadence when the Service transitions to general availability</li>
          <li>When Cadence launches publicly, you will be required to select and pay for a subscription tier in order to continue using the Service</li>
          <li>Cadence reserves the right to introduce, modify, or remove paid tiers at its sole discretion, and no beta participant is guaranteed any specific pricing, feature set, or grandfathered plan</li>
        </ul>
      </div>

      <div className={sectionClass}>
        <h2 className={h2Class}>3. Feedback</h2>
        <p className={pClass}>
          A core purpose of the beta is to gather feedback. By participating, you agree to provide feedback, bug reports, and suggestions when requested, through the channels Cadence designates (in-app forms, email, scheduled calls, or surveys).
        </p>
        <p className={pClass}>
          You grant Cadence a perpetual, irrevocable, worldwide, royalty-free license to use, modify, incorporate, and commercialize any feedback, suggestions, ideas, or improvements you provide, without obligation to compensate or credit you. Nothing in this section transfers ownership of Your Content — only feedback about the Service itself.
        </p>
      </div>

      <div className={sectionClass}>
        <h2 className={h2Class}>4. Confidentiality</h2>
        <p className={pClass}>
          As a Beta Participant, you will have access to non-public information about Cadence, including unreleased features, user interface designs, product roadmaps, pricing strategies, technical architecture, and business plans (collectively, "Confidential Information").
        </p>
        <p className={pClass}>You agree to:</p>
        <ul className={ulClass}>
          <li>Keep all Confidential Information strictly confidential and not disclose it to any third party</li>
          <li>Not publish screenshots, screen recordings, demo videos, or written descriptions of the Service on social media, blogs, forums, or any public platform without Cadence's prior written consent</li>
          <li>Not discuss unreleased features, roadmap items, or internal product details with anyone outside your organization</li>
          <li>Not use Confidential Information for any purpose other than evaluating and providing feedback on the Service</li>
          <li>Protect Confidential Information with at least the same degree of care you would use to protect your own confidential information, and in no event less than a reasonable standard of care</li>
        </ul>
        <p className={pClass}>
          Confidential Information does not include information that is (a) already publicly available through no fault of yours, (b) independently developed by you without reference to Confidential Information, or (c) required to be disclosed by court order or applicable law (in which case you must notify Cadence in advance if legally permitted).
        </p>
        <p className={pClass}>
          The confidentiality obligations in this section survive termination of your beta participation and remain in effect until Cadence publicly launches or publicly discloses the relevant information.
        </p>
      </div>

      <div className={sectionClass}>
        <h2 className={h2Class}>5. Permitted Public Statements</h2>
        <p className={pClass}>You may make the following public statements without prior written consent from Cadence:</p>
        <ul className={ulClass}>
          <li>The fact that you are participating in the Cadence beta</li>
          <li>General, non-specific descriptions of Cadence as "a music catalog management platform" or similar neutral descriptions</li>
          <li>Your overall impression of Cadence once the Service has launched publicly</li>
        </ul>
        <p className={pClass}>
          Any other public statements, screenshots, or detailed discussions of the Service require advance written approval from Cadence at <a href="mailto:communication@cadence-ci.com" className="text-[#5B8A72] font-medium hover:underline">communication@cadence-ci.com</a>.
        </p>
      </div>

      <div className={sectionClass}>
        <h2 className={h2Class}>6. Data During Beta</h2>
        <p className={pClass}>
          Catalog data, royalty statements, contracts, and other content you upload during the beta are treated under the main Privacy Policy with one important caveat: because the Service is under active development, we cannot guarantee the same level of data durability or availability that a production service would provide.
        </p>
        <p className={pClass}>You acknowledge that:</p>
        <ul className={ulClass}>
          <li>Data may be migrated, restructured, or temporarily unavailable as we ship updates</li>
          <li>Scheduled database resets are possible (though we will provide advance notice whenever feasible)</li>
          <li>You are responsible for maintaining independent backups of any critical data</li>
          <li>Cadence is not liable for any data loss, corruption, or unavailability during the beta period</li>
        </ul>
        <p className={pClass}>
          When Cadence transitions out of beta into general availability, we will make reasonable efforts to preserve your catalog data in your account, but this is not guaranteed and may depend on the tier you choose at that time.
        </p>
      </div>

      <div className={sectionClass}>
        <h2 className={h2Class}>7. Beta Term and Termination</h2>
        <p className={pClass}>
          The beta period begins when you receive access credentials and ends on the earlier of (a) the public launch of Cadence, (b) the date Cadence notifies you that the beta has ended, or (c) termination of your beta access.
        </p>
        <p className={pClass}>
          Cadence may terminate your beta access at any time, for any reason or no reason, with or without notice. You may stop participating in the beta at any time by contacting <a href="mailto:communication@cadence-ci.com" className="text-[#5B8A72] font-medium hover:underline">communication@cadence-ci.com</a>.
        </p>
        <p className={pClass}>
          Upon termination of beta access, your right to use the Service ceases immediately. You will have 30 days to export Your Content before it is removed from active systems. Confidentiality obligations survive termination.
        </p>
      </div>

      <div className={sectionClass}>
        <h2 className={h2Class}>8. No Warranty, No Liability</h2>
        <p className={`${pClass} uppercase text-[13px] font-medium`}>
          THE BETA SERVICE IS PROVIDED "AS IS" AND "AS AVAILABLE" WITH ALL FAULTS AND WITHOUT WARRANTY OF ANY KIND. CADENCE MAKES NO REPRESENTATIONS OR WARRANTIES, EXPRESS OR IMPLIED, REGARDING THE BETA SERVICE, INCLUDING ANY WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, ACCURACY, OR NON-INFRINGEMENT.
        </p>
        <p className={`${pClass} uppercase text-[13px] font-medium`}>
          TO THE FULLEST EXTENT PERMITTED BY LAW, CADENCE AND ITS OFFICERS, DIRECTORS, EMPLOYEES, AND AFFILIATES SHALL NOT BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, CONSEQUENTIAL, OR PUNITIVE DAMAGES ARISING OUT OF OR RELATING TO YOUR PARTICIPATION IN THE BETA, INCLUDING BUT NOT LIMITED TO DATA LOSS, LOST PROFITS, LOST OPPORTUNITIES, OR BUSINESS INTERRUPTION, EVEN IF CADENCE HAS BEEN ADVISED OF THE POSSIBILITY OF SUCH DAMAGES.
        </p>
        <p className={`${pClass} uppercase text-[13px] font-medium`}>
          BY PARTICIPATING IN THE BETA, YOU EXPRESSLY ASSUME THE RISK OF USING EXPERIMENTAL SOFTWARE.
        </p>
      </div>

      <div className={sectionClass}>
        <h2 className={h2Class}>9. Transition to General Availability</h2>
        <p className={pClass}>When Cadence transitions from beta to general availability ("GA"):</p>
        <ul className={ulClass}>
          <li>Beta Participants will be notified in advance</li>
          <li>You will be required to accept the main Terms & Conditions and select a subscription tier to continue using the Service</li>
          <li>Cadence may, at its sole discretion, offer Beta Participants promotional pricing, early-access windows, or other incentives, but no such offers are guaranteed by these Beta Terms</li>
          <li>Any data retention beyond the beta is subject to your selection of a paid tier and compliance with the main Terms & Conditions</li>
        </ul>
      </div>

      <div className={sectionClass}>
        <h2 className={h2Class}>10. Relationship to Main Terms</h2>
        <p className={pClass}>
          Except as expressly modified by these Beta Terms, all provisions of the main Cadence Terms & Conditions apply to your beta participation, including sections on acceptable use, intellectual property, indemnification, governing law, and dispute resolution.
        </p>
      </div>

      <div className={sectionClass}>
        <h2 className={h2Class}>11. Changes to These Beta Terms</h2>
        <p className={pClass}>
          Cadence may update these Beta Terms at any time during the beta period. Material changes will be communicated by email or through the Service. Continued participation in the beta after changes take effect constitutes acceptance.
        </p>
      </div>

      <div className={sectionClass}>
        <h2 className={h2Class}>12. Contact</h2>
        <p className={pClass}>
          Questions about the beta or these Beta Terms? Contact <a href="mailto:communication@cadence-ci.com" className="text-[#5B8A72] font-medium hover:underline">communication@cadence-ci.com</a>.
        </p>
      </div>
    </PublicPageLayout>
  )
}

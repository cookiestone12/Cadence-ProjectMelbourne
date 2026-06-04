import React from 'react'
import PublicPageLayout from '../components/PublicPageLayout'
import SEO from '../components/SEO'

export default function ContentPolicyPage() {
  const sectionClass = "mb-8"
  const h2Class = "text-[18px] font-bold text-[#3D4A44] mb-3"
  const h3Class = "text-[15px] font-semibold text-[#3D4A44] mb-2"
  const pClass = "text-[15px] text-[#5A6660] leading-relaxed mb-4"
  const ulClass = "list-disc pl-6 space-y-1.5 text-[15px] text-[#5A6660] leading-relaxed mb-4"

  return (
    <PublicPageLayout>
      <SEO
        path="/content-policy"
        title="Content Policy"
        description="Cadence Catalog Intelligence's content policy describing acceptable use of the platform for music catalog management, rights administration, and royalty processing."
        image="https://cadence-ci.com/content-policy-og.png"
      />
      <h1 className="text-[32px] sm:text-[40px] font-bold text-[#3D4A44] mb-2">Content Policy</h1>
      <p className="text-[14px] text-[#7A8580] mb-4">Last Updated: April 14, 2026</p>
      <p className={pClass}>
        Cadence Catalog Intelligence Co. ("Cadence") provides a platform for managing music catalogs, rights, royalties, and related business operations. This Content Policy describes what content is permitted on the platform and what is prohibited.
      </p>

      <div className={sectionClass}>
        <h2 className={h2Class}>1. Permitted Content</h2>
        <p className={pClass}>You may upload the following types of content to Cadence, provided you have the necessary rights:</p>
        <ul className={ulClass}>
          <li><strong>Music metadata:</strong> song titles, artist names, ISRCs, ISWCs, release dates, genre, mood, BPM, key, and other descriptive data</li>
          <li><strong>Audio files:</strong> masters, demos, instrumentals, stems, and reference recordings for catalog management and sync pitching purposes</li>
          <li><strong>Rights documentation:</strong> contracts, split sheets, licensing agreements, Schedule A documents, and registration records</li>
          <li><strong>Royalty statements:</strong> statements from BMI, ASCAP, SESAC, GMR, the MLC, SoundExchange, distributors, sub-publishers, and other collection societies</li>
          <li><strong>Contact information:</strong> industry contact directories for business purposes (subject to applicable privacy laws)</li>
          <li><strong>Creative and marketing materials:</strong> artwork, press photos, bios, and other assets used to promote your catalog</li>
        </ul>
      </div>

      <div className={sectionClass}>
        <h2 className={h2Class}>2. Prohibited Content</h2>
        <p className={pClass}>You may not upload, store, or transmit the following content on Cadence:</p>

        <h3 className={h3Class}>Infringing Content</h3>
        <ul className={ulClass}>
          <li>Music, recordings, compositions, or audio files that you do not own or have not been authorized to manage</li>
          <li>Unauthorized samples, interpolations, or derivative works</li>
          <li>Bootlegs, leaked material, or unreleased content belonging to third parties</li>
          <li>Content obtained through hacking, theft, or unauthorized access</li>
        </ul>

        <h3 className={h3Class}>Illegal or Harmful Content</h3>
        <ul className={ulClass}>
          <li>Content that violates any applicable law or regulation</li>
          <li>Child sexual abuse material (CSAM) in any form — Cadence has zero tolerance and reports to NCMEC and law enforcement</li>
          <li>Content that promotes or facilitates violence, terrorism, or criminal activity</li>
          <li>Content that harasses, threatens, defames, or endangers any individual</li>
        </ul>

        <h3 className={h3Class}>Deceptive Content</h3>
        <ul className={ulClass}>
          <li>Falsified contracts, split sheets, or ownership documentation</li>
          <li>Altered or fabricated royalty statements</li>
          <li>Impersonation of artists, songwriters, publishers, or other rights holders</li>
          <li>Misrepresentation of catalog ownership or authority</li>
        </ul>

        <h3 className={h3Class}>Malicious or Technical Abuse</h3>
        <ul className={ulClass}>
          <li>Malware, viruses, or other harmful code</li>
          <li>Content designed to exploit vulnerabilities in the Service or third-party integrations</li>
          <li>Data scraped from other platforms in violation of their terms of service</li>
        </ul>

        <h3 className={h3Class}>Privacy Violations</h3>
        <ul className={ulClass}>
          <li>Personal information of individuals without a lawful business purpose and, where required, consent</li>
          <li>Private communications shared without authorization</li>
          <li>Content that violates any applicable privacy or data protection law</li>
        </ul>
      </div>

      <div className={sectionClass}>
        <h2 className={h2Class}>3. Audio File Guidelines</h2>
        <p className={pClass}>When uploading audio files for catalog management, sync pitching, or storage:</p>
        <ul className={ulClass}>
          <li>You must hold the necessary master and publishing rights, or have written permission from the rights holders</li>
          <li>Audio files should be properly tagged with accurate metadata</li>
          <li>Files are stored for catalog management and sync business purposes only — not for public streaming or distribution</li>
          <li>Cadence does not operate as a distributor, DSP, or public-facing music service</li>
        </ul>
      </div>

      <div className={sectionClass}>
        <h2 className={h2Class}>4. Enforcement</h2>
        <p className={pClass}>
          Cadence reviews content when flagged, reported, or detected by automated systems. If we determine that content violates this policy, we may:
        </p>
        <ul className={ulClass}>
          <li>Remove the offending content</li>
          <li>Suspend or terminate the account</li>
          <li>Notify affected rights holders</li>
          <li>Report illegal content to law enforcement</li>
          <li>Cooperate with legal investigations</li>
        </ul>
        <p className={pClass}>
          We reserve the right to make enforcement decisions in our sole discretion, including in cases not explicitly listed above.
        </p>
      </div>

      <div className={sectionClass}>
        <h2 className={h2Class}>5. Reporting Violations</h2>
        <p className={pClass}>
          To report content that violates this policy, contact <a href="mailto:communication@cadence-ci.com" className="text-[#5B8A72] font-medium hover:underline">communication@cadence-ci.com</a>. For copyright-specific claims, see our DMCA Policy for the correct procedure to submit a takedown notice.
        </p>
      </div>

      <div className={sectionClass}>
        <h2 className={h2Class}>6. Changes to This Policy</h2>
        <p className={pClass}>
          We may update this Content Policy from time to time. Material changes will be communicated through the Service.
        </p>
      </div>
    </PublicPageLayout>
  )
}

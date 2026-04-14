import React from 'react'
import { useNavigate } from 'react-router-dom'

export default function PublicFooter() {
  const navigate = useNavigate()

  const linkClass = "text-[13px] text-[#9CA8A1] hover:text-white transition-colors cursor-pointer"
  const headingClass = "text-[11px] font-semibold tracking-[0.15em] uppercase text-[#7A8580] mb-4"

  return (
    <footer className="bg-[#1A2420] border-t border-[rgba(59,77,67,0.15)]">
      <div className="max-w-6xl mx-auto px-6 py-14">
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-10 mb-12">
          <div className="col-span-2 sm:col-span-1">
            <img src="/cadence-logo-full.png" alt="Cadence" className="h-8 w-auto brightness-0 invert opacity-60 mb-4" />
            <p className="text-[13px] text-[#7A8580] leading-relaxed max-w-[220px]">
              The operating system for modern music catalogs.
            </p>
          </div>

          <div>
            <h4 className={headingClass}>Company</h4>
            <ul className="space-y-2.5">
              <li><button onClick={() => navigate('/about')} className={linkClass}>About Cadence</button></li>
              <li><button onClick={() => navigate('/careers')} className={linkClass}>Careers</button></li>
              <li><button onClick={() => navigate('/investors')} className={linkClass}>Investors</button></li>
            </ul>
          </div>

          <div>
            <h4 className={headingClass}>Legal</h4>
            <ul className="space-y-2.5">
              <li><button onClick={() => navigate('/terms')} className={linkClass}>Terms & Conditions</button></li>
              <li><button onClick={() => navigate('/privacy')} className={linkClass}>Privacy Policy</button></li>
              <li><button onClick={() => navigate('/anti-fraud')} className={linkClass}>Anti-Fraud Policy</button></li>
              <li><button onClick={() => navigate('/content-policy')} className={linkClass}>Content Policy</button></li>
              <li><button onClick={() => navigate('/beta-terms')} className={linkClass}>Beta Terms</button></li>
            </ul>
          </div>

          <div>
            <h4 className={headingClass}>Resources</h4>
            <ul className="space-y-2.5">
              <li><button onClick={() => navigate('/help')} className={linkClass}>Help Center</button></li>
              <li><a href="mailto:communication@cadence-ci.com" className={linkClass}>Contact Us</a></li>
            </ul>
          </div>
        </div>

        <div className="border-t border-[rgba(255,255,255,0.06)] pt-6 flex flex-col sm:flex-row items-center justify-between gap-4">
          <p className="text-[12px] text-[#5A6660]">
            &copy; {new Date().getFullYear()} Cadence Catalog Intelligence Co. All rights reserved.
          </p>
          <p className="text-[12px] text-[#5A6660]">
            Delaware C-Corp &middot; Atlanta, GA
          </p>
        </div>
      </div>
    </footer>
  )
}

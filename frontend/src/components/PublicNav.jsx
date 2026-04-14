import React from 'react'
import { useNavigate } from 'react-router-dom'

export default function PublicNav() {
  const navigate = useNavigate()

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 bg-[#FAFBF9]/80 backdrop-blur-xl border-b border-[rgba(59,77,67,0.06)]">
      <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
        <div className="flex items-center cursor-pointer" onClick={() => navigate('/')}>
          <img src="/cadence-logo-full.png" alt="Cadence - Catalog Intelligence" className="h-12 w-auto" />
        </div>
        <div className="flex items-center gap-4">
          <button
            onClick={() => navigate('/careers')}
            className="hidden sm:inline-flex text-[14px] font-medium text-[#7A8580] hover:text-[#5B8A72] transition-colors"
          >
            Careers
          </button>
          <button
            onClick={() => navigate('/investors')}
            className="hidden sm:inline-flex text-[14px] font-medium text-[#7A8580] hover:text-[#5B8A72] transition-colors"
          >
            Investors
          </button>
          <button
            onClick={() => navigate('/login')}
            className="text-[14px] font-medium text-[#5B8A72] hover:text-[#4A7A62] transition-colors px-4 py-2 rounded-full hover:bg-[#5B8A72]/8"
          >
            Sign In
          </button>
        </div>
      </div>
    </nav>
  )
}

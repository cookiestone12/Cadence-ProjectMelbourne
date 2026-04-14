import React from 'react'
import PublicNav from './PublicNav'
import PublicFooter from './PublicFooter'

export default function PublicPageLayout({ children }) {
  return (
    <div className="min-h-screen bg-[#FAFBF9] flex flex-col">
      <PublicNav />
      <main className="flex-1 pt-24 pb-16 px-6">
        <div className="max-w-3xl mx-auto">
          {children}
        </div>
      </main>
      <PublicFooter />
    </div>
  )
}

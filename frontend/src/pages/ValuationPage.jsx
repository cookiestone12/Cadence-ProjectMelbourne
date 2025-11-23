import React from 'react'
import { CurrencyDollarIcon } from '@heroicons/react/24/outline'

export default function ValuationPage() {
  return (
    <div className="p-8">
      <div className="mb-8">
        <h1 className="text-4xl font-bold text-gray-900 mb-2">Valuation</h1>
        <p className="text-gray-600">Catalog valuation powered by Luminate</p>
      </div>
      
      <div className="bg-gradient-to-br from-purple-50 to-pink-50 rounded-xl shadow-sm p-12 text-center">
        <div className="inline-flex items-center justify-center w-20 h-20 bg-gradient-to-r from-purple-500 to-pink-500 rounded-full mb-6">
          <CurrencyDollarIcon className="w-10 h-10 text-white" />
        </div>
        
        <h2 className="text-2xl font-bold text-gray-900 mb-3">Coming Soon</h2>
        <p className="text-gray-600 max-w-2xl mx-auto mb-6">
          Catalog valuation features powered by Luminate data are currently in development. 
          Soon you'll be able to view real-time valuations, market trends, and revenue forecasts 
          for your entire catalog.
        </p>
        
        <div className="inline-flex items-center space-x-2 text-sm text-purple-600">
          <div className="w-2 h-2 bg-purple-600 rounded-full animate-pulse"></div>
          <span>Integration with Luminate in progress</span>
        </div>
      </div>
      
      <div className="mt-8 grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-white rounded-xl shadow-sm p-6">
          <h3 className="font-bold text-gray-900 mb-2">Portfolio Value</h3>
          <p className="text-sm text-gray-500 mb-3">Estimated market value of your entire catalog</p>
          <div className="text-2xl font-bold text-gray-300">$--</div>
        </div>
        
        <div className="bg-white rounded-xl shadow-sm p-6">
          <h3 className="font-bold text-gray-900 mb-2">30-Day Revenue</h3>
          <p className="text-sm text-gray-500 mb-3">Projected revenue for the next 30 days</p>
          <div className="text-2xl font-bold text-gray-300">$--</div>
        </div>
        
        <div className="bg-white rounded-xl shadow-sm p-6">
          <h3 className="font-bold text-gray-900 mb-2">YoY Growth</h3>
          <p className="text-sm text-gray-500 mb-3">Year-over-year catalog value growth</p>
          <div className="text-2xl font-bold text-gray-300">--%</div>
        </div>
      </div>
    </div>
  )
}

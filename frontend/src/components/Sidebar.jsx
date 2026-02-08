import React, { useState, useEffect } from 'react'
import { Link, useLocation } from 'react-router-dom'
import axios from 'axios'
import { 
  HomeIcon, 
  MagnifyingGlassIcon,
  UsersIcon, 
  MusicalNoteIcon, 
  DocumentTextIcon,
  RectangleStackIcon,
  ChartBarIcon,
  CurrencyDollarIcon,
  Cog6ToothIcon,
  XMarkIcon,
  ShieldCheckIcon,
  ClipboardDocumentListIcon,
  ClipboardDocumentCheckIcon,
  BanknotesIcon,
  FilmIcon,
  BuildingOfficeIcon
} from '@heroicons/react/24/outline'
import NotificationBell from './NotificationBell'

export default function Sidebar({ user, onLogout, isOpen, onClose }) {
  const location = useLocation()
  const [orgBranding, setOrgBranding] = useState(null)
  const [isOrgAdmin, setIsOrgAdmin] = useState(false)

  useEffect(() => {
    const fetchOrgData = async () => {
      try {
        const [orgRes, memberRes] = await Promise.all([
          axios.get('/api/organizations/current'),
          axios.get('/api/organizations/current/membership')
        ])
        setOrgBranding(orgRes.data)
        setIsOrgAdmin(memberRes.data.role === 'OWNER' || memberRes.data.role === 'ADMIN')
      } catch {}
    }
    fetchOrgData()
  }, [])

  const isActive = (path) => {
    if (path === '/') return location.pathname === '/'
    return location.pathname.startsWith(path)
  }
  
  const navItems = [
    { path: '/', label: 'Home', icon: HomeIcon },
    { path: '/search', label: 'Search', icon: MagnifyingGlassIcon },
    { path: '/roster', label: 'Roster', icon: UsersIcon },
    { path: '/catalog', label: 'Catalog', icon: MusicalNoteIcon },
    { path: '/works', label: 'Works', icon: DocumentTextIcon },
    { path: '/releases', label: 'Releases', icon: RectangleStackIcon },
    { path: '/contracts', label: 'Contracts', icon: ClipboardDocumentListIcon },
    { path: '/actions', label: 'Actions', icon: ClipboardDocumentCheckIcon },
    { path: '/royalties', label: 'Royalties', icon: BanknotesIcon },
    { path: '/placements', label: 'Placements', icon: FilmIcon },
    { path: '/reports', label: 'Reports', icon: ChartBarIcon },
    { path: '/valuation', label: 'Valuation', icon: CurrencyDollarIcon },
  ]
  
  return (
    <>
      {isOpen && (
        <div 
          className="fixed inset-0 bg-black/20 backdrop-blur-sm z-40 lg:hidden transition-opacity duration-200"
          onClick={onClose}
        />
      )}
      
      <div className={`
        fixed lg:relative inset-y-0 left-0 z-50
        h-screen w-64 bg-white/95 backdrop-blur-xl
        flex flex-col border-r border-am-separator
        transform transition-transform duration-200 ease-am
        ${isOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}
      `}>
        <div className="p-5 border-b border-am-separator">
          <div className="flex items-center justify-between">
            <div className="flex items-center">
              {orgBranding?.logo_url ? (
                <img 
                  src={orgBranding.logo_url} 
                  alt={orgBranding.display_name || orgBranding.name || 'Rythm'} 
                  className="h-12 w-auto object-contain"
                />
              ) : (
                <img 
                  src="/rythm-logo.png" 
                  alt="Rythm - Catalog Intelligence" 
                  className="h-28 w-auto object-contain"
                />
              )}
            </div>
            <button
              onClick={onClose}
              className="lg:hidden w-9 h-9 flex items-center justify-center rounded-full text-am-text-secondary hover:text-am-text hover:bg-am-subtle transition-all duration-150"
            >
              <XMarkIcon className="w-5 h-5" />
            </button>
          </div>
        </div>
      
        <nav className="flex-1 px-3 py-4 space-y-0.5 overflow-y-auto">
          {navItems.map((item) => {
            const Icon = item.icon
            const active = isActive(item.path)
            
            return (
              <Link
                key={item.path}
                to={item.path}
                onClick={() => window.innerWidth < 1024 && onClose()}
                className={`
                  flex items-center gap-3 px-3 py-2.5 rounded-xl
                  transition-all duration-150 ease-am
                  ${active 
                    ? 'bg-gradient-to-r from-am-accent to-am-accent-light text-white shadow-am-button' 
                    : 'text-am-text hover:bg-am-subtle'
                  }
                `}
              >
                <Icon className={`w-[22px] h-[22px] ${active ? 'stroke-[1.8]' : 'stroke-[1.5]'}`} />
                <span className={`text-[15px] ${active ? 'font-semibold' : 'font-medium'}`}>{item.label}</span>
              </Link>
            )
          })}
        </nav>
      
        <div className="p-3 border-t border-am-separator space-y-1">
          <div className="flex items-center gap-3 px-3 py-2.5">
            <div className="w-9 h-9 rounded-full bg-gradient-to-br from-am-accent to-am-accent-light flex items-center justify-center text-[14px] font-semibold text-white shadow-am-sm">
              {user?.username?.charAt(0).toUpperCase() || 'U'}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-[14px] font-medium text-am-text truncate">{user?.username || 'User'}</p>
              <p className="text-[12px] text-am-text-secondary">{user?.is_super_admin ? 'Super Admin' : user?.is_admin ? 'Admin' : 'Member'}</p>
            </div>
            <NotificationBell />
          </div>
          
          {user?.is_super_admin ? (
            <Link
              to="/admin"
              onClick={() => window.innerWidth < 1024 && onClose()}
              className={`
                flex items-center gap-3 px-3 py-2.5 rounded-xl
                transition-all duration-150 ease-am
                ${isActive('/admin')
                  ? 'bg-am-info/10 text-am-info font-medium'
                  : 'text-am-text-secondary hover:bg-am-subtle hover:text-am-text'
                }
              `}
            >
              <ShieldCheckIcon className="w-[20px] h-[20px] stroke-[1.5]" />
              <span className="text-[14px]">Master Admin</span>
            </Link>
          ) : isOrgAdmin ? (
            <Link
              to="/org-admin"
              onClick={() => window.innerWidth < 1024 && onClose()}
              className={`
                flex items-center gap-3 px-3 py-2.5 rounded-xl
                transition-all duration-150 ease-am
                ${isActive('/org-admin')
                  ? 'bg-am-accent/10 text-am-accent font-medium'
                  : 'text-am-text-secondary hover:bg-am-subtle hover:text-am-text'
                }
              `}
            >
              <BuildingOfficeIcon className="w-[20px] h-[20px] stroke-[1.5]" />
              <span className="text-[14px]">Org Admin</span>
            </Link>
          ) : null}
          
          <Link
            to="/settings"
            onClick={() => window.innerWidth < 1024 && onClose()}
            className={`
              flex items-center gap-3 px-3 py-2.5 rounded-xl
              transition-all duration-150 ease-am
              ${isActive('/settings')
                ? 'bg-am-subtle text-am-accent font-medium'
                : 'text-am-text-secondary hover:bg-am-subtle hover:text-am-text'
              }
            `}
          >
            <Cog6ToothIcon className="w-[20px] h-[20px] stroke-[1.5]" />
            <span className="text-[14px]">Settings</span>
          </Link>
          
          <button 
            onClick={onLogout}
            className="w-full px-3 py-2.5 text-am-text-secondary hover:text-am-error hover:bg-red-50 rounded-xl transition-all duration-150 text-left flex items-center gap-3 group"
          >
            <svg className="w-[20px] h-[20px] stroke-[1.5]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 9V5.25A2.25 2.25 0 0013.5 3h-6a2.25 2.25 0 00-2.25 2.25v13.5A2.25 2.25 0 007.5 21h6a2.25 2.25 0 002.25-2.25V15m3 0l3-3m0 0l-3-3m3 3H9" />
            </svg>
            <span className="text-[14px]">Sign Out</span>
          </button>
        </div>
      </div>
    </>
  )
}

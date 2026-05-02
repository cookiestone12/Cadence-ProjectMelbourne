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
  BuildingOfficeIcon,
  UserGroupIcon,
  SparklesIcon,
  CloudArrowUpIcon,
  StarIcon,
  ShareIcon,
  LifebuoyIcon,
  ChevronDownIcon,
  ChevronRightIcon
} from '@heroicons/react/24/outline'
import NotificationBell from './NotificationBell'
import OrgSwitcher from './OrgSwitcher'

export default function Sidebar({ user, onLogout, isOpen, onClose }) {
  const location = useLocation()
  const [orgBranding, setOrgBranding] = useState(null)
  const [isOrgAdmin, setIsOrgAdmin] = useState(false)
  const [canManageRoster, setCanManageRoster] = useState(false)
  const [isClient, setIsClient] = useState(false)

  useEffect(() => {
    const fetchOrgData = async () => {
      try {
        const [orgRes, memberRes] = await Promise.all([
          axios.get('/api/organizations/current'),
          axios.get('/api/organizations/current/membership')
        ])
        setOrgBranding(orgRes.data)
        const role = memberRes.data.role
        setIsClient(role === 'CLIENT')
        setIsOrgAdmin(role === 'OWNER' || role === 'ADMIN')
        setCanManageRoster(
          role === 'OWNER' || role === 'ADMIN' || memberRes.data.can_manage_roster === true
        )
      } catch {}
    }
    fetchOrgData()
  }, [])

  const isActive = (path) => {
    if (path === '/') return location.pathname === '/'
    if (path === '/catalog') return location.pathname === '/catalog'
    return location.pathname.startsWith(path)
  }

  const clientNavItems = [
    { path: '/client-portal', label: 'My Portal', icon: HomeIcon },
    { path: '/support', label: 'Support', icon: LifebuoyIcon },
  ]

  const topItems = [
    { path: '/', label: 'Home', icon: HomeIcon },
    { path: '/search', label: 'Search', icon: MagnifyingGlassIcon },
  ]

  const sectionDefs = [
    {
      key: 'catalog',
      label: 'Catalog',
      defaultOpen: true,
      items: [
        { path: '/catalog', label: 'Catalog', icon: MusicalNoteIcon },
        { path: '/catalog/unreleased', label: 'Unreleased', icon: DocumentTextIcon, indent: true },
        { path: '/releases', label: 'Artist Releases', icon: RectangleStackIcon },
        { path: '/credits', label: 'Credits', icon: StarIcon },
        { path: '/storage-scan', label: 'Storage Scan', icon: CloudArrowUpIcon },
        { path: '/registration-reports', label: 'Bulk Registration', icon: DocumentTextIcon },
      ],
    },
    {
      key: 'financials',
      label: 'Financials',
      defaultOpen: true,
      items: [
        { path: '/contracts', label: 'Contracts', icon: ClipboardDocumentListIcon },
        { path: '/royalties', label: 'Royalties', icon: BanknotesIcon },
        { path: '/valuation', label: 'Valuation', icon: CurrencyDollarIcon },
        { path: '/actions', label: 'Actions', icon: ClipboardDocumentCheckIcon },
      ],
    },
    {
      key: 'analytics',
      label: 'Analytics',
      defaultOpen: false,
      items: [
        { path: '/reports', label: 'Reports', icon: ChartBarIcon },
        { path: '/placements', label: 'Sync HQ', icon: FilmIcon },
        { path: '/brief-builder', label: 'Brief Builder', icon: SparklesIcon },
        { path: '/audit', label: 'Royalty Audit', icon: ShieldCheckIcon },
      ],
    },
    {
      key: 'team',
      label: 'Team',
      defaultOpen: false,
      items: [
        { path: '/roster', label: 'Roster', icon: UsersIcon, requiresRoster: true },
        { path: '/directory', label: 'Directory', icon: UserGroupIcon },
        { path: '/shared-with-me', label: 'Shared With Me', icon: ShareIcon },
        { path: '/support', label: 'Support', icon: LifebuoyIcon },
      ],
    },
    {
      key: 'settings',
      label: 'Settings',
      defaultOpen: false,
      items: [
        { path: '/settings', label: 'Settings', icon: Cog6ToothIcon },
      ],
    },
  ]

  const filterItem = (item) => {
    if (item.requiresRoster) return canManageRoster
    return true
  }

  const sections = sectionDefs
    .map((sec) => ({ ...sec, items: sec.items.filter(filterItem) }))
    .filter((sec) => sec.items.length > 0)

  const initialOpen = () => {
    const next = {}
    for (const sec of sectionDefs) {
      next[sec.key] = sec.defaultOpen || sec.items.some((it) => isActive(it.path))
    }
    return next
  }
  const [openSections, setOpenSections] = useState(initialOpen)

  useEffect(() => {
    setOpenSections((prev) => {
      const next = { ...prev }
      for (const sec of sectionDefs) {
        if (sec.items.some((it) => isActive(it.path))) {
          next[sec.key] = true
        }
      }
      return next
    })
  }, [location.pathname])

  const toggleSection = (key) => {
    setOpenSections((prev) => ({ ...prev, [key]: !prev[key] }))
  }
  
  return (
    <>
      {isOpen && (
        <div 
          className="fixed inset-0 bg-black/20 backdrop-blur-sm z-40 lg:hidden transition-opacity duration-200"
          onClick={onClose}
        />
      )}
      
      <div className={`
        fixed lg:sticky inset-y-0 left-0 z-50
        h-screen w-64 bg-white/95 backdrop-blur-xl
        flex flex-col border-r border-am-separator
        transform transition-transform duration-200 ease-am
        lg:flex-shrink-0 lg:top-0
        ${isOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}
      `}>
        <div className="p-5 border-b border-am-separator">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 min-w-0">
              {orgBranding?.logo_url ? (
                <img 
                  src={orgBranding.logo_url} 
                  alt={orgBranding.display_name || orgBranding.name || 'Cadence'} 
                  className="h-10 max-w-[140px] object-contain"
                />
              ) : (
                <span className="text-lg font-bold text-[#3D4A44] truncate">
                  {orgBranding?.display_name || orgBranding?.name || 'Cadence'}
                </span>
              )}
              <span className="px-1.5 py-0.5 text-[9px] font-semibold tracking-wide uppercase bg-[#5B8A72]/10 text-[#5B8A72] rounded-md flex-shrink-0">Beta</span>
            </div>
            <button
              onClick={onClose}
              className="lg:hidden w-9 h-9 flex items-center justify-center rounded-full text-am-text-secondary hover:text-am-text hover:bg-am-subtle transition-all duration-150"
            >
              <XMarkIcon className="w-5 h-5" />
            </button>
          </div>
          {!isClient && (
            <div className="mt-2">
              <OrgSwitcher activeOrg={orgBranding} />
            </div>
          )}
        </div>
      
        <div className="flex-1 overflow-y-auto">
          <nav className="px-3 py-4 space-y-0.5">
            {(isClient ? clientNavItems : topItems).map((item) => {
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

            {!isClient && sections.map((sec) => {
              const isOpen = !!openSections[sec.key]
              return (
                <div key={sec.key} className="pt-3">
                  <button
                    type="button"
                    onClick={() => toggleSection(sec.key)}
                    className="w-full flex items-center justify-between px-3 pb-1 text-[11px] font-semibold uppercase tracking-wider text-am-text-secondary hover:text-am-text transition-colors duration-150"
                  >
                    <span>{sec.label}</span>
                    {isOpen ? (
                      <ChevronDownIcon className="w-3.5 h-3.5" />
                    ) : (
                      <ChevronRightIcon className="w-3.5 h-3.5" />
                    )}
                  </button>
                  {isOpen && (
                    <div className="space-y-0.5">
                      {sec.items.map((item) => {
                        const Icon = item.icon
                        const active = isActive(item.path)
                        return (
                          <Link
                            key={item.path}
                            to={item.path}
                            onClick={() => window.innerWidth < 1024 && onClose()}
                            className={`
                              flex items-center gap-3 ${item.indent ? 'pl-8 pr-3' : 'px-3'} py-2.5 rounded-xl
                              transition-all duration-150 ease-am
                              ${active
                                ? 'bg-gradient-to-r from-am-accent to-am-accent-light text-white shadow-am-button'
                                : 'text-am-text hover:bg-am-subtle'
                              }
                            `}
                          >
                            <Icon className={`${item.indent ? 'w-[18px] h-[18px]' : 'w-[22px] h-[22px]'} ${active ? 'stroke-[1.8]' : 'stroke-[1.5]'}`} />
                            <span className={`${item.indent ? 'text-[13px]' : 'text-[15px]'} ${active ? 'font-semibold' : 'font-medium'}`}>{item.label}</span>
                          </Link>
                        )
                      })}
                    </div>
                  )}
                </div>
              )
            })}
          </nav>

          <div className="px-3 pb-3 pt-2 border-t border-am-separator space-y-0.5">
            {isClient ? null : user?.is_super_admin ? (
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

          <div className="px-3 pb-3 pt-2 border-t border-am-separator">
            <div className="flex items-center gap-3 px-3 py-2">
              <div className="w-9 h-9 flex-shrink-0 rounded-full bg-gradient-to-br from-am-accent to-am-accent-light flex items-center justify-center text-[14px] font-semibold text-white shadow-am-sm">
                {user?.username?.charAt(0).toUpperCase() || 'U'}
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-[14px] font-medium text-am-text truncate">{user?.username || 'User'}</p>
                <p className="text-[12px] text-am-text-secondary truncate">{isClient ? 'Client' : user?.is_super_admin ? 'Super Admin' : user?.is_admin ? 'Admin' : 'Member'}</p>
              </div>
              <div className="flex-shrink-0">
                <NotificationBell />
              </div>
            </div>
          </div>
        </div>
      </div>
    </>
  )
}

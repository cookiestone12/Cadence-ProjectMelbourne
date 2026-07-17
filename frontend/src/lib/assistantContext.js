const context = {}

export function setAssistantContext(values = {}) {
  Object.assign(context, values)
}

export function clearAssistantContext(keys = []) {
  for (const key of keys) {
    delete context[key]
  }
}

export function getAssistantContext() {
  return { ...context }
}

export function pageFromPath(path = '/') {
  if (path.startsWith('/roster/')) return 'creator_detail'
  if (path.startsWith('/roster')) return 'roster'
  if (path.startsWith('/catalog')) return 'catalog'
  if (path.startsWith('/contracts')) return 'contracts'
  if (path.startsWith('/royalties')) return 'royalties'
  if (path.startsWith('/placements')) return 'placements'
  if (path.startsWith('/reports')) return 'reports'
  if (path.startsWith('/valuation')) return 'valuation'
  if (path.startsWith('/actions')) return 'actions'
  if (path.startsWith('/settings')) return 'settings'
  return 'app'
}

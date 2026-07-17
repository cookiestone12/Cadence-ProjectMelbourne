export const API_BASE = '/api/v1'

export function apiUrl(url) {
  if (!url || /^https?:\/\//i.test(url)) return url
  if (url === '/api') return API_BASE
  if (url.startsWith(`${API_BASE}/`) || url === API_BASE) return url
  if (url.startsWith('/api/')) return `${API_BASE}${url.slice('/api'.length)}`
  return url
}

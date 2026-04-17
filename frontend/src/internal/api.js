import axios from 'axios'

// Internal portal authentication is cookie-based:
// POST /api/internal/portal/cookie-login sets `cadence_internal_token`
// as an httpOnly cookie scoped to path=/api/internal (Secure in
// production, SameSite=Lax always). Every /api/internal/portal/* call
// below uses withCredentials=true so the browser sends that cookie
// back. The JWT itself is never exposed to JS and never written to
// localStorage on this side.
const internal = axios.create({ withCredentials: true })

internal.interceptors.response.use(
  (r) => r,
  (err) => {
    if (err?.response?.status === 401) {
      localStorage.removeItem('internal_user')
      if (!window.location.pathname.endsWith('/internal/login')) {
        window.location.href = '/internal/login'
      }
    }
    return Promise.reject(err)
  }
)

export default internal

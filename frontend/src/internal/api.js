import axios from 'axios'

// Internal portal authentication is cookie-based:
// POST /api/internal/portal/cookie-login sets `cadence_internal_token`
// as an httpOnly Secure SameSite=Lax cookie at path=/. Every other
// /api/internal/portal/* call below uses withCredentials=true so the
// browser sends that cookie back. The JWT itself is therefore never
// exposed to JS — there is no localStorage token persistence here.
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

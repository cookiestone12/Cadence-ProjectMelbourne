import axios from 'axios'

const internal = axios.create()

internal.interceptors.request.use((cfg) => {
  const token = localStorage.getItem('internal_token')
  if (token) cfg.headers.Authorization = `Bearer ${token}`
  return cfg
})

internal.interceptors.response.use(
  (r) => r,
  (err) => {
    if (err?.response?.status === 401) {
      localStorage.removeItem('internal_token')
      localStorage.removeItem('internal_user')
      if (!window.location.pathname.endsWith('/internal/login')) {
        window.location.href = '/internal/login'
      }
    }
    return Promise.reject(err)
  }
)

export default internal

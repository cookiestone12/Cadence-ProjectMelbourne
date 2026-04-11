import axios from 'axios'

function urlBase64ToUint8Array(base64String) {
  const padding = '='.repeat((4 - base64String.length % 4) % 4)
  const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/')
  const rawData = window.atob(base64)
  const outputArray = new Uint8Array(rawData.length)
  for (let i = 0; i < rawData.length; ++i) {
    outputArray[i] = rawData.charCodeAt(i)
  }
  return outputArray
}

export function isIOSSafari() {
  const ua = navigator.userAgent
  return /iPad|iPhone|iPod/.test(ua) || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1)
}

export function isInstalledPWA() {
  return window.matchMedia('(display-mode: standalone)').matches
    || window.navigator.standalone === true
}

export function isPushSupported() {
  return 'serviceWorker' in navigator && 'PushManager' in window && 'Notification' in window
}

export function needsPWAInstall() {
  return isIOSSafari() && !isInstalledPWA()
}

export async function subscribeToPush() {
  if (!isPushSupported()) return { success: false, reason: 'not_supported' }

  if (isIOSSafari() && !isInstalledPWA()) {
    return { success: false, reason: 'ios_needs_install' }
  }

  try {
    const permission = await Notification.requestPermission()
    if (permission !== 'granted') {
      return { success: false, reason: 'denied' }
    }

    const reg = await navigator.serviceWorker.ready
    const existing = await reg.pushManager.getSubscription()
    if (existing) {
      return { success: true, reason: 'already_subscribed' }
    }

    const keyResponse = await axios.get('/api/push/vapid-public-key')
    const vapidKey = keyResponse.data.publicKey
    const applicationServerKey = urlBase64ToUint8Array(vapidKey)

    const sub = await reg.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey,
    })

    const subJSON = sub.toJSON()
    await axios.post('/api/push/subscribe', {
      endpoint: subJSON.endpoint,
      keys: {
        p256dh: subJSON.keys.p256dh,
        auth: subJSON.keys.auth,
      },
      userAgent: navigator.userAgent,
    })

    return { success: true, reason: 'subscribed' }
  } catch (err) {
    console.error('Push subscription error:', err)
    return { success: false, reason: 'error', error: err }
  }
}

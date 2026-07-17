import { useEffect } from 'react'

const FOCUSABLE_SELECTOR = [
  'a[href]',
  'button:not([disabled])',
  'textarea:not([disabled])',
  'input:not([disabled]):not([type="hidden"])',
  'select:not([disabled])',
  '[tabindex]:not([tabindex="-1"])',
].join(',')

const describeButton = (button) => {
  const explicit = button.getAttribute('aria-label') || button.getAttribute('aria-labelledby')
  if (explicit) return

  const title = button.getAttribute('title')
  const text = button.textContent?.trim()
  if (text) return

  if (title) {
    button.setAttribute('aria-label', title)
    return
  }

  const iconTitle = button.querySelector('svg title')?.textContent?.trim()
  if (iconTitle) {
    button.setAttribute('aria-label', iconTitle)
  }
}

const enhanceTable = (table) => {
  if (!table.hasAttribute('tabindex')) table.tabIndex = 0
  if (!table.hasAttribute('aria-label') && !table.hasAttribute('aria-labelledby')) {
    const heading = table.closest('section, article, div')?.querySelector('h1, h2, h3, h4')?.textContent?.trim()
    table.setAttribute('aria-label', heading ? `${heading} table` : 'Data table')
  }

  table.querySelectorAll('tbody tr').forEach((row) => {
    if (!row.hasAttribute('tabindex')) row.tabIndex = 0
  })
}

const focusFirstModalControl = (modal) => {
  const target = modal.querySelector(FOCUSABLE_SELECTOR) || modal
  window.requestAnimationFrame(() => target.focus?.())
}

const enhanceModal = (modal, activeElement) => {
  if (!modal.hasAttribute('role')) modal.setAttribute('role', 'dialog')
  if (!modal.hasAttribute('aria-modal')) modal.setAttribute('aria-modal', 'true')
  if (!modal.hasAttribute('tabindex')) modal.tabIndex = -1
  if (!modal.dataset.accessibilityFocused || !modal.contains(activeElement)) {
    modal.dataset.accessibilityFocused = 'true'
    focusFirstModalControl(modal)
  }
}

const getActiveModal = () => {
  const candidates = Array.from(document.querySelectorAll('[role="dialog"], .fixed.inset-0'))
  return candidates.find((candidate) => {
    const style = window.getComputedStyle(candidate)
    return style.display !== 'none' && style.visibility !== 'hidden'
  })
}

export default function useGlobalAccessibility() {
  useEffect(() => {
    const enhance = () => {
      document.querySelectorAll('button').forEach(describeButton)
      document.querySelectorAll('table').forEach(enhanceTable)
      const modal = getActiveModal()
      if (modal) enhanceModal(modal, document.activeElement)
    }

    const handleKeyDown = (event) => {
      const table = event.target.closest?.('table')
      if (table && event.target.matches('tr')) {
        const rows = Array.from(table.querySelectorAll('tbody tr[tabindex]'))
        const index = rows.indexOf(event.target)
        const delta = event.key === 'ArrowDown' ? 1 : event.key === 'ArrowUp' ? -1 : 0
        if (delta !== 0 && index !== -1) {
          event.preventDefault()
          rows[Math.max(0, Math.min(rows.length - 1, index + delta))]?.focus()
        }
      }

      const modal = getActiveModal()
      if (!modal) return
      if (event.key === 'Escape') {
        modal.querySelector('button[aria-label*="Close" i], button[aria-label*="Cancel" i]')?.click()
        return
      }
      if (event.key !== 'Tab') return

      const focusable = Array.from(modal.querySelectorAll(FOCUSABLE_SELECTOR))
      if (focusable.length === 0) {
        event.preventDefault()
        modal.focus()
        return
      }

      const first = focusable[0]
      const last = focusable[focusable.length - 1]
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault()
        last.focus()
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault()
        first.focus()
      }
    }

    enhance()
    const observer = new MutationObserver(enhance)
    observer.observe(document.body, { childList: true, subtree: true, attributes: true })
    document.addEventListener('keydown', handleKeyDown)

    return () => {
      observer.disconnect()
      document.removeEventListener('keydown', handleKeyDown)
    }
  }, [])
}

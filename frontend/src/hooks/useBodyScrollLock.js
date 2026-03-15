import { useEffect, useRef, useCallback } from 'react'

export default function useBodyScrollLock(isLocked) {
  const scrollYRef = useRef(0)

  const preventOverscroll = useCallback((e) => {
    const target = e.target
    let scrollable = target
    while (scrollable && scrollable !== document.body) {
      const style = window.getComputedStyle(scrollable)
      const overflowY = style.overflowY
      if (overflowY === 'auto' || overflowY === 'scroll') {
        const { scrollTop, scrollHeight, clientHeight } = scrollable
        const atTop = scrollTop <= 0
        const atBottom = scrollTop + clientHeight >= scrollHeight - 1
        if (e.touches && e.touches.length === 1) {
          const touchY = e.touches[0].clientY
          if (!scrollable._lastTouchY) {
            scrollable._lastTouchY = touchY
            return
          }
          const delta = touchY - scrollable._lastTouchY
          scrollable._lastTouchY = touchY
          if ((atTop && delta > 0) || (atBottom && delta < 0)) {
            e.preventDefault()
          }
        }
        return
      }
      scrollable = scrollable.parentElement
    }
    e.preventDefault()
  }, [])

  const clearLastTouch = useCallback((e) => {
    let scrollable = e.target
    while (scrollable && scrollable !== document.body) {
      if (scrollable._lastTouchY !== undefined) {
        delete scrollable._lastTouchY
      }
      scrollable = scrollable.parentElement
    }
  }, [])

  useEffect(() => {
    if (isLocked) {
      scrollYRef.current = window.scrollY
      document.body.style.position = 'fixed'
      document.body.style.top = `-${scrollYRef.current}px`
      document.body.style.left = '0'
      document.body.style.right = '0'
      document.body.style.overflow = 'hidden'

      document.addEventListener('touchmove', preventOverscroll, { passive: false })
      document.addEventListener('touchend', clearLastTouch)
      document.addEventListener('touchcancel', clearLastTouch)

      return () => {
        document.body.style.position = ''
        document.body.style.top = ''
        document.body.style.left = ''
        document.body.style.right = ''
        document.body.style.overflow = ''
        window.scrollTo(0, scrollYRef.current)

        document.removeEventListener('touchmove', preventOverscroll)
        document.removeEventListener('touchend', clearLastTouch)
        document.removeEventListener('touchcancel', clearLastTouch)
      }
    }
  }, [isLocked, preventOverscroll, clearLastTouch])
}

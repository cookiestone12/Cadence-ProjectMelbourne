import { useEffect, useRef, useCallback } from 'react'

export default function useBodyScrollLock(isLocked) {
  const scrollYRef = useRef(0)
  const startYRef = useRef(0)

  const preventOverscroll = useCallback((e) => {
    if (!e.touches || e.touches.length !== 1) return

    const touch = e.touches[0]
    const target = e.target
    let scrollable = target

    while (scrollable && scrollable !== document.body) {
      const style = window.getComputedStyle(scrollable)
      const overflowX = style.overflowX
      const overflowY = style.overflowY

      if (overflowX === 'auto' || overflowX === 'scroll') {
        const { scrollLeft, scrollWidth, clientWidth } = scrollable
        if (scrollWidth > clientWidth) {
          return
        }
      }

      if (overflowY === 'auto' || overflowY === 'scroll') {
        const { scrollTop, scrollHeight, clientHeight } = scrollable
        if (scrollHeight <= clientHeight) {
          scrollable = scrollable.parentElement
          continue
        }
        const atTop = scrollTop <= 0
        const atBottom = scrollTop + clientHeight >= scrollHeight - 1
        const deltaY = touch.clientY - startYRef.current
        if ((atTop && deltaY > 0) || (atBottom && deltaY < 0)) {
          e.preventDefault()
        }
        return
      }
      scrollable = scrollable.parentElement
    }
    e.preventDefault()
  }, [])

  const recordTouchStart = useCallback((e) => {
    if (e.touches && e.touches.length === 1) {
      startYRef.current = e.touches[0].clientY
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

      document.addEventListener('touchstart', recordTouchStart, { passive: true })
      document.addEventListener('touchmove', preventOverscroll, { passive: false })

      return () => {
        document.body.style.position = ''
        document.body.style.top = ''
        document.body.style.left = ''
        document.body.style.right = ''
        document.body.style.overflow = ''
        window.scrollTo(0, scrollYRef.current)

        document.removeEventListener('touchstart', recordTouchStart)
        document.removeEventListener('touchmove', preventOverscroll)
      }
    }
  }, [isLocked, preventOverscroll, recordTouchStart])
}

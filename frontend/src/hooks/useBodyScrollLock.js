import { useEffect, useRef } from 'react'

export default function useBodyScrollLock(isLocked) {
  const scrollYRef = useRef(0)

  useEffect(() => {
    if (isLocked) {
      scrollYRef.current = window.scrollY
      const scrollbarWidth = window.innerWidth - document.documentElement.clientWidth
      document.body.style.position = 'fixed'
      document.body.style.top = `-${scrollYRef.current}px`
      document.body.style.left = '0'
      document.body.style.right = '0'
      document.body.style.overflow = 'hidden'
      if (scrollbarWidth > 0) {
        document.body.style.paddingRight = `${scrollbarWidth}px`
      }

      return () => {
        document.body.style.position = ''
        document.body.style.top = ''
        document.body.style.left = ''
        document.body.style.right = ''
        document.body.style.overflow = ''
        document.body.style.paddingRight = ''
        window.scrollTo(0, scrollYRef.current)
      }
    }
  }, [isLocked])
}

import React, { useState, useRef, useCallback, useEffect } from 'react'

const THRESHOLD = 80
const MAX_PULL = 120

export default function PullToRefresh({ children }) {
  const [pulling, setPulling] = useState(false)
  const [pullDistance, setPullDistance] = useState(0)
  const [refreshing, setRefreshing] = useState(false)
  const startY = useRef(0)
  const currentY = useRef(0)
  const containerRef = useRef(null)
  const isPulling = useRef(false)

  const getScrollParent = useCallback(() => {
    let el = containerRef.current
    while (el) {
      if (el.scrollTop > 0) return el
      el = el.parentElement
    }
    return null
  }, [])

  const isAtTop = useCallback(() => {
    const scrollParent = getScrollParent()
    if (scrollParent) return scrollParent.scrollTop <= 0
    return window.scrollY <= 0
  }, [getScrollParent])

  const handleTouchStart = useCallback((e) => {
    if (refreshing) return
    if (!isAtTop()) return
    startY.current = e.touches[0].clientY
    isPulling.current = true
  }, [refreshing, isAtTop])

  const handleTouchMove = useCallback((e) => {
    if (!isPulling.current || refreshing) return
    if (!isAtTop()) {
      isPulling.current = false
      setPulling(false)
      setPullDistance(0)
      return
    }

    currentY.current = e.touches[0].clientY
    const diff = currentY.current - startY.current

    if (diff > 0) {
      e.preventDefault()
      const distance = Math.min(diff * 0.5, MAX_PULL)
      setPullDistance(distance)
      setPulling(true)
    }
  }, [refreshing, isAtTop])

  const handleTouchEnd = useCallback(() => {
    if (!isPulling.current) return
    isPulling.current = false

    if (pullDistance >= THRESHOLD && !refreshing) {
      setRefreshing(true)
      setPullDistance(THRESHOLD)
      window.location.reload()
    } else {
      setPulling(false)
      setPullDistance(0)
    }
  }, [pullDistance, refreshing])

  useEffect(() => {
    const el = containerRef.current
    if (!el) return
    el.addEventListener('touchstart', handleTouchStart, { passive: true })
    el.addEventListener('touchmove', handleTouchMove, { passive: false })
    el.addEventListener('touchend', handleTouchEnd, { passive: true })
    return () => {
      el.removeEventListener('touchstart', handleTouchStart)
      el.removeEventListener('touchmove', handleTouchMove)
      el.removeEventListener('touchend', handleTouchEnd)
    }
  }, [handleTouchStart, handleTouchMove, handleTouchEnd])

  const progress = Math.min(pullDistance / THRESHOLD, 1)
  const showIndicator = pulling || refreshing

  return (
    <div ref={containerRef} style={{ position: 'relative', minHeight: '100%' }}>
      {showIndicator && (
        <div
          style={{
            position: 'fixed',
            top: 0,
            left: '50%',
            transform: 'translateX(-50%)',
            zIndex: 9999,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            paddingTop: Math.max(pullDistance - 30, 8),
            transition: refreshing ? 'none' : 'padding-top 0.1s ease',
            pointerEvents: 'none',
          }}
        >
          <div
            style={{
              width: 36,
              height: 36,
              borderRadius: '50%',
              background: '#fff',
              boxShadow: '0 2px 12px rgba(0,0,0,0.15)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              opacity: progress,
              transform: `scale(${0.5 + progress * 0.5})`,
              transition: refreshing ? 'none' : 'transform 0.1s ease, opacity 0.1s ease',
            }}
          >
            {refreshing ? (
              <div
                style={{
                  width: 20,
                  height: 20,
                  border: '2.5px solid #5B8A72',
                  borderTopColor: 'transparent',
                  borderRadius: '50%',
                  animation: 'ptr-spin 0.6s linear infinite',
                }}
              />
            ) : (
              <svg
                width="20"
                height="20"
                viewBox="0 0 24 24"
                fill="none"
                stroke="#5B8A72"
                strokeWidth="2.5"
                strokeLinecap="round"
                strokeLinejoin="round"
                style={{
                  transform: `rotate(${progress * 360}deg)`,
                  transition: 'transform 0.1s ease',
                }}
              >
                <path d="M1 4v6h6" />
                <path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10" />
              </svg>
            )}
          </div>
        </div>
      )}
      <style>{`@keyframes ptr-spin { to { transform: rotate(360deg); } }`}</style>
      <div
        style={{
          transform: showIndicator ? `translateY(${Math.min(pullDistance * 0.3, 30)}px)` : 'none',
          transition: pulling ? 'none' : 'transform 0.3s ease',
        }}
      >
        {children}
      </div>
    </div>
  )
}

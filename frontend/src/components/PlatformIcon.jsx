import { useId } from 'react'

const platformSVGs = {
  SPOTIFY: ({ size }) => (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none">
      <circle cx="12" cy="12" r="12" fill="#1DB954" />
      <path d="M16.94 10.58c-2.68-1.59-7.1-1.74-9.66-.96-.41.13-.85-.1-.98-.51s.1-.85.51-.98c2.94-.89 7.82-.72 10.91 1.11.36.21.47.67.26 1.03-.21.35-.67.47-1.04.31zm-.19 2.55c-.18.29-.56.38-.85.2-2.23-1.37-5.63-1.77-8.27-.97-.33.1-.68-.09-.78-.42s.09-.68.42-.78c3.01-.91 6.75-.47 9.31 1.1.29.18.38.57.17.87zm-.97 2.45c-.14.23-.44.31-.68.17-1.95-1.19-4.4-1.46-7.29-.8-.28.06-.55-.11-.62-.39-.06-.28.11-.55.39-.62 3.16-.72 5.87-.41 8.05.91.24.14.31.44.15.73z" fill="white" />
    </svg>
  ),
  APPLE_MUSIC: ({ size, gradId }) => (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none">
      <defs>
        <linearGradient id={gradId} x1="12" y1="0" x2="12" y2="24" gradientUnits="userSpaceOnUse">
          <stop stopColor="#FA233B" />
          <stop offset="1" stopColor="#FB5C74" />
        </linearGradient>
      </defs>
      <rect width="24" height="24" rx="5.4" fill={`url(#${gradId})`} />
      <path d="M16.5 5.8v8.6c0 1.5-1.2 2.1-2.2 2.2-1.1.1-2-.5-2-1.5 0-1.1.9-1.7 1.9-1.8.5-.1 1-.01 1.3.1V8.2l-5 1.5v7c0 1.5-1.2 2.1-2.2 2.2-1.1.1-2-.5-2-1.5 0-1.1.9-1.7 1.9-1.8.5-.1 1-.01 1.3.1V7.3c0-.4.2-.7.5-.8l5.5-1.6c.6-.2 1 .2 1 .9z" fill="white" />
    </svg>
  ),
  YOUTUBE_MUSIC: ({ size }) => (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none">
      <circle cx="12" cy="12" r="12" fill="#FF0000" />
      <circle cx="12" cy="12" r="4.5" fill="#FF0000" stroke="white" strokeWidth="1.2" />
      <polygon points="10.8,9.6 14.8,12 10.8,14.4" fill="white" />
    </svg>
  ),
  AMAZON_MUSIC: ({ size }) => (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none">
      <rect width="24" height="24" rx="5.4" fill="#25D1DA" />
      <path d="M7 14.5c0 0 2.5 2.5 5 2.5s5-2.5 5-2.5" stroke="white" strokeWidth="1.8" strokeLinecap="round" fill="none" />
      <path d="M12 6.5v7" stroke="white" strokeWidth="1.8" strokeLinecap="round" />
      <path d="M9 9.5l3-3 3 3" stroke="white" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" fill="none" />
    </svg>
  ),
  TIDAL: ({ size }) => (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none">
      <rect width="24" height="24" rx="5.4" fill="#000000" />
      <path d="M8 8.5l2.67 2.67L8 13.83l-2.67-2.66L8 8.5zm4 0l2.67 2.67L12 13.83 9.33 11.17 12 8.5zm4 0l2.67 2.67L16 13.83l-2.67-2.66L16 8.5zm-4 4l2.67 2.67L12 17.83 9.33 15.17 12 12.5z" fill="white" />
    </svg>
  ),
  DEEZER: ({ size }) => (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none">
      <rect width="24" height="24" rx="5.4" fill="#A238FF" />
      <rect x="4" y="15" width="3.2" height="2" rx="0.4" fill="white" />
      <rect x="8.2" y="15" width="3.2" height="2" rx="0.4" fill="white" />
      <rect x="8.2" y="12.2" width="3.2" height="2" rx="0.4" fill="white" />
      <rect x="12.4" y="15" width="3.2" height="2" rx="0.4" fill="white" />
      <rect x="12.4" y="12.2" width="3.2" height="2" rx="0.4" fill="white" />
      <rect x="12.4" y="9.4" width="3.2" height="2" rx="0.4" fill="white" />
      <rect x="16.6" y="15" width="3.2" height="2" rx="0.4" fill="white" />
      <rect x="16.6" y="12.2" width="3.2" height="2" rx="0.4" fill="white" />
      <rect x="16.6" y="9.4" width="3.2" height="2" rx="0.4" fill="white" />
      <rect x="16.6" y="6.6" width="3.2" height="2" rx="0.4" fill="white" />
    </svg>
  ),
}

export default function PlatformIcon({ platform, size = 24 }) {
  const uid = useId()
  const SVGComponent = platformSVGs[platform]
  if (!SVGComponent) {
    return (
      <div
        className="rounded-full flex-shrink-0"
        style={{ width: size, height: size, background: '#7A8580' }}
      />
    )
  }
  return <span className="flex-shrink-0 inline-flex">{SVGComponent({ size, gradId: `am-grad-${uid}` })}</span>
}

import React, { forwardRef } from 'react'

const CadenceLogoLight = ({ height = 48 }) => {
  const aspectRatio = 1804 / 476
  const width = Math.round(height * aspectRatio)
  return (
    <img
      src="/cadence-logo-transparent.png"
      alt="Cadence"
      crossOrigin="anonymous"
      style={{ height, width, objectFit: 'contain' }}
    />
  )
}

function formatNum(num) {
  if (!num) return '0'
  if (num >= 1_000_000_000) return (num / 1_000_000_000).toFixed(1) + 'B'
  if (num >= 1_000_000) return (num / 1_000_000).toFixed(1) + 'M'
  if (num >= 1_000) return (num / 1_000).toFixed(1) + 'K'
  return num.toLocaleString()
}

const RosterSocialCard = forwardRef(({ orgName, totalCredits, totalStreams, activeCreators, topCreators = [], format = 'story' }, ref) => {
  const isSquare = format === 'square'
  const cardWidth = 1080
  const cardHeight = isSquare ? 1080 : 1350
  const pad = isSquare ? 44 : 56
  const displayCreators = topCreators.slice(0, isSquare ? 4 : 5)
  const singleUnits = totalStreams ? Math.round(totalStreams / 150) : 0

  return (
    <div
      ref={ref}
      style={{
        width: cardWidth,
        height: cardHeight,
        background: 'linear-gradient(165deg, #2D5A43 0%, #3D6B54 25%, #4A7A62 50%, #3D6B54 75%, #2D5A43 100%)',
        fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
        color: '#FFFFFF',
        position: 'relative',
        overflow: 'hidden',
        display: 'flex',
        flexDirection: 'column',
      }}
    >
      <div style={{
        position: 'absolute',
        top: -200,
        right: -200,
        width: 600,
        height: 600,
        borderRadius: '50%',
        background: 'radial-gradient(circle, rgba(255,255,255,0.06) 0%, transparent 70%)',
      }} />
      <div style={{
        position: 'absolute',
        bottom: -150,
        left: -150,
        width: 500,
        height: 500,
        borderRadius: '50%',
        background: 'radial-gradient(circle, rgba(255,255,255,0.04) 0%, transparent 70%)',
      }} />

      <div style={{
        padding: `${isSquare ? 36 : 48}px ${pad}px 0`,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
      }}>
        <CadenceLogoLight height={isSquare ? 56 : 68} />
      </div>

      <div style={{
        padding: `${isSquare ? 28 : 44}px ${pad}px 0`,
        display: 'flex',
        alignItems: 'center',
        gap: isSquare ? 22 : 28,
      }}>
        <div style={{
          width: isSquare ? 88 : 110,
          height: isSquare ? 88 : 110,
          borderRadius: isSquare ? 20 : 26,
          background: 'rgba(255,255,255,0.12)',
          border: `${isSquare ? 3 : 4}px solid rgba(255,255,255,0.25)`,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          flexShrink: 0,
        }}>
          <svg width={isSquare ? 44 : 56} height={isSquare ? 44 : 56} viewBox="0 0 24 24" fill="none" stroke="rgba(255,255,255,0.7)" strokeWidth="1.5">
            <path d="M18 18.72a9.094 9.094 0 003.741-.479 3 3 0 00-4.682-2.72m.94 3.198l.001.031c0 .225-.012.447-.037.666A11.944 11.944 0 0112 21c-2.17 0-4.207-.576-5.963-1.584A6.062 6.062 0 016 18.719m12 0a5.971 5.971 0 00-.941-3.197m0 0A5.995 5.995 0 0012 12.75a5.995 5.995 0 00-5.058 2.772m0 0a3 3 0 00-4.681 2.72 8.986 8.986 0 003.74.477m.94-3.197a5.971 5.971 0 00-.94 3.197M15 6.75a3 3 0 11-6 0 3 3 0 016 0zm6 3a2.25 2.25 0 11-4.5 0 2.25 2.25 0 014.5 0zm-13.5 0a2.25 2.25 0 11-4.5 0 2.25 2.25 0 014.5 0z" />
          </svg>
        </div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{
            fontSize: isSquare ? 36 : 44,
            fontWeight: 800,
            lineHeight: 1.15,
            wordBreak: 'break-word',
          }}>{orgName || 'Roster'}</div>
          <div style={{ fontSize: isSquare ? 16 : 18, opacity: 0.6, marginTop: isSquare ? 4 : 6 }}>Roster Credits Overview</div>
        </div>
      </div>

      <div style={{
        margin: `${isSquare ? 24 : 36}px ${pad}px 0`,
        display: 'flex',
        gap: isSquare ? 12 : 16,
      }}>
        {[
          { label: 'CREDITS', value: formatNum(totalCredits) },
          { label: 'EST. STREAMS', value: formatNum(totalStreams) },
          { label: 'CREATORS', value: activeCreators },
        ].map((stat, i) => (
          <div key={i} style={{
            flex: 1,
            background: 'rgba(255,255,255,0.1)',
            borderRadius: isSquare ? 12 : 16,
            padding: isSquare ? '14px 16px' : '20px 20px',
            backdropFilter: 'blur(10px)',
            border: '1px solid rgba(255,255,255,0.12)',
          }}>
            <div style={{ fontSize: isSquare ? 10 : 12, opacity: 0.5, letterSpacing: 1.5, fontWeight: 600, marginBottom: isSquare ? 4 : 6 }}>{stat.label}</div>
            <div style={{ fontSize: isSquare ? 26 : 32, fontWeight: 800 }}>{stat.value}</div>
          </div>
        ))}
      </div>

      <div style={{
        margin: `${isSquare ? 12 : 18}px ${pad}px 0`,
        display: 'flex',
        gap: isSquare ? 10 : 14,
      }}>
        <div style={{
          flex: 1,
          background: 'rgba(255,255,255,0.07)',
          borderRadius: isSquare ? 10 : 14,
          padding: isSquare ? '12px 16px' : '16px 20px',
          border: '1px solid rgba(255,255,255,0.08)',
        }}>
          <div style={{ fontSize: isSquare ? 9 : 11, opacity: 0.45, letterSpacing: 1.5, fontWeight: 600, marginBottom: isSquare ? 3 : 5 }}>SINGLE UNITS</div>
          <div style={{ fontSize: isSquare ? 22 : 26, fontWeight: 800 }}>{formatNum(singleUnits)}</div>
        </div>
        <div style={{
          flex: 1,
          background: 'rgba(255,255,255,0.07)',
          borderRadius: isSquare ? 10 : 14,
          padding: isSquare ? '12px 16px' : '16px 20px',
          border: '1px solid rgba(255,255,255,0.08)',
        }}>
          <div style={{ fontSize: isSquare ? 9 : 11, opacity: 0.45, letterSpacing: 1.5, fontWeight: 600, marginBottom: isSquare ? 3 : 5 }}>AVG / SONG</div>
          <div style={{ fontSize: isSquare ? 22 : 26, fontWeight: 800 }}>{totalCredits > 0 ? formatNum(Math.round(totalStreams / totalCredits)) : '0'}</div>
        </div>
      </div>

      <div style={{
        margin: `${isSquare ? 20 : 32}px ${pad}px 0`,
        flex: 1,
        minHeight: 0,
      }}>
        <div style={{
          fontSize: isSquare ? 11 : 13,
          fontWeight: 700,
          letterSpacing: 2,
          opacity: 0.45,
          marginBottom: isSquare ? 10 : 16,
        }}>TOP CREATORS</div>

        <div style={{
          background: 'rgba(255,255,255,0.07)',
          borderRadius: isSquare ? 16 : 20,
          overflow: 'hidden',
          border: '1px solid rgba(255,255,255,0.08)',
        }}>
          {displayCreators.map((creator, idx) => (
            <div key={creator.creator_id || idx} style={{
              display: 'flex',
              alignItems: 'center',
              gap: isSquare ? 12 : 16,
              padding: isSquare ? '12px 20px' : '16px 24px',
              borderBottom: idx < displayCreators.length - 1 ? '1px solid rgba(255,255,255,0.06)' : 'none',
            }}>
              <span style={{
                fontSize: isSquare ? 14 : 16,
                fontWeight: 800,
                opacity: 0.35,
                width: isSquare ? 22 : 28,
                textAlign: 'right',
                flexShrink: 0,
              }}>{idx + 1}</span>

              {creator.hero_image_url ? (
                <img
                  src={creator.hero_image_url}
                  alt=""
                  crossOrigin="anonymous"
                  style={{
                    width: isSquare ? 44 : 52,
                    height: isSquare ? 44 : 52,
                    borderRadius: '50%',
                    objectFit: 'cover',
                    flexShrink: 0,
                  }}
                />
              ) : (
                <div style={{
                  width: isSquare ? 44 : 52,
                  height: isSquare ? 44 : 52,
                  borderRadius: '50%',
                  background: 'rgba(255,255,255,0.12)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  flexShrink: 0,
                  fontSize: isSquare ? 18 : 22,
                  fontWeight: 700,
                  opacity: 0.7,
                }}>
                  {(creator.display_name || '?').charAt(0).toUpperCase()}
                </div>
              )}

              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{
                  fontSize: isSquare ? 15 : 17,
                  fontWeight: 700,
                  lineHeight: 1.2,
                  wordBreak: 'break-word',
                }}>{creator.display_name}</div>
                {creator.top_role && (
                  <div style={{
                    fontSize: isSquare ? 10 : 12,
                    opacity: 0.5,
                    marginTop: 2,
                    textTransform: 'uppercase',
                    letterSpacing: 0.5,
                  }}>{creator.top_role.replace('_', ' ')}</div>
                )}
              </div>

              <div style={{ textAlign: 'right', flexShrink: 0 }}>
                <div style={{ fontSize: isSquare ? 15 : 17, fontWeight: 800 }}>{formatNum(creator.total_estimated_streams)}</div>
                <div style={{ fontSize: isSquare ? 10 : 11, opacity: 0.4, marginTop: 1 }}>streams</div>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div style={{
        padding: `${isSquare ? 16 : 24}px ${pad}px ${isSquare ? 28 : 40}px`,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
      }}>
        <span style={{ fontSize: isSquare ? 11 : 13, opacity: 0.3, fontWeight: 500 }}>
          Powered by Cadence — Catalog Intelligence
        </span>
        <span style={{ fontSize: isSquare ? 10 : 11, opacity: 0.2 }}>
          Estimates may vary from actual figures
        </span>
      </div>
    </div>
  )
})

RosterSocialCard.displayName = 'RosterSocialCard'

export default RosterSocialCard

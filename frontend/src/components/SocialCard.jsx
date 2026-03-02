import React, { forwardRef } from 'react'

const PLATFORM_COLORS = {
  SPOTIFY: '#1DB954',
  APPLE_MUSIC: '#FA233B',
  YOUTUBE_MUSIC: '#FF0000',
  AMAZON_MUSIC: '#25D1DA',
  TIDAL: '#000000',
  DEEZER: '#A238FF',
}

const PLATFORM_LABELS = {
  SPOTIFY: 'Spotify',
  APPLE_MUSIC: 'Apple Music',
  YOUTUBE_MUSIC: 'YouTube Music',
  AMAZON_MUSIC: 'Amazon Music',
  TIDAL: 'Tidal',
  DEEZER: 'Deezer',
}

function formatNum(num) {
  if (!num) return '0'
  if (num >= 1_000_000_000) return (num / 1_000_000_000).toFixed(1) + 'B'
  if (num >= 1_000_000) return (num / 1_000_000).toFixed(1) + 'M'
  if (num >= 1_000) return (num / 1_000).toFixed(1) + 'K'
  return num.toLocaleString()
}

const SocialCard = forwardRef(({ data, avatarUrl, creatorName, orgName }, ref) => {
  const topSongs = (data.top_songs || []).slice(0, 5)
  const platformBreakdown = data.platform_breakdown || {}
  const totalStreams = data.total_estimated_streams || 0
  const totalCredits = data.total_credits || 0
  const singleUnits = totalStreams ? Math.round(totalStreams / 150) : 0

  const platforms = Object.entries(platformBreakdown)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 4)

  return (
    <div
      ref={ref}
      style={{
        width: 1080,
        height: 1350,
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
        padding: '48px 56px 0',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
      }}>
        <img
          src="/cadence-logo.png"
          alt="Cadence"
          crossOrigin="anonymous"
          style={{
            height: 48,
            objectFit: 'contain',
          }}
        />
        <span style={{ fontSize: 14, opacity: 0.5, letterSpacing: 1 }}>CATALOG INTELLIGENCE</span>
      </div>

      <div style={{
        padding: '44px 56px 0',
        display: 'flex',
        alignItems: 'center',
        gap: 28,
      }}>
        {avatarUrl ? (
          <img
            src={avatarUrl}
            alt=""
            crossOrigin="anonymous"
            style={{
              width: 110,
              height: 110,
              borderRadius: '50%',
              objectFit: 'cover',
              border: '4px solid rgba(255,255,255,0.3)',
              flexShrink: 0,
            }}
          />
        ) : (
          <div style={{
            width: 110,
            height: 110,
            borderRadius: '50%',
            background: 'rgba(255,255,255,0.15)',
            border: '4px solid rgba(255,255,255,0.3)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            flexShrink: 0,
          }}>
            <svg width="52" height="52" viewBox="0 0 24 24" fill="none" stroke="rgba(255,255,255,0.5)" strokeWidth="1.5">
              <path d="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0A17.933 17.933 0 0112 21.75c-2.676 0-5.216-.584-7.499-1.632z" />
            </svg>
          </div>
        )}
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{
            fontSize: 44,
            fontWeight: 800,
            lineHeight: 1.15,
            wordBreak: 'break-word',
          }}>{creatorName}</div>
          {orgName && (
            <div style={{ fontSize: 18, opacity: 0.6, marginTop: 6 }}>{orgName}</div>
          )}
        </div>
      </div>

      <div style={{
        margin: '36px 56px 0',
        display: 'flex',
        gap: 16,
      }}>
        {[
          { label: 'CREDITS', value: totalCredits },
          { label: 'EST. STREAMS', value: formatNum(totalStreams) },
          { label: 'SINGLE UNITS', value: formatNum(singleUnits) },
        ].map((stat, i) => (
          <div key={i} style={{
            flex: 1,
            background: 'rgba(255,255,255,0.1)',
            borderRadius: 16,
            padding: '20px 20px',
            backdropFilter: 'blur(10px)',
            border: '1px solid rgba(255,255,255,0.12)',
          }}>
            <div style={{ fontSize: 12, opacity: 0.5, letterSpacing: 1.5, fontWeight: 600, marginBottom: 6 }}>{stat.label}</div>
            <div style={{ fontSize: 32, fontWeight: 800 }}>{stat.value}</div>
          </div>
        ))}
      </div>

      {platforms.length > 0 && (
        <div style={{
          margin: '24px 56px 0',
          display: 'flex',
          gap: 12,
          flexWrap: 'wrap',
        }}>
          {platforms.map(([platform, streams]) => (
            <div key={platform} style={{
              display: 'flex',
              alignItems: 'center',
              gap: 10,
              background: 'rgba(255,255,255,0.08)',
              borderRadius: 12,
              padding: '10px 16px',
              border: '1px solid rgba(255,255,255,0.08)',
            }}>
              <div style={{
                width: 10,
                height: 10,
                borderRadius: '50%',
                background: PLATFORM_COLORS[platform] || '#888',
                flexShrink: 0,
              }} />
              <span style={{ fontSize: 14, fontWeight: 600, opacity: 0.9 }}>
                {PLATFORM_LABELS[platform] || platform}
              </span>
              <span style={{ fontSize: 14, fontWeight: 700 }}>
                {formatNum(streams)}
              </span>
            </div>
          ))}
        </div>
      )}

      <div style={{
        margin: '32px 56px 0',
        flex: 1,
        minHeight: 0,
      }}>
        <div style={{
          fontSize: 13,
          fontWeight: 700,
          letterSpacing: 2,
          opacity: 0.45,
          marginBottom: 16,
        }}>TOP SONGS</div>

        <div style={{
          background: 'rgba(255,255,255,0.07)',
          borderRadius: 20,
          overflow: 'hidden',
          border: '1px solid rgba(255,255,255,0.08)',
        }}>
          {topSongs.map((song, idx) => (
            <div key={song.song_id || idx} style={{
              display: 'flex',
              alignItems: 'center',
              gap: 16,
              padding: '16px 24px',
              borderBottom: idx < topSongs.length - 1 ? '1px solid rgba(255,255,255,0.06)' : 'none',
            }}>
              <span style={{
                fontSize: 16,
                fontWeight: 800,
                opacity: 0.35,
                width: 28,
                textAlign: 'right',
                flexShrink: 0,
              }}>{idx + 1}</span>

              {song.artwork_url ? (
                <img
                  src={song.artwork_url}
                  alt=""
                  crossOrigin="anonymous"
                  style={{
                    width: 52,
                    height: 52,
                    borderRadius: 10,
                    objectFit: 'cover',
                    flexShrink: 0,
                  }}
                />
              ) : (
                <div style={{
                  width: 52,
                  height: 52,
                  borderRadius: 10,
                  background: 'rgba(255,255,255,0.08)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  flexShrink: 0,
                }}>
                  <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="rgba(255,255,255,0.3)" strokeWidth="1.5">
                    <path d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3" />
                  </svg>
                </div>
              )}

              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{
                  fontSize: 17,
                  fontWeight: 700,
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  whiteSpace: 'nowrap',
                }}>{song.title}</div>
                <div style={{
                  fontSize: 13,
                  opacity: 0.5,
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  whiteSpace: 'nowrap',
                  marginTop: 2,
                }}>{song.artist}</div>
              </div>

              <div style={{ textAlign: 'right', flexShrink: 0 }}>
                <div style={{ fontSize: 17, fontWeight: 800 }}>{formatNum(song.total_streams)}</div>
                <div style={{ fontSize: 11, opacity: 0.4, marginTop: 1 }}>streams</div>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div style={{
        padding: '24px 56px 40px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
      }}>
        <span style={{ fontSize: 13, opacity: 0.3, fontWeight: 500 }}>
          Powered by Cadence — Catalog Intelligence
        </span>
        <span style={{ fontSize: 11, opacity: 0.2 }}>
          Estimates may vary from actual figures
        </span>
      </div>
    </div>
  )
})

SocialCard.displayName = 'SocialCard'

export default SocialCard

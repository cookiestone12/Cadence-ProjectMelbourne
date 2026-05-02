export default function BrandingPreview({
  primaryColor = '#5B8A72',
  logoUrl = null,
  logoOrientation = 'square',
  displayName = 'Your Organization',
  reportTitle = 'Catalog Valuation Report',
  reportSubtitle = 'Sample export preview',
}) {
  const orientation = (logoOrientation || 'square').toLowerCase()
  const logoSize =
    orientation === 'horizontal'
      ? { width: 96, height: 32 }
      : orientation === 'vertical'
      ? { width: 32, height: 96 }
      : { width: 56, height: 56 }

  return (
    <div className="border border-[#E5E8E3] rounded-xl overflow-hidden bg-[#FAFBF9] shadow-sm">
      <div
        className="px-4 py-2 flex items-center justify-between border-b"
        style={{ borderBottomColor: primaryColor }}
      >
        <div className="text-[11px] font-semibold tracking-wide uppercase text-[#3D4A44]">
          {displayName}
        </div>
        <div className="text-[10px] text-[#7A8580]">Generated · Now</div>
      </div>

      <div className="bg-white px-6 py-6">
        <div className="flex items-start gap-4">
          {logoUrl ? (
            <img
              src={logoUrl}
              alt="Logo"
              className="rounded object-contain bg-[#F5F7F4]"
              style={logoSize}
            />
          ) : (
            <div
              className="rounded flex items-center justify-center text-white font-bold text-sm"
              style={{ ...logoSize, backgroundColor: primaryColor }}
            >
              {(displayName || 'O').charAt(0).toUpperCase()}
            </div>
          )}
          <div className="flex-1 min-w-0">
            <div
              className="text-[20px] font-bold leading-tight"
              style={{ color: primaryColor }}
            >
              {reportTitle}
            </div>
            <div className="text-[12px] text-[#7A8580] mt-1">{reportSubtitle}</div>
            <div
              className="mt-2 h-[2px] w-full rounded"
              style={{ backgroundColor: primaryColor }}
            />
          </div>
        </div>

        <div className="mt-5 grid grid-cols-3 gap-2">
          {['Songs', 'Value', 'Confidence'].map((label) => (
            <div
              key={label}
              className="rounded border border-[#E5E8E3] px-3 py-2"
              style={{ backgroundColor: lighten(primaryColor, 0.92) }}
            >
              <div className="text-[9px] uppercase tracking-wide text-[#7A8580]">{label}</div>
              <div className="text-[14px] font-bold mt-0.5" style={{ color: primaryColor }}>
                ——
              </div>
            </div>
          ))}
        </div>

        <div className="mt-4 rounded overflow-hidden border border-[#E5E8E3]">
          <div
            className="grid grid-cols-3 px-3 py-1.5 text-white text-[10px] font-bold uppercase tracking-wide"
            style={{ backgroundColor: primaryColor }}
          >
            <div>Title</div>
            <div>Artist</div>
            <div className="text-right">Value</div>
          </div>
          {[0, 1, 2].map((i) => (
            <div
              key={i}
              className="grid grid-cols-3 px-3 py-1.5 text-[10px] text-[#3D4A44]"
              style={{ backgroundColor: i % 2 === 1 ? lighten(primaryColor, 0.94) : 'white' }}
            >
              <div>Song {i + 1}</div>
              <div>Artist</div>
              <div className="text-right">$——</div>
            </div>
          ))}
        </div>
      </div>

      <div className="px-4 py-2 flex items-center justify-between border-t border-[#E5E8E3] bg-[#FAFBF9]">
        <div className="text-[9px] text-[#A0A8A3]">{displayName}</div>
        <div className="text-[9px] font-bold tracking-wide uppercase" style={{ color: primaryColor }}>
          Powered by Cadence
        </div>
        <div className="text-[9px] text-[#A0A8A3]">Page 1</div>
      </div>
    </div>
  )
}

function lighten(hex, amount) {
  const h = (hex || '#5B8A72').replace('#', '')
  const full = h.length === 3 ? h.split('').map((c) => c + c).join('') : h
  const r = parseInt(full.slice(0, 2), 16)
  const g = parseInt(full.slice(2, 4), 16)
  const b = parseInt(full.slice(4, 6), 16)
  const lr = Math.round(r + (255 - r) * amount)
  const lg = Math.round(g + (255 - g) * amount)
  const lb = Math.round(b + (255 - b) * amount)
  return `#${[lr, lg, lb].map((x) => x.toString(16).padStart(2, '0')).join('')}`
}

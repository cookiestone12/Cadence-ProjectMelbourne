import React, { useState, useEffect } from 'react'
import axios from 'axios'
import {
  LineChart, Line, BarChart, Bar, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend,
} from 'recharts'
import {
  ChartBarIcon,
  ArrowTrendingDownIcon,
  MusicalNoteIcon,
  GlobeAltIcon,
  ArrowPathIcon,
} from '@heroicons/react/24/outline'

const COLORS = ['#5B8A72', '#7BA594', '#4A7A62', '#9BBFAD', '#3D6A52', '#B5D4C6', '#2D5A42', '#6B9A82']
const RIGHT_COLORS = { mechanical: '#3B82F6', performance: '#8B5CF6', sync: '#F59E0B', print_lyrics: '#EC4899', neighboring_rights: '#14B8A6', other: '#9CA3AF' }
const CHANNEL_COLORS = { streaming: '#10B981', download: '#3B82F6', broadcast: '#F97316', live: '#EF4444', ugc: '#EAB308', social: '#EC4899', physical: '#6B7280', other: '#9CA3AF' }

const formatDollars = (val) => {
  if (val == null) return '$0.00'
  return Number(val).toLocaleString('en-US', { style: 'currency', currency: 'USD' })
}

export default function RoyaltyAnalyticsDashboard({ orgId }) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [selectedSong, setSelectedSong] = useState(null)
  const [songData, setSongData] = useState(null)
  const [songLoading, setSongLoading] = useState(false)

  useEffect(() => {
    if (!orgId) return
    setLoading(true)
    axios.get(`/api/royalty-processing/${orgId}/analytics/portfolio`)
      .then(res => setData(res.data))
      .catch(err => console.error('Failed to load analytics:', err))
      .finally(() => setLoading(false))
  }, [orgId])

  useEffect(() => {
    if (!selectedSong || !orgId) return
    setSongLoading(true)
    axios.get(`/api/royalty-processing/${orgId}/analytics/song/${selectedSong}`)
      .then(res => setSongData(res.data))
      .catch(err => console.error('Failed to load song analytics:', err))
      .finally(() => setSongLoading(false))
  }, [selectedSong, orgId])

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-[#5B8A72]" />
      </div>
    )
  }

  if (!data) {
    return (
      <div className="text-center py-16">
        <ChartBarIcon className="w-12 h-12 mx-auto text-[#A0A8A3] mb-3" />
        <p className="text-sm text-[#7A8580]">No royalty analytics data available yet.</p>
        <p className="text-xs text-[#A0A8A3] mt-1">Upload and process royalty statements to see analytics.</p>
      </div>
    )
  }

  const hasTimeSeries = data.time_series?.length > 0

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          label="Catalog Concentration"
          value={data.concentration ? `${(data.concentration.top1_share * 100).toFixed(1)}%` : 'N/A'}
          sub={`Top-1 share across ${data.concentration?.song_count || 0} songs`}
        />
        <MetricCard
          label="Top-5 Share"
          value={data.concentration ? `${(data.concentration.top5_share * 100).toFixed(1)}%` : 'N/A'}
          sub="Revenue concentration in top 5 songs"
        />
        <MetricCard
          label="HHI Index"
          value={data.concentration ? data.concentration.hhi.toFixed(4) : 'N/A'}
          sub={data.concentration?.hhi > 0.25 ? 'Highly concentrated' : data.concentration?.hhi > 0.15 ? 'Moderately concentrated' : 'Well diversified'}
        />
        {data.decay && (
          <MetricCard
            label="Portfolio Half-Life"
            value={`${data.decay.half_life_periods.toFixed(1)} Q`}
            sub={`~${(data.decay.half_life_periods * 3).toFixed(0)} months (R²: ${data.decay.r2_log.toFixed(2)})`}
          />
        )}
        {data.cagr && !data.decay && (
          <MetricCard
            label="CAGR"
            value={`${data.cagr.cagr_pct.toFixed(1)}%`}
            sub={`${data.cagr.start_period} to ${data.cagr.end_period}`}
          />
        )}
      </div>

      {hasTimeSeries && (
        <div className="bg-white/80 backdrop-blur-xl rounded-[18px] shadow-am border border-[rgba(59,77,67,0.08)] p-6">
          <h3 className="text-sm font-semibold text-[#3D4A44] mb-4">Revenue Over Time</h3>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={data.time_series}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(59,77,67,0.08)" />
              <XAxis dataKey="period" tick={{ fontSize: 11, fill: '#7A8580' }} />
              <YAxis tickFormatter={v => `$${(v / 1000).toFixed(0)}k`} tick={{ fontSize: 11, fill: '#7A8580' }} />
              <Tooltip formatter={(v) => formatDollars(v)} labelStyle={{ color: '#3D4A44' }} />
              <Line type="monotone" dataKey="net" stroke="#5B8A72" strokeWidth={2.5} dot={{ fill: '#5B8A72', r: 4 }} name="Net Revenue" />
              {data.time_series[0]?.gross != null && data.time_series[0]?.gross !== data.time_series[0]?.net && (
                <Line type="monotone" dataKey="gross" stroke="#7BA594" strokeWidth={1.5} strokeDasharray="5 5" dot={false} name="Gross Revenue" />
              )}
            </LineChart>
          </ResponsiveContainer>
          {data.decay && (
            <div className="mt-3 flex items-center gap-4 text-xs text-[#7A8580]">
              <span>Decay rate: {data.decay.k_per_period.toFixed(3)}/quarter</span>
              <span>Half-life: {data.decay.half_life_periods.toFixed(1)} quarters</span>
              <span>Fit quality: <span className={data.decay.r2_log >= 0.7 ? 'text-green-600 font-medium' : data.decay.r2_log >= 0.4 ? 'text-amber-600 font-medium' : 'text-red-500 font-medium'}>{data.decay.decay_quality} (R² {data.decay.r2_log.toFixed(2)})</span></span>
            </div>
          )}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {data.by_right_category?.length > 0 && (
          <div className="bg-white/80 backdrop-blur-xl rounded-[18px] shadow-am border border-[rgba(59,77,67,0.08)] p-6">
            <h3 className="text-sm font-semibold text-[#3D4A44] mb-4">Revenue by Right Type</h3>
            <ResponsiveContainer width="100%" height={250}>
              <PieChart>
                <Pie
                  data={data.by_right_category.filter(r => r.net_total > 0)}
                  cx="50%" cy="50%" innerRadius={50} outerRadius={90}
                  dataKey="net_total" nameKey="category"
                  label={({ category, percent }) => `${category} ${(percent * 100).toFixed(0)}%`}
                  labelLine={false}
                >
                  {data.by_right_category.filter(r => r.net_total > 0).map((entry, i) => (
                    <Cell key={i} fill={RIGHT_COLORS[entry.category] || COLORS[i % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip formatter={v => formatDollars(v)} />
              </PieChart>
            </ResponsiveContainer>
          </div>
        )}

        {data.by_channel?.length > 0 && (
          <div className="bg-white/80 backdrop-blur-xl rounded-[18px] shadow-am border border-[rgba(59,77,67,0.08)] p-6">
            <h3 className="text-sm font-semibold text-[#3D4A44] mb-4">Revenue by Channel</h3>
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={data.by_channel.filter(c => c.net_total > 0).sort((a, b) => b.net_total - a.net_total)}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(59,77,67,0.08)" />
                <XAxis dataKey="channel" tick={{ fontSize: 10, fill: '#7A8580' }} />
                <YAxis tickFormatter={v => `$${(v / 1000).toFixed(0)}k`} tick={{ fontSize: 11, fill: '#7A8580' }} />
                <Tooltip formatter={v => formatDollars(v)} />
                <Bar dataKey="net_total" name="Net Revenue" radius={[6, 6, 0, 0]}>
                  {data.by_channel.filter(c => c.net_total > 0).sort((a, b) => b.net_total - a.net_total).map((entry, i) => (
                    <Cell key={i} fill={CHANNEL_COLORS[entry.channel] || COLORS[i % COLORS.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>

      {data.top_songs?.length > 0 && (
        <div className="bg-white/80 backdrop-blur-xl rounded-[18px] shadow-am border border-[rgba(59,77,67,0.08)] p-6">
          <h3 className="text-sm font-semibold text-[#3D4A44] mb-4">Top Earning Songs</h3>
          <div className="space-y-2">
            {data.top_songs.map((song, i) => {
              const maxNet = data.top_songs[0]?.net_total || 1
              const pct = (song.net_total / maxNet) * 100
              return (
                <div key={i} className="cursor-pointer hover:bg-[rgba(91,138,114,0.04)] rounded-xl p-2 transition-colors" onClick={() => setSelectedSong(song.song_id)}>
                  <div className="flex items-center justify-between mb-1">
                    <div className="flex items-center gap-3">
                      <span className="w-6 h-6 flex items-center justify-center rounded-full bg-[rgba(91,138,114,0.1)] text-xs font-bold text-[#5B8A72]">{i + 1}</span>
                      <div>
                        <p className="text-sm font-medium text-[#3D4A44]">{song.title}</p>
                        <p className="text-xs text-[#7A8580]">{song.artist}</p>
                      </div>
                    </div>
                    <span className="text-sm font-semibold text-[#3D4A44]">{formatDollars(song.net_total)}</span>
                  </div>
                  <div className="h-1.5 bg-[rgba(59,77,67,0.06)] rounded-full overflow-hidden ml-9">
                    <div className="h-full bg-gradient-to-r from-[#5B8A72] to-[#7BA594] rounded-full" style={{ width: `${pct}%` }} />
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {selectedSong && (
        <SongAnalyticsPanel songData={songData} loading={songLoading} onClose={() => { setSelectedSong(null); setSongData(null) }} />
      )}
    </div>
  )
}


function MetricCard({ label, value, sub }) {
  return (
    <div className="bg-white/80 backdrop-blur-xl rounded-[18px] shadow-am border border-[rgba(59,77,67,0.08)] p-5">
      <p className="text-xs text-[#7A8580] mb-1">{label}</p>
      <p className="text-2xl font-bold text-[#3D4A44]">{value}</p>
      {sub && <p className="text-xs text-[#A0A8A3] mt-1">{sub}</p>}
    </div>
  )
}


function SongAnalyticsPanel({ songData, loading, onClose }) {
  if (loading) {
    return (
      <div className="bg-white/80 backdrop-blur-xl rounded-[18px] shadow-am border border-[rgba(59,77,67,0.08)] p-6">
        <div className="flex justify-center py-8">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[#5B8A72]" />
        </div>
      </div>
    )
  }

  if (!songData || songData.error) {
    return null
  }

  return (
    <div className="bg-white/80 backdrop-blur-xl rounded-[18px] shadow-am border border-[rgba(59,77,67,0.08)] p-6">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <MusicalNoteIcon className="w-5 h-5 text-[#5B8A72]" />
          <div>
            <h3 className="text-sm font-semibold text-[#3D4A44]">{songData.song?.title}</h3>
            <p className="text-xs text-[#7A8580]">{songData.song?.artist}</p>
          </div>
        </div>
        <button onClick={onClose} className="text-xs text-[#7A8580] hover:text-[#3D4A44] px-3 py-1.5 border border-[rgba(59,77,67,0.15)] rounded-lg">Close</button>
      </div>

      {songData.decay && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-4">
          <div className="text-center p-2 bg-[rgba(91,138,114,0.06)] rounded-xl">
            <p className="text-xs text-[#7A8580]">Half-Life</p>
            <p className="text-lg font-bold text-[#3D4A44]">{songData.decay.half_life_periods.toFixed(1)} Q</p>
          </div>
          <div className="text-center p-2 bg-[rgba(91,138,114,0.06)] rounded-xl">
            <p className="text-xs text-[#7A8580]">Decay Rate</p>
            <p className="text-lg font-bold text-[#3D4A44]">{songData.decay.k_per_period.toFixed(3)}/Q</p>
          </div>
          <div className="text-center p-2 bg-[rgba(91,138,114,0.06)] rounded-xl">
            <p className="text-xs text-[#7A8580]">Fit Quality</p>
            <p className={`text-lg font-bold ${songData.decay.r2_log >= 0.7 ? 'text-green-600' : songData.decay.r2_log >= 0.4 ? 'text-amber-600' : 'text-red-500'}`}>
              {songData.decay.decay_quality}
            </p>
          </div>
          <div className="text-center p-2 bg-[rgba(91,138,114,0.06)] rounded-xl">
            <p className="text-xs text-[#7A8580]">Peak</p>
            <p className="text-lg font-bold text-[#3D4A44]">{formatDollars(songData.decay.peak_value)}</p>
          </div>
        </div>
      )}

      {songData.time_series?.length > 0 && (
        <ResponsiveContainer width="100%" height={200}>
          <LineChart data={songData.time_series}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(59,77,67,0.08)" />
            <XAxis dataKey="period" tick={{ fontSize: 10, fill: '#7A8580' }} />
            <YAxis tickFormatter={v => `$${(v / 1000).toFixed(0)}k`} tick={{ fontSize: 11, fill: '#7A8580' }} />
            <Tooltip formatter={v => formatDollars(v)} />
            <Line type="monotone" dataKey="net" stroke="#5B8A72" strokeWidth={2} dot={{ fill: '#5B8A72', r: 3 }} name="Net Revenue" />
          </LineChart>
        </ResponsiveContainer>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mt-4">
        {songData.by_right_category?.length > 0 && (
          <div>
            <h4 className="text-xs font-semibold text-[#7A8580] mb-2">By Right Type</h4>
            {songData.by_right_category.map((r, i) => (
              <div key={i} className="flex justify-between text-xs py-1">
                <span className="text-[#3D4A44] capitalize">{r.category?.replace(/_/g, ' ')}</span>
                <span className="font-medium text-[#3D4A44]">{formatDollars(r.net_total)}</span>
              </div>
            ))}
          </div>
        )}
        {songData.by_territory?.length > 0 && (
          <div>
            <h4 className="text-xs font-semibold text-[#7A8580] mb-2">Top Territories</h4>
            {songData.by_territory.map((t, i) => (
              <div key={i} className="flex justify-between text-xs py-1">
                <span className="text-[#3D4A44]">{t.territory}</span>
                <span className="font-medium text-[#3D4A44]">{formatDollars(t.net_total)}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

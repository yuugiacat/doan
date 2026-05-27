import { AttentionScore, AttentionState } from '../../types'

const STATE_LABELS: Record<AttentionState, string> = {
  focused: 'Đang học',
  distracted: 'Mất tập trung',
  on_phone: 'Dùng điện thoại',
  sleepy: 'Mệt mỏi / Buồn ngủ',
}

const STATE_ICONS: Record<AttentionState, string> = {
  focused: '📖',
  distracted: '😵',
  on_phone: '📱',
  sleepy: '😴',
}

const STATE_COLORS: Record<AttentionState, string> = {
  focused: 'text-green-400',
  distracted: 'text-orange-400',
  on_phone: 'text-red-400',
  sleepy: 'text-purple-400',
}

const STATE_BG: Record<AttentionState, string> = {
  focused: 'bg-green-500',
  distracted: 'bg-orange-500',
  on_phone: 'bg-red-500',
  sleepy: 'bg-purple-500',
}

const GAUGE_COLOR: Record<AttentionState, string> = {
  focused: '#22c55e',
  distracted: '#f97316',
  on_phone: '#ef4444',
  sleepy: '#a855f7',
}

interface Props {
  score: AttentionScore | null
  activeComposites: string[]
}

export default function AttentionMeter({ score, activeComposites }: Props) {
  const value = score?.score ?? 0
  const state = score?.state ?? 'focused'

  return (
    <div className="bg-gray-800 rounded-2xl p-6 flex flex-col gap-4">
      <h2 className="text-lg font-semibold text-gray-200">Độ tập trung</h2>

      {/* Circular gauge */}
      <div className="flex justify-center">
        <div className="relative w-36 h-36">
          <svg viewBox="0 0 100 100" className="w-full h-full -rotate-90">
            <circle cx="50" cy="50" r="42" fill="none" stroke="#374151" strokeWidth="10" />
            <circle
              cx="50" cy="50" r="42" fill="none"
              stroke={GAUGE_COLOR[state]}
              strokeWidth="10"
              strokeDasharray={`${(value / 100) * 263.9} 263.9`}
              strokeLinecap="round"
              style={{ transition: 'stroke-dasharray 0.5s ease' }}
            />
          </svg>
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <span className="text-3xl font-bold text-white">{Math.round(value)}</span>
            <span className="text-xs text-gray-400">/ 100</span>
          </div>
        </div>
      </div>

      {/* State label */}
      <div className={`text-center font-semibold text-lg flex items-center justify-center gap-2 ${STATE_COLORS[state]}`}>
        <span>{STATE_ICONS[state]}</span>
        <span>{STATE_LABELS[state]}</span>
      </div>

      {/* Progress bar */}
      <div className="h-3 bg-gray-700 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-500 ${STATE_BG[state]}`}
          style={{ width: `${value}%` }}
        />
      </div>

      {/* Active composites */}
      {activeComposites.length > 0 && (
        <div className="flex flex-wrap gap-1 mt-1">
          {activeComposites.map((c) => (
            <span key={c} className="text-xs px-2 py-0.5 rounded-full bg-gray-700 text-gray-300">
              {c.replace(/_/g, ' ')}
            </span>
          ))}
        </div>
      )}
    </div>
  )
}

import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { api } from '../services/api'
import { SessionReport as IReport } from '../types'
import FocusTimeline from '../components/analytics/FocusTimeline'
import EmotionHeatmap from '../components/analytics/EmotionHeatmap'
import AdviceCard from '../components/recommendation/AdviceCard'

export default function SessionReport() {
  const { sessionId } = useParams<{ sessionId: string }>()
  const [report, setReport] = useState<IReport | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!sessionId) return
    api.getReport(sessionId)
      .then(setReport)
      .finally(() => setLoading(false))
  }, [sessionId])

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-950 flex items-center justify-center text-gray-400">
        Đang tải báo cáo...
      </div>
    )
  }

  if (!report) {
    return (
      <div className="min-h-screen bg-gray-950 flex items-center justify-center text-red-400">
        Không tìm thấy phiên học.
      </div>
    )
  }

  const a = report.analysis
  const duration = report.ended_at
    ? Math.round((report.ended_at - report.started_at) / 60)
    : null

  return (
    <div className="min-h-screen bg-gray-950 text-white p-6">
      <div className="max-w-4xl mx-auto space-y-6">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold">📊 Báo cáo phiên học</h1>
          <Link to="/" className="text-blue-400 hover:text-blue-300 text-sm">
            ← Học tiếp
          </Link>
        </div>

        {/* Summary cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <StatCard label="Điểm TB" value={`${a.overall_score}`} color="blue" />
          <StatCard label="Điểm cao nhất" value={`${a.peak_score}`} color="green" />
          <StatCard label="📖 Đang học" value={`${a.focused_pct}%`} color="green" />
          <StatCard label="😴 Mệt mỏi" value={`${a.sleepy_pct}%`} color="purple" />
        </div>

        {/* Duration & episodes */}
        <div className="bg-gray-800 rounded-2xl p-5 grid grid-cols-2 md:grid-cols-3 gap-4 text-sm">
          {duration && <Info label="Thời gian học" value={`${duration} phút`} />}
          <Info label="Số lần sao nhãng" value={String(a.distraction_episodes)} />
          <Info label="Nguyên nhân chính" value={a.main_distraction_cause?.replace(/_/g, ' ') ?? 'Không có'} />
        </div>

        {/* State distribution */}
        <div className="bg-gray-800 rounded-2xl p-5">
          <h3 className="text-sm font-semibold text-gray-300 mb-3">Phân phối trạng thái</h3>
          <div className="flex h-8 rounded-full overflow-hidden">
            {a.focused_pct > 0 && (
              <div className="bg-green-500" style={{ width: `${a.focused_pct}%` }} title={`Đang học ${a.focused_pct}%`} />
            )}
            {a.distracted_pct > 0 && (
              <div className="bg-orange-500" style={{ width: `${a.distracted_pct}%` }} title={`Mất tập trung ${a.distracted_pct}%`} />
            )}
            {a.on_phone_pct > 0 && (
              <div className="bg-red-500" style={{ width: `${a.on_phone_pct}%` }} title={`Dùng điện thoại ${a.on_phone_pct}%`} />
            )}
            {a.sleepy_pct > 0 && (
              <div className="bg-purple-500" style={{ width: `${a.sleepy_pct}%` }} title={`Mệt mỏi ${a.sleepy_pct}%`} />
            )}
          </div>
          <div className="flex flex-wrap gap-4 mt-2 text-xs text-gray-400">
            <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-green-500 inline-block" /> 📖 Đang học {a.focused_pct}%</span>
            <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-orange-500 inline-block" /> 😵 Mất tập trung {a.distracted_pct}%</span>
            <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-red-500 inline-block" /> 📱 Dùng điện thoại {a.on_phone_pct}%</span>
            <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-purple-500 inline-block" /> 😴 Mệt mỏi {a.sleepy_pct}%</span>
          </div>
        </div>

        {/* Timeline */}
        {report.attention_scores.length > 0 && (
          <FocusTimeline history={report.attention_scores} />
        )}

        {/* Emotion heatmap */}
        {Object.keys(a.expression_counts).length > 0 && (
          <EmotionHeatmap counts={a.expression_counts} />
        )}

        {/* Advice */}
        <AdviceCard advice={report.advice} />
      </div>
    </div>
  )
}

function StatCard({ label, value, color }: { label: string; value: string; color: string }) {
  const colorMap: Record<string, string> = {
    blue: 'text-blue-400',
    green: 'text-green-400',
    red: 'text-red-400',
    purple: 'text-purple-400',
  }
  return (
    <div className="bg-gray-800 rounded-2xl p-4 text-center">
      <p className={`text-2xl font-bold ${colorMap[color]}`}>{value}</p>
      <p className="text-xs text-gray-400 mt-1">{label}</p>
    </div>
  )
}

function Info({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-gray-400 text-xs">{label}</p>
      <p className="text-white font-semibold capitalize">{value}</p>
    </div>
  )
}

import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../services/api'
import { SessionInfo } from '../types'

export default function Dashboard() {
  const [sessions, setSessions] = useState<SessionInfo[]>([])

  useEffect(() => {
    api.listSessions().then(setSessions)
  }, [])

  return (
    <div className="min-h-screen bg-gray-950 text-white p-6">
      <div className="max-w-3xl mx-auto space-y-6">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold">📈 Dashboard</h1>
          <Link
            to="/"
            className="bg-blue-600 hover:bg-blue-500 px-4 py-2 rounded-xl text-sm font-semibold transition"
          >
            + Phiên mới
          </Link>
        </div>

        {sessions.length === 0 ? (
          <div className="text-center text-gray-500 py-16">
            <p className="text-lg">Chưa có phiên học nào</p>
            <Link to="/" className="text-blue-400 hover:text-blue-300 mt-2 inline-block">
              Bắt đầu phiên đầu tiên →
            </Link>
          </div>
        ) : (
          <div className="space-y-3">
            {[...sessions].reverse().map((s) => (
              <SessionCard key={s.id} session={s} />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

function SessionCard({ session: s }: { session: SessionInfo }) {
  const date = new Date(s.started_at * 1000).toLocaleString('vi-VN')
  const duration = s.ended_at
    ? Math.round((s.ended_at - s.started_at) / 60)
    : null
  const score = s.overall_score !== null ? Math.round(s.overall_score) : null
  const scoreColor =
    score === null ? 'text-gray-400'
    : score >= 80 ? 'text-green-400'
    : score >= 50 ? 'text-yellow-400'
    : score >= 20 ? 'text-orange-400'
    : 'text-red-400'

  return (
    <div className="bg-gray-800 rounded-2xl p-4 flex items-center justify-between">
      <div>
        <p className="text-sm text-gray-300">{date}</p>
        <div className="flex gap-3 mt-1 text-xs text-gray-500">
          {duration && <span>{duration} phút</span>}
          <span>{s.event_count} events</span>
          <span>{s.alert_count} cảnh báo</span>
        </div>
      </div>
      <div className="flex items-center gap-4">
        <div className="text-right">
          <p className={`text-2xl font-bold ${scoreColor}`}>
            {score !== null ? score : '—'}
          </p>
          <p className="text-xs text-gray-500">điểm TB</p>
        </div>
        <Link
          to={`/report/${s.id}`}
          className="text-xs text-blue-400 hover:text-blue-300 border border-blue-700 px-3 py-1.5 rounded-lg transition"
        >
          Xem báo cáo
        </Link>
      </div>
    </div>
  )
}

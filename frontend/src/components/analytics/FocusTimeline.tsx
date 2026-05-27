import { LineChart, Line, XAxis, YAxis, Tooltip, ReferenceLine, ResponsiveContainer } from 'recharts'
import { AttentionScore } from '../../types'

interface Props {
  history: AttentionScore[]
}

export default function FocusTimeline({ history }: Props) {
  const data = history.slice(-600).map((s) => ({
    t: new Date(s.timestamp * 1000).toLocaleTimeString('vi-VN', { minute: '2-digit', second: '2-digit' }),
    score: s.score,
  }))

  return (
    <div className="bg-gray-800 rounded-2xl p-4">
      <h3 className="text-sm font-semibold text-gray-300 mb-3">Timeline tập trung (10 phút gần nhất)</h3>
      <ResponsiveContainer width="100%" height={140}>
        <LineChart data={data}>
          <XAxis dataKey="t" tick={{ fontSize: 10, fill: '#9ca3af' }} interval="preserveStartEnd" />
          <YAxis domain={[0, 100]} tick={{ fontSize: 10, fill: '#9ca3af' }} width={30} />
          <Tooltip
            contentStyle={{ background: '#1f2937', border: 'none', borderRadius: 8 }}
            labelStyle={{ color: '#9ca3af' }}
            formatter={(v: number) => [`${v}`, 'Điểm']}
          />
          <ReferenceLine y={80} stroke="#22c55e" strokeDasharray="4 4" strokeOpacity={0.5} />
          <ReferenceLine y={50} stroke="#eab308" strokeDasharray="4 4" strokeOpacity={0.5} />
          <ReferenceLine y={20} stroke="#f97316" strokeDasharray="4 4" strokeOpacity={0.5} />
          <Line
            type="monotone"
            dataKey="score"
            stroke="#60a5fa"
            strokeWidth={2}
            dot={false}
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}

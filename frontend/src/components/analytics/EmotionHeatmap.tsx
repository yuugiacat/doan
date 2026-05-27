import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts'

const EMOTION_COLORS: Record<string, string> = {
  neutral: '#6b7280',
  happy: '#22c55e',
  surprise: '#3b82f6',
  sad: '#8b5cf6',
  angry: '#ef4444',
  fear: '#f97316',
  disgust: '#84cc16',
}

const EMOTION_LABELS: Record<string, string> = {
  neutral: 'Bình thường',
  happy: 'Vui vẻ',
  surprise: 'Ngạc nhiên',
  sad: 'Buồn',
  angry: 'Tức giận',
  fear: 'Lo lắng',
  disgust: 'Khó chịu',
}

interface Props {
  counts: Record<string, number>
}

export default function EmotionHeatmap({ counts }: Props) {
  const data = Object.entries(counts).map(([key, value]) => ({
    name: EMOTION_LABELS[key] ?? key,
    key,
    value,
  }))

  return (
    <div className="bg-gray-800 rounded-2xl p-4">
      <h3 className="text-sm font-semibold text-gray-300 mb-3">Phân phối biểu cảm</h3>
      <ResponsiveContainer width="100%" height={160}>
        <BarChart data={data} layout="vertical">
          <XAxis type="number" tick={{ fontSize: 10, fill: '#9ca3af' }} />
          <YAxis dataKey="name" type="category" tick={{ fontSize: 10, fill: '#9ca3af' }} width={70} />
          <Tooltip
            contentStyle={{ background: '#1f2937', border: 'none', borderRadius: 8 }}
            formatter={(v: number) => [v, 'Số lần']}
          />
          <Bar dataKey="value" radius={[0, 4, 4, 0]}>
            {data.map((entry) => (
              <Cell key={entry.key} fill={EMOTION_COLORS[entry.key] ?? '#60a5fa'} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}

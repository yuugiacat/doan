interface Props {
  advice: string[]
}

export default function AdviceCard({ advice }: Props) {
  if (!advice.length) return null
  return (
    <div className="bg-blue-900/30 border border-blue-700 rounded-2xl p-5">
      <h3 className="text-blue-300 font-semibold mb-3 flex items-center gap-2">
        <span>📋</span> Lời khuyên cải thiện
      </h3>
      <ul className="space-y-2">
        {advice.map((a, i) => (
          <li key={i} className="flex items-start gap-2 text-sm text-gray-300">
            <span className="text-blue-400 mt-0.5">•</span>
            <span>{a}</span>
          </li>
        ))}
      </ul>
    </div>
  )
}

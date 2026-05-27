import { useEffect, useState } from 'react'
import { Alert, AlertType } from '../../types'

const STYLES: Record<AlertType, string> = {
  nudge: 'bg-yellow-500/20 border-yellow-500 text-yellow-300',
  alert: 'bg-orange-500/20 border-orange-500 text-orange-300',
  strong_alert: 'bg-red-500/20 border-red-500 text-red-300 animate-pulse',
}

const ICONS: Record<AlertType, string> = {
  nudge: '💡',
  alert: '⚠️',
  strong_alert: '🚨',
}

interface Props {
  alert: Alert | null
}

export default function AlertBanner({ alert }: Props) {
  const [visible, setVisible] = useState(false)

  useEffect(() => {
    if (alert) {
      setVisible(true)
      const t = setTimeout(() => setVisible(false), 8000)
      return () => clearTimeout(t)
    }
  }, [alert])

  if (!visible || !alert) return null

  return (
    <div
      className={`fixed top-4 right-4 z-50 max-w-sm border rounded-xl p-4 shadow-xl backdrop-blur transition-all ${STYLES[alert.alert_type]}`}
    >
      <div className="flex items-start gap-3">
        <span className="text-2xl">{ICONS[alert.alert_type]}</span>
        <div className="flex-1">
          <p className="font-semibold text-sm">{alert.message}</p>
          <p className="text-xs opacity-70 mt-1">{alert.reason.replace(/_/g, ' ')}</p>
        </div>
        <button onClick={() => setVisible(false)} className="text-sm opacity-60 hover:opacity-100">
          ✕
        </button>
      </div>
    </div>
  )
}

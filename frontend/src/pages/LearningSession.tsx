import { useCallback, useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../services/api'
import { useWebSocket } from '../hooks/useWebSocket'
import { useSessionStore } from '../store/sessionStore'
import WebcamView from '../components/webcam/WebcamView'
import AttentionMeter from '../components/analytics/AttentionMeter'
import FocusTimeline from '../components/analytics/FocusTimeline'
import AlertBanner from '../components/recommendation/AlertBanner'
import { FeatureFrame } from '../types'

const CALIBRATION_SECS = 30

export default function LearningSession() {
  const navigate = useNavigate()
  const {
    sessionId, isActive, isCalibrating, calibrationProgress,
    currentScore, scoreHistory, activeComposites, latestAlert,
    setSessionId, setActive, setCalibrating, setCalibrationProgress, reset,
  } = useSessionStore()

  const { sendFrame, sendCalibration } = useWebSocket(sessionId)
  const calibTimerRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const [consent, setConsent] = useState(false)
  const [sessionDuration, setSessionDuration] = useState(0)
  const durationRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const startSession = async () => {
    const { session_id } = await api.createSession()
    setSessionId(session_id)
    setActive(true)
    setCalibrating(true)
    setCalibrationProgress(0)

    let elapsed = 0
    calibTimerRef.current = setInterval(() => {
      elapsed += 1
      setCalibrationProgress(Math.round((elapsed / CALIBRATION_SECS) * 100))
      if (elapsed >= CALIBRATION_SECS) {
        clearInterval(calibTimerRef.current!)
        setCalibrating(false)
        sendCalibration({ calibrated: true, timestamp: Date.now() / 1000 })
      }
    }, 1000)

    durationRef.current = setInterval(() => setSessionDuration((d) => d + 1), 1000)
  }

  const stopSession = async () => {
    if (!sessionId) return
    clearInterval(calibTimerRef.current!)
    clearInterval(durationRef.current!)
    setActive(false)
    await api.endSession(sessionId)
    navigate(`/report/${sessionId}`)
    reset()
  }

  const onFrame = useCallback(
    (frame: FeatureFrame) => {
      if (isActive) sendFrame(frame)
    },
    [isActive, sendFrame]
  )

  useEffect(() => () => {
    clearInterval(calibTimerRef.current!)
    clearInterval(durationRef.current!)
  }, [])

  const formatDuration = (s: number) =>
    `${String(Math.floor(s / 60)).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`

  if (!consent) {
    return (
      <div className="min-h-screen bg-gray-950 flex items-center justify-center p-8">
        <div className="max-w-lg bg-gray-800 rounded-2xl p-8 space-y-5">
          <h1 className="text-2xl font-bold text-white">🎓 Learning Analytics AI</h1>
          <div className="text-gray-300 space-y-3 text-sm">
            <p>Ứng dụng sẽ sử dụng webcam của bạn để phân tích hành vi học tập trong thời gian thực.</p>
            <ul className="list-disc pl-5 space-y-1">
              <li>Không lưu video hay hình ảnh</li>
              <li>Chỉ lưu các sự kiện hành vi đã được trừu tượng hóa</li>
              <li>Xử lý hoàn toàn trên thiết bị của bạn</li>
              <li>Bạn có thể dừng bất kỳ lúc nào</li>
            </ul>
          </div>
          <button
            onClick={() => setConsent(true)}
            className="w-full bg-blue-600 hover:bg-blue-500 text-white py-3 rounded-xl font-semibold transition"
          >
            Tôi đồng ý — Bắt đầu
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-950 text-white p-6">
      <AlertBanner alert={latestAlert} />

      <div className="max-w-5xl mx-auto space-y-5">
        {/* Header */}
        <div className="flex items-center justify-between">
          <h1 className="text-xl font-bold">🎓 Phiên học</h1>
          <div className="flex items-center gap-4">
            {isActive && (
              <span className="text-gray-400 text-sm font-mono">{formatDuration(sessionDuration)}</span>
            )}
            {!isActive ? (
              <button
                onClick={startSession}
                className="bg-green-600 hover:bg-green-500 px-5 py-2 rounded-xl font-semibold transition"
              >
                Bắt đầu học
              </button>
            ) : (
              <button
                onClick={stopSession}
                className="bg-red-600 hover:bg-red-500 px-5 py-2 rounded-xl font-semibold transition"
              >
                Kết thúc
              </button>
            )}
          </div>
        </div>

        {/* Calibration banner */}
        {isCalibrating && (
          <div className="bg-blue-900/40 border border-blue-600 rounded-xl p-4">
            <p className="text-blue-300 font-medium">
              🔧 Đang hiệu chỉnh ({calibrationProgress}%) — Hãy ngồi thẳng và nhìn vào màn hình
            </p>
            <div className="mt-2 h-2 bg-gray-700 rounded-full overflow-hidden">
              <div
                className="h-full bg-blue-500 transition-all duration-1000"
                style={{ width: `${calibrationProgress}%` }}
              />
            </div>
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-5 gap-5">
          {/* Webcam */}
          <div className="lg:col-span-3">
            <WebcamView onFrame={onFrame} enabled={isActive} />
          </div>

          {/* Attention meter */}
          <div className="lg:col-span-2">
            <AttentionMeter score={currentScore} activeComposites={activeComposites} />
          </div>
        </div>

        {/* Timeline */}
        {scoreHistory.length > 2 && (
          <FocusTimeline history={scoreHistory} />
        )}
      </div>
    </div>
  )
}

import { useCallback, useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../services/api'
import { userIdentity } from '../services/userIdentity'
import { useWebSocket } from '../hooks/useWebSocket'
import { useSessionStore } from '../store/sessionStore'
import WebcamView from '../components/webcam/WebcamView'
import AttentionMeter from '../components/analytics/AttentionMeter'
import FocusTimeline from '../components/analytics/FocusTimeline'
import AlertBanner from '../components/recommendation/AlertBanner'
import { FeatureFrame } from '../types'

const CALIBRATION_SECS = 30
const POMODORO_SECS = 25 * 60        // phiên Pomodoro chuẩn: 25 phút
const SHORT_SESSION_WARN_SECS = 10 * 60   // dưới 10p thì data không đủ → cảnh báo trước khi dừng

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
  const [consentResearch, setConsentResearch] = useState(
    () => userIdentity.getConsentResearch()
  )
  const [email, setEmail] = useState(() => userIdentity.getEmail())
  const [displayName, setDisplayName] = useState(() => userIdentity.getName())
  const [sessionDuration, setSessionDuration] = useState(0)
  const durationRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const startSession = async () => {
    // Xoá dữ liệu phiên cũ (score history, alerts, composites) trước khi
    // tạo phiên mới — phòng trường hợp phiên trước không reset đúng cách
    // (api.endSession lỗi, user vào lại bằng back browser, refresh, v.v.).
    reset()
    setSessionDuration(0)
    // Lưu lại để lần sau prefill
    userIdentity.setEmail(email)
    userIdentity.setName(displayName)
    userIdentity.setConsentResearch(consentResearch)

    const { session_id } = await api.createSession({
      anonymous_id: userIdentity.getAnonymousId(),
      email: email.trim() || null,
      display_name: displayName.trim() || null,
      consent_research: consentResearch,
    })
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

  // Tự động kết thúc khi đủ 25 phút Pomodoro
  useEffect(() => {
    if (isActive && sessionDuration >= POMODORO_SECS) {
      void stopSession()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionDuration, isActive])

  // Nút "Kết thúc" — cảnh báo nếu dừng sớm dưới 10 phút
  const handleStopClick = async () => {
    if (sessionDuration < SHORT_SESSION_WARN_SECS) {
      const ok = window.confirm(
        `Phiên mới ${Math.floor(sessionDuration / 60)} phút — dưới 10 phút sẽ không đủ dữ liệu để phân tích. Vẫn kết thúc?`
      )
      if (!ok) return
    }
    await stopSession()
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
            <p>Ứng dụng sử dụng webcam để phân tích hành vi học tập theo thời gian thực.</p>
            <ul className="list-disc pl-5 space-y-1">
              <li><b>Không lưu video hay hình ảnh</b></li>
              <li>Chỉ lưu các sự kiện hành vi đã trừu tượng hoá (head pose, mắt mở/nhắm, cúi đầu...)</li>
              <li>Phân tích MediaPipe chạy hoàn toàn trên trình duyệt của bạn</li>
              <li>Bạn có thể dừng bất kỳ lúc nào</li>
            </ul>
          </div>

          <div className="bg-gray-900/60 border border-gray-700 rounded-xl p-4 space-y-3">
            <p className="text-sm text-gray-300 font-semibold">
              📊 Đóng góp cho đồ án nghiên cứu (tuỳ chọn)
            </p>
            <p className="text-xs text-gray-400">
              Nếu đồng ý, dữ liệu phiên học (không có video) sẽ được lưu để chủ đồ án phân tích.
              Bạn có thể nhập email/tên để tiện liên hệ (không bắt buộc).
            </p>
            <label className="flex items-start gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={consentResearch}
                onChange={(e) => setConsentResearch(e.target.checked)}
                className="mt-0.5"
              />
              <span className="text-sm text-gray-200">
                Đồng ý chia sẻ dữ liệu hành vi học tập cho nghiên cứu
              </span>
            </label>
            {consentResearch && (
              <div className="space-y-2 pt-1">
                <input
                  type="text"
                  placeholder="Tên (tuỳ chọn)"
                  value={displayName}
                  onChange={(e) => setDisplayName(e.target.value)}
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white placeholder-gray-500"
                />
                <input
                  type="email"
                  placeholder="Email (tuỳ chọn)"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white placeholder-gray-500"
                />
              </div>
            )}
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
          <h1 className="text-xl font-bold">🍅 Phiên Pomodoro 25 phút</h1>
          <div className="flex items-center gap-4">
            {isActive && (
              <div className="text-right">
                <div className="text-gray-400 text-xs">Còn lại</div>
                <div className="text-2xl font-mono font-bold text-white">
                  {formatDuration(Math.max(0, POMODORO_SECS - sessionDuration))}
                </div>
              </div>
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
                onClick={handleStopClick}
                className="bg-red-600 hover:bg-red-500 px-5 py-2 rounded-xl font-semibold transition"
              >
                Kết thúc
              </button>
            )}
          </div>
        </div>

        {/* Pomodoro progress bar */}
        {isActive && !isCalibrating && (
          <div className="h-1.5 bg-gray-800 rounded-full overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-green-500 to-red-500 transition-all duration-1000"
              style={{ width: `${Math.min(100, (sessionDuration / POMODORO_SECS) * 100)}%` }}
            />
          </div>
        )}

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

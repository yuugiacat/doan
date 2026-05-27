import { useEffect, useRef } from 'react'
import { useWebcam } from '../../hooks/useWebcam'
import { useMediaPipe } from '../../hooks/useMediaPipe'
import { FeatureFrame } from '../../types'

interface Props {
  onFrame: (frame: FeatureFrame) => void
  enabled: boolean
}

export default function WebcamView({ onFrame, enabled }: Props) {
  const { videoRef, ready, error, start, stop } = useWebcam()
  const overlayRef = useRef<HTMLCanvasElement>(null)
  const { ready: mpReady, initError, phoneDetected } =
    useMediaPipe(videoRef, onFrame, enabled && ready, overlayRef)

  useEffect(() => {
    if (enabled) start()
    else stop()
  }, [enabled, start, stop])

  return (
    <div className="relative bg-gray-900 rounded-2xl overflow-hidden aspect-video">
      <video
        ref={videoRef}
        className="w-full h-full object-cover mirror"
        muted
        playsInline
      />

      {/* Canvas overlay — vẽ khung + nhãn điện thoại (không mirror để chữ đọc xuôi) */}
      <canvas
        ref={overlayRef}
        className="absolute inset-0 w-full h-full object-cover pointer-events-none"
      />

      {/* Cảnh báo phát hiện điện thoại */}
      {phoneDetected && (
        <div className="absolute top-2 right-2 bg-orange-600/90 text-white text-xs font-semibold px-2.5 py-1 rounded-full flex items-center gap-1 animate-pulse">
          📱 Phát hiện điện thoại
        </div>
      )}

      {/* Status overlay */}
      {!ready && (
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="text-center text-gray-400">
            {error ? (
              <p className="text-red-400">{error}</p>
            ) : (
              <p>Đang khởi động webcam...</p>
            )}
          </div>
        </div>
      )}

      {ready && !mpReady && (
        <div className="absolute top-2 left-2 bg-yellow-900/80 text-yellow-300 text-xs px-2 py-1 rounded">
          Đang tải MediaPipe...
          {initError && <span className="text-red-300 ml-1">({initError})</span>}
        </div>
      )}

      {ready && mpReady && (
        <div className="absolute top-2 left-2 flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full bg-green-400 animate-pulse" />
          <span className="text-xs text-green-300">Đang quan sát</span>
        </div>
      )}

      <style>{`.mirror { transform: scaleX(-1); }`}</style>
    </div>
  )
}

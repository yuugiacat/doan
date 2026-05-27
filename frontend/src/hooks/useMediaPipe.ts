/**
 * MediaPipe feature extractor hook.
 * FaceLandmarker  — EAR, head-pose, gaze, mouth
 * ObjectDetector  — phát hiện điện thoại (chạy mỗi 10 frame ~3fps)
 */
import { useCallback, useEffect, useRef, useState } from 'react'
import type { FeatureFrame } from '../types'

type FaceLandmarker   = any
type ObjectDetector   = any

const WASM_PATH = 'https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.14/wasm'

const FACE_MODEL_URL =
  'https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task'

// EfficientDet-Lite2 — nhận diện "cell phone" từ COCO (chính xác hơn Lite0)
const OD_MODEL_URL =
  'https://storage.googleapis.com/mediapipe-models/object_detector/efficientdet_lite2/float32/1/efficientdet_lite2.tflite'

const LEFT_EYE_INDICES  = [33, 160, 158, 133, 153, 144]
const RIGHT_EYE_INDICES = [362, 385, 387, 263, 373, 380]
const MOUTH_TOP    = 13
const MOUTH_BOTTOM = 14

function ear(landmarks: any[], indices: number[]): number {
  const p = (i: number) => landmarks[indices[i]]
  const A = dist(p(1), p(5))
  const B = dist(p(2), p(4))
  const C = dist(p(0), p(3))
  return (A + B) / (2.0 * C + 1e-6)
}

function dist(a: any, b: any): number {
  const dx = a.x - b.x, dy = a.y - b.y, dz = (a.z || 0) - (b.z || 0)
  return Math.sqrt(dx * dx + dy * dy + dz * dz)
}

function headPose(landmarks: any[]): { yaw: number; pitch: number; roll: number } {
  const nose     = landmarks[1]
  const leftEye  = landmarks[33]
  const rightEye = landmarks[263]
  const chin     = landmarks[152]
  const forehead = landmarks[10]

  const eyeMidX = (leftEye.x + rightEye.x) / 2
  const yaw = (nose.x - eyeMidX) * 120

  const faceHeight = Math.abs(chin.y - forehead.y) + 1e-6
  const neutralNoseY = forehead.y + faceHeight * 0.60
  const pitch = (neutralNoseY - nose.y) / faceHeight * 90

  const roll = Math.atan2(rightEye.y - leftEye.y, rightEye.x - leftEye.x) * (180 / Math.PI)
  return { yaw, pitch, roll }
}

function gazeDirection(landmarks: any[], pose: ReturnType<typeof headPose>) {
  const absYaw = Math.abs(pose.yaw), absPitch = Math.abs(pose.pitch)
  if (absYaw <= 15 && absPitch <= 15) return 'center'
  if (pose.yaw  >  15) return 'right'
  if (pose.yaw  < -15) return 'left'
  if (pose.pitch < -15) return 'down'
  return 'up'
}

type PhoneBox = { x: number; y: number; w: number; h: number; score: number }

// Vẽ bounding box + nhãn điện thoại. Tọa độ x được lật ngang để khớp với
// video đang mirror (scaleX(-1)); canvas KHÔNG mirror nên chữ vẫn đọc xuôi.
function drawPhoneOverlay(
  canvas: HTMLCanvasElement | null | undefined,
  video: HTMLVideoElement,
  boxes: { x: number; y: number; w: number; h: number; score: number }[]
) {
  if (!canvas) return
  const vw = video.videoWidth, vh = video.videoHeight
  if (!vw || !vh) return
  if (canvas.width !== vw) canvas.width = vw
  if (canvas.height !== vh) canvas.height = vh

  const ctx = canvas.getContext('2d')
  if (!ctx) return
  ctx.clearRect(0, 0, vw, vh)

  for (const b of boxes) {
    const drawX = vw - (b.x + b.w)   // lật ngang cho khớp video mirror
    ctx.lineWidth = Math.max(2, vw / 250)
    ctx.strokeStyle = '#f97316'      // orange-500
    ctx.strokeRect(drawX, b.y, b.w, b.h)

    const label = `📱 Điện thoại ${Math.round(b.score * 100)}%`
    ctx.font = `${Math.max(14, vw / 40)}px sans-serif`
    const padX = 6, textW = ctx.measureText(label).width
    const fontH = Math.max(14, vw / 40)
    const labelY = b.y > fontH + 8 ? b.y - fontH - 6 : b.y + 2
    ctx.fillStyle = '#f97316'
    ctx.fillRect(drawX, labelY, textW + padX * 2, fontH + 6)
    ctx.fillStyle = '#ffffff'
    ctx.textBaseline = 'top'
    ctx.fillText(label, drawX + padX, labelY + 3)
  }
}

export function useMediaPipe(
  videoRef: React.RefObject<HTMLVideoElement>,
  onFrame: (frame: FeatureFrame) => void,
  enabled: boolean,
  overlayCanvasRef?: React.RefObject<HTMLCanvasElement>
) {
  const faceLandmarkerRef = useRef<FaceLandmarker | null>(null)
  const objectDetectorRef = useRef<ObjectDetector | null>(null)
  const rafRef     = useRef<number>(0)
  const frameCount = useRef<number>(0)
  // Cache kết quả phone detection giữa các frame (chỉ re-detect mỗi vài frame)
  const phoneCache = useRef<boolean>(false)
  // Bounding box điện thoại gần nhất để vẽ nhãn lên overlay
  const phoneBoxes = useRef<PhoneBox[]>([])
  const lastPhoneState = useRef<boolean>(false)

  const [ready, setReady]       = useState(false)
  const [initError, setInitError] = useState<string | null>(null)
  const [phoneDetected, setPhoneDetected] = useState(false)

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      try {
        const { FaceLandmarker, ObjectDetector, FilesetResolver } =
          await import('@mediapipe/tasks-vision')
        const vision = await FilesetResolver.forVisionTasks(WASM_PATH)

        const fl = await FaceLandmarker.createFromOptions(vision, {
          baseOptions: { modelAssetPath: FACE_MODEL_URL, delegate: 'GPU' },
          outputFaceBlendshapes: false,
          runningMode: 'VIDEO',
          numFaces: 2,
        })

        // ObjectDetector — chỉ giữ "cell phone", ngưỡng 0.3
        // Thử GPU trước, nếu lỗi (driver/WebGL) thì fallback CPU để vẫn nhận diện được.
        const makeOD = (delegate: 'GPU' | 'CPU') =>
          ObjectDetector.createFromOptions(vision, {
            baseOptions: { modelAssetPath: OD_MODEL_URL, delegate },
            runningMode: 'VIDEO',
            scoreThreshold: 0.3,          // hạ ngưỡng để bắt điện thoại nhạy hơn
            maxResults: 5,
            categoryAllowlist: ['cell phone'],
          })

        let od: ObjectDetector | null = null
        try {
          od = await makeOD('GPU')
        } catch (eGpu) {
          console.warn('ObjectDetector GPU failed, thử CPU:', eGpu)
          try {
            od = await makeOD('CPU')
          } catch (eCpu) {
            console.warn('ObjectDetector load failed — phone detection disabled:', eCpu)
          }
        }

        if (!cancelled) {
          faceLandmarkerRef.current = fl
          objectDetectorRef.current = od
          setReady(true)
        }
      } catch (e: any) {
        if (!cancelled) setInitError(e.message)
      }
    })()
    return () => { cancelled = true }
  }, [])

  const loop = useCallback(() => {
    const video = videoRef.current
    const fl    = faceLandmarkerRef.current
    if (!video || !fl || video.readyState < 2) {
      rafRef.current = requestAnimationFrame(loop)
      return
    }

    const ts = performance.now()
    frameCount.current += 1

    // ── Face ─────────────────────────────────────────────────────
    const faceResult = fl.detectForVideo(video, ts)
    const landmarks  = faceResult?.faceLandmarks?.[0] ?? null
    const count      = faceResult?.faceLandmarks?.length ?? 0

    const detected   = !!landmarks
    const earL       = detected ? ear(landmarks, LEFT_EYE_INDICES)  : 0.3
    const earR       = detected ? ear(landmarks, RIGHT_EYE_INDICES) : 0.3
    const pose       = detected ? headPose(landmarks)                : { yaw: 0, pitch: 0, roll: 0 }
    const direction  = detected ? gazeDirection(landmarks, pose)     : 'center'
    const onScreen   = direction === 'center'
    const mouthRatio = detected ? dist(landmarks[MOUTH_TOP], landmarks[MOUTH_BOTTOM]) : 0

    let bbox = { x: 0.2, y: 0.1, width: 0.4, height: 0.6 }
    if (detected) {
      const xs = landmarks.map((l: any) => l.x)
      const ys = landmarks.map((l: any) => l.y)
      const x = Math.min(...xs), y = Math.min(...ys)
      bbox = { x, y, width: Math.max(...xs) - x, height: Math.max(...ys) - y }
    }

    // ── Phone detection (mỗi 5 frame ~6fps — nhạy hơn trước) ─────
    const od = objectDetectorRef.current
    if (od && frameCount.current % 5 === 0) {
      try {
        const odResult = od.detectForVideo(video, ts)
        const phones = (odResult?.detections ?? []).filter((d: any) =>
          d.categories?.some((c: any) => c.categoryName === 'cell phone')
        )
        phoneCache.current = phones.length > 0
        phoneBoxes.current = phones.map((d: any) => {
          const b = d.boundingBox ?? {}
          const top = d.categories?.find((c: any) => c.categoryName === 'cell phone')
          return {
            x: b.originX ?? 0,
            y: b.originY ?? 0,
            w: b.width ?? 0,
            h: b.height ?? 0,
            score: top?.score ?? 0,
          }
        })
      } catch {
        // ignore per-frame errors
      }
    }

    // Cập nhật state badge chỉ khi đổi trạng thái (tránh re-render 30fps)
    if (phoneCache.current !== lastPhoneState.current) {
      lastPhoneState.current = phoneCache.current
      setPhoneDetected(phoneCache.current)
    }

    // ── Vẽ khung + nhãn "📱 Điện thoại" lên overlay ──────────────
    drawPhoneOverlay(overlayCanvasRef?.current, video, phoneBoxes.current)

    const frame: FeatureFrame = {
      type: 'frame',
      timestamp: Date.now() / 1000,
      face: { detected, count, confidence: detected ? 0.95 : 0, bbox },
      head_pose: pose,
      gaze: {
        on_screen: onScreen,
        direction: direction as any,
        confidence: 0.85,
        ear_left: earL,
        ear_right: earR,
      },
      hands: {
        left:  { detected: false, wrist: { x: 0, y: 0 } },
        right: { detected: false, wrist: { x: 0, y: 0 } },
      },
      expression: {
        neutral: 0.7, happy: 0.1, surprise: 0.05,
        sad: 0.05, angry: 0.03, fear: 0.04, disgust: 0.03,
      },
      pose: { detected: false, left_shoulder_z: 0, right_shoulder_z: 0 },
      mouth_open_ratio: mouthRatio,
      phone_detected: phoneCache.current,
    }

    onFrame(frame)
    rafRef.current = requestAnimationFrame(loop)
  }, [videoRef, onFrame, overlayCanvasRef])

  useEffect(() => {
    if (enabled && ready) {
      rafRef.current = requestAnimationFrame(loop)
    } else {
      cancelAnimationFrame(rafRef.current)
    }
    return () => cancelAnimationFrame(rafRef.current)
  }, [enabled, ready, loop])

  return { ready, initError, phoneDetected }
}

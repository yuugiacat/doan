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

export function useMediaPipe(
  videoRef: React.RefObject<HTMLVideoElement>,
  onFrame: (frame: FeatureFrame) => void,
  enabled: boolean
) {
  const faceLandmarkerRef = useRef<FaceLandmarker | null>(null)
  const objectDetectorRef = useRef<ObjectDetector | null>(null)
  const rafRef     = useRef<number>(0)
  const frameCount = useRef<number>(0)
  // Cache kết quả phone detection giữa các frame (chỉ re-detect mỗi 10 frame)
  const phoneCache = useRef<boolean>(false)

  const [ready, setReady]       = useState(false)
  const [initError, setInitError] = useState<string | null>(null)

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

        // ObjectDetector — chỉ giữ "cell phone", ngưỡng 0.4
        let od: ObjectDetector | null = null
        try {
          od = await ObjectDetector.createFromOptions(vision, {
            baseOptions: { modelAssetPath: OD_MODEL_URL, delegate: 'GPU' },
            runningMode: 'VIDEO',
            scoreThreshold: 0.4,
            categoryAllowlist: ['cell phone'],
          })
        } catch (e) {
          console.warn('ObjectDetector load failed — phone detection disabled:', e)
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

    // ── Phone detection (mỗi 10 frame ~3fps để tiết kiệm CPU) ────
    const od = objectDetectorRef.current
    if (od && frameCount.current % 10 === 0) {
      try {
        const odResult = od.detectForVideo(video, ts)
        phoneCache.current = odResult?.detections?.some((d: any) =>
          d.categories?.some((c: any) => c.categoryName === 'cell phone')
        ) ?? false
      } catch {
        // ignore per-frame errors
      }
    }

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
  }, [videoRef, onFrame])

  useEffect(() => {
    if (enabled && ready) {
      rafRef.current = requestAnimationFrame(loop)
    } else {
      cancelAnimationFrame(rafRef.current)
    }
    return () => cancelAnimationFrame(rafRef.current)
  }, [enabled, ready, loop])

  return { ready, initError }
}

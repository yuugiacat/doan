export type AttentionState =
  | 'focused'
  | 'distracted'
  | 'sleepy'

export type AlertType = 'nudge' | 'alert' | 'strong_alert'

export interface AttentionScore {
  session_id: string
  timestamp: number
  score: number
  state: AttentionState
  active_composites: string[]
}

export interface Alert {
  alert_id: string
  session_id: string
  timestamp: number
  alert_type: AlertType
  reason: string
  message: string
}

export interface BehaviorEvent {
  event_id: string
  session_id: string
  event_type: string
  category: 'atomic' | 'composite'
  event_group: string
  timestamp_start: number
  timestamp_end: number | null
  duration_ms: number | null
  confidence: number
  attributes: Record<string, unknown>
}

export interface FrameResult {
  type: 'frame_processed'
  timestamp: number
  active_composites: string[]
  atomic_count: number
  score: AttentionScore | null
  alert: Alert | null
}

export interface FeatureFrame {
  type: 'frame'
  timestamp: number
  face: {
    detected: boolean
    count: number
    confidence: number
    bbox: { x: number; y: number; width: number; height: number }
  }
  head_pose: { yaw: number; pitch: number; roll: number }
  gaze: {
    on_screen: boolean
    direction: 'center' | 'left' | 'right' | 'up' | 'down'
    confidence: number
    ear_left: number
    ear_right: number
  }
  hands: {
    left: { detected: boolean; wrist: { x: number; y: number } }
    right: { detected: boolean; wrist: { x: number; y: number } }
  }
  expression: {
    neutral: number
    happy: number
    surprise: number
    sad: number
    angry: number
    fear: number
    disgust: number
  }
  pose: {
    detected: boolean
    left_shoulder_z: number
    right_shoulder_z: number
  }
  mouth_open_ratio: number
  phone_detected: boolean
}

export interface SessionInfo {
  id: string
  started_at: number
  ended_at: number | null
  overall_score: number | null
  event_count: number
  score_count: number
  alert_count: number
}

export interface SessionReport extends SessionInfo {
  events: BehaviorEvent[]
  attention_scores: AttentionScore[]
  alerts: Alert[]
  analysis: {
    overall_score: number
    peak_score: number
    focused_pct: number
    distracted_pct: number
    sleepy_pct: number
    distraction_episodes: number
    main_distraction_cause: string | null
    distraction_cause_counts: Record<string, number>
    expression_counts: Record<string, number>
  }
  advice: string[]
}

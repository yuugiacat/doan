import { create } from 'zustand'
import { AttentionScore, Alert, FeatureFrame, SessionInfo } from '../types'

interface SessionState {
  sessionId: string | null
  isActive: boolean
  isCalibrating: boolean
  calibrationProgress: number

  currentScore: AttentionScore | null
  scoreHistory: AttentionScore[]
  activeComposites: string[]
  latestAlert: Alert | null
  alerts: Alert[]

  sessions: SessionInfo[]

  setSessionId: (id: string | null) => void
  setActive: (active: boolean) => void
  setCalibrating: (v: boolean) => void
  setCalibrationProgress: (p: number) => void
  updateScore: (score: AttentionScore) => void
  setActiveComposites: (composites: string[]) => void
  addAlert: (alert: Alert) => void
  setSessions: (sessions: SessionInfo[]) => void
  reset: () => void
}

export const useSessionStore = create<SessionState>((set) => ({
  sessionId: null,
  isActive: false,
  isCalibrating: false,
  calibrationProgress: 0,

  currentScore: null,
  scoreHistory: [],
  activeComposites: [],
  latestAlert: null,
  alerts: [],
  sessions: [],

  setSessionId: (id) => set({ sessionId: id }),
  setActive: (active) => set({ isActive: active }),
  setCalibrating: (v) => set({ isCalibrating: v }),
  setCalibrationProgress: (p) => set({ calibrationProgress: p }),

  updateScore: (score) =>
    set((state) => ({
      currentScore: score,
      scoreHistory: [...state.scoreHistory.slice(-600), score],
    })),

  setActiveComposites: (composites) => set({ activeComposites: composites }),

  addAlert: (alert) =>
    set((state) => ({
      latestAlert: alert,
      alerts: [...state.alerts, alert],
    })),

  setSessions: (sessions) => set({ sessions }),

  reset: () =>
    set({
      sessionId: null,
      isActive: false,
      isCalibrating: false,
      calibrationProgress: 0,
      currentScore: null,
      scoreHistory: [],
      activeComposites: [],
      latestAlert: null,
      alerts: [],
    }),
}))

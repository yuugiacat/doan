import { useCallback, useEffect, useRef } from 'react'
import { FrameResult, FeatureFrame } from '../types'
import { useSessionStore } from '../store/sessionStore'

export function useWebSocket(sessionId: string | null) {
  const wsRef = useRef<WebSocket | null>(null)
  const { updateScore, setActiveComposites, addAlert } = useSessionStore()

  const connect = useCallback(() => {
    if (!sessionId || wsRef.current) return
    const backendUrl = import.meta.env.VITE_BACKEND_URL ?? `${window.location.protocol}//${window.location.host}`
    const wsUrl = backendUrl.replace(/^http/, 'ws')
    const ws = new WebSocket(`${wsUrl}/ws/${sessionId}`)

    ws.onmessage = (evt) => {
      const msg: FrameResult = JSON.parse(evt.data)
      if (msg.type === 'frame_processed') {
        if (msg.score) updateScore(msg.score)
        setActiveComposites(msg.active_composites)
        if (msg.alert) addAlert(msg.alert)
      }
    }

    ws.onerror = () => ws.close()
    ws.onclose = () => { wsRef.current = null }
    wsRef.current = ws
  }, [sessionId, updateScore, setActiveComposites, addAlert])

  const disconnect = useCallback(() => {
    wsRef.current?.close()
    wsRef.current = null
  }, [])

  const sendFrame = useCallback((frame: FeatureFrame) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(frame))
    }
  }, [])

  const sendCalibration = useCallback((baseline: object) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'calibration', baseline }))
    }
  }, [])

  useEffect(() => {
    if (sessionId) connect()
    return () => { disconnect() }
  }, [sessionId, connect, disconnect])

  return { sendFrame, sendCalibration, disconnect }
}

/**
 * Notification helper — bắn thông báo khi phiên Pomodoro kết thúc.
 *
 * 3 kênh đồng thời:
 *   1. Browser Notification API — hiện ở góc OS kể cả khi tab ẩn
 *   2. Web Audio chime — tiếng "ding" 2 nốt, không cần file mp3
 *   3. (toast trong app — do component caller render)
 *
 * Sound dùng Web Audio API thay vì file MP3 vì:
 *   - Không cần asset đi kèm
 *   - Chrome autoplay policy: vẫn play được vì user đã click "Bắt đầu phiên"
 *     trước đó → tab đã có user gesture
 */

export type NotifyPermission = 'granted' | 'denied' | 'default' | 'unsupported'

export function getPermission(): NotifyPermission {
  if (typeof Notification === 'undefined') return 'unsupported'
  return Notification.permission as NotifyPermission
}

export async function requestPermission(): Promise<NotifyPermission> {
  if (typeof Notification === 'undefined') return 'unsupported'
  if (Notification.permission !== 'default') return Notification.permission as NotifyPermission
  const result = await Notification.requestPermission()
  return result as NotifyPermission
}

// Tiếng "ding-ding" 2 nốt (C6 → G6) bằng Web Audio API.
// Tổng ~1.2s, fade out mượt để không chói tai.
export function playChime(): void {
  try {
    const Ctx = window.AudioContext || (window as any).webkitAudioContext
    if (!Ctx) return
    const ctx: AudioContext = new Ctx()

    const playNote = (freq: number, startOffset: number, duration: number) => {
      const osc = ctx.createOscillator()
      const gain = ctx.createGain()
      osc.type = 'sine'
      osc.frequency.value = freq
      osc.connect(gain)
      gain.connect(ctx.destination)
      const t = ctx.currentTime + startOffset
      gain.gain.setValueAtTime(0.0001, t)
      gain.gain.exponentialRampToValueAtTime(0.25, t + 0.02)
      gain.gain.exponentialRampToValueAtTime(0.0001, t + duration)
      osc.start(t)
      osc.stop(t + duration)
    }

    playNote(1046.5, 0, 0.5)   // C6
    playNote(1568.0, 0.18, 0.7) // G6
  } catch {
    // im lặng — không để lỗi audio làm crash app
  }
}

interface NotifyOptions {
  title: string
  body: string
  onClick?: () => void
}

export function fireBrowserNotification({ title, body, onClick }: NotifyOptions): void {
  if (typeof Notification === 'undefined' || Notification.permission !== 'granted') return
  try {
    const notif = new Notification(title, {
      body,
      icon: '/vite.svg',
      tag: 'session-complete',
    })
    if (onClick) {
      notif.onclick = () => {
        window.focus()
        onClick()
        notif.close()
      }
    }
  } catch {
    // im lặng
  }
}

// Convenience: làm cả 2 (notif + chime) cùng lúc khi phiên kết thúc.
export function notifySessionComplete(opts: NotifyOptions): void {
  playChime()
  fireBrowserNotification(opts)
}

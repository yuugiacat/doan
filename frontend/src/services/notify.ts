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

// Giai điệu chúc mừng — arpeggio C major thăng dần + chord climax cuối.
// Tổng ~2s, kiểu "ding ding ding ding DIIING" như chuông hoàn thành nhiệm vụ.
// Dùng sóng triangle thay sine cho âm sắc tươi tắn hơn (giống synth game cũ).
export function playChime(): void {
  try {
    const Ctx = window.AudioContext || (window as any).webkitAudioContext
    if (!Ctx) return
    const ctx: AudioContext = new Ctx()

    const playNote = (
      freq: number,
      startOffset: number,
      duration: number,
      volume = 0.25,
    ) => {
      const osc = ctx.createOscillator()
      const gain = ctx.createGain()
      osc.type = 'triangle'
      osc.frequency.value = freq
      osc.connect(gain)
      gain.connect(ctx.destination)
      const t = ctx.currentTime + startOffset
      gain.gain.setValueAtTime(0.0001, t)
      gain.gain.exponentialRampToValueAtTime(volume, t + 0.02)
      gain.gain.exponentialRampToValueAtTime(0.0001, t + duration)
      osc.start(t)
      osc.stop(t + duration)
    }

    // Phần 1: 4 nốt arpeggio C major thăng dần (ding ding ding ding)
    playNote(523.25,  0.00, 0.22)  // C5
    playNote(659.25,  0.14, 0.22)  // E5
    playNote(783.99,  0.28, 0.22)  // G5
    playNote(1046.50, 0.42, 0.28)  // C6
    // Phần 2: 1 nhịp nghỉ ngắn rồi 3 nốt chord cao chồng nhau làm climax (DIIING)
    playNote(1046.50, 0.78, 1.10, 0.20)  // C6 (giữ nền)
    playNote(1318.51, 0.78, 1.10, 0.22)  // E6
    playNote(1567.98, 0.78, 1.20, 0.20)  // G6 (đỉnh hợp âm)
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

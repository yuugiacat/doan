// Định danh user ẩn danh — UUID lưu localStorage, persist giữa các session.
// Cùng máy/cùng browser = cùng anonymous_id (đủ cho phân tích đồ án).

const ANON_KEY = 'learning_analytics_anonymous_id'
const EMAIL_KEY = 'learning_analytics_email'
const NAME_KEY = 'learning_analytics_name'
const CONSENT_KEY = 'learning_analytics_consent_research'

function uuid(): string {
  // crypto.randomUUID() available trong browser modern; fallback nếu thiếu.
  if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) {
    return (crypto as any).randomUUID()
  }
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0
    const v = c === 'x' ? r : (r & 0x3) | 0x8
    return v.toString(16)
  })
}

export function getAnonymousId(): string {
  let id = localStorage.getItem(ANON_KEY)
  if (!id) {
    id = uuid()
    localStorage.setItem(ANON_KEY, id)
  }
  return id
}

export const userIdentity = {
  getAnonymousId,
  getEmail: () => localStorage.getItem(EMAIL_KEY) || '',
  setEmail: (v: string) => localStorage.setItem(EMAIL_KEY, v),
  getName: () => localStorage.getItem(NAME_KEY) || '',
  setName: (v: string) => localStorage.setItem(NAME_KEY, v),
  getConsentResearch: () => localStorage.getItem(CONSENT_KEY) === 'true',
  setConsentResearch: (v: boolean) =>
    localStorage.setItem(CONSENT_KEY, v ? 'true' : 'false'),
}

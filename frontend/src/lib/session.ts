const SESSION_KEY = 'lyubava_session_id'

function createSessionId(): string {
  return crypto.randomUUID()
}

export function getSessionId(): string {
  const existing = localStorage.getItem(SESSION_KEY)
  if (existing) {
    return existing
  }

  const id = createSessionId()
  localStorage.setItem(SESSION_KEY, id)
  return id
}

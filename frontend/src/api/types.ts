export type MessageRole = 'user' | 'assistant'

export interface ChatMessage {
  id: string
  role: MessageRole
  content: string
  created_at: string
}

export interface ChatHistory {
  session_id: string
  messages: ChatMessage[]
}

export interface SendMessageRequest {
  session_id: string
  message: string
}

export interface SendMessageResponse {
  session_id: string
  user_message: ChatMessage
  assistant_message: ChatMessage
}

export interface AdminPredictionRow {
  timestamp: string
  session_id: string
  text: string
  predicted_emotion: string
  confidence: number
  model: string
  provider: string
}

export interface AdminPredictionsResponse {
  items: AdminPredictionRow[]
}

export type RetrainState = 'idle' | 'running' | 'succeeded' | 'failed'

export interface RetrainStatusResponse {
  state: RetrainState
  started_at: string | null
  finished_at: string | null
  message: string | null
  metrics: Record<string, unknown> | null
}

export type DriftStatus =
  | 'ok'
  | 'warn'
  | 'critical'
  | 'insufficient_data'
  | 'unavailable'

export interface DriftSectionSnapshot {
  score: number | null
  status: DriftStatus
}

export interface DriftSnapshotResponse {
  service_status: DriftStatus
  window_size: number
  min_samples: number
  sample_count: number
  drift: {
    data: DriftSectionSnapshot
    concept: DriftSectionSnapshot
    target: DriftSectionSnapshot
  }
  last_update: string | null
}

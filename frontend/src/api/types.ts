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

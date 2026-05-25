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
  session_id?: string
  content: string
}

export interface SendMessageResponse {
  session_id: string
  user_message: ChatMessage
  assistant_message: ChatMessage
}

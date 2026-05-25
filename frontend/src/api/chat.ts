import { API_V1_PREFIX, apiClient } from '@/api/client'
import type {
  ChatHistory,
  ChatMessage,
  SendMessageRequest,
  SendMessageResponse,
} from '@/api/types'

const useMock = import.meta.env.VITE_CHAT_MOCK !== 'false'

const mockStore = new Map<string, ChatMessage[]>()

function delay(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

function getMockMessages(sessionId: string): ChatMessage[] {
  if (!mockStore.has(sessionId)) {
    mockStore.set(sessionId, [
      {
        id: 'welcome',
        role: 'assistant',
        content: 'Привет! Я Lyubava. Как ты сегодня?',
        created_at: new Date().toISOString(),
      },
    ])
  }
  return mockStore.get(sessionId) ?? []
}

async function getMessagesMock(sessionId: string): Promise<ChatHistory> {
  await delay(300)
  return {
    session_id: sessionId,
    messages: getMockMessages(sessionId),
  }
}

async function sendMessageMock(
  payload: SendMessageRequest,
): Promise<SendMessageResponse> {
  await delay(500)

  const sessionId = payload.session_id
  const messages = getMockMessages(sessionId)

  const userMessage: ChatMessage = {
    id: crypto.randomUUID(),
    role: 'user',
    content: payload.message,
    created_at: new Date().toISOString(),
  }

  const assistantMessage: ChatMessage = {
    id: crypto.randomUUID(),
    role: 'assistant',
    content: 'Спасибо за сообщение. Я скоро смогу отвечать по-настоящему.',
    created_at: new Date().toISOString(),
  }

  messages.push(userMessage, assistantMessage)
  mockStore.set(sessionId, messages)

  return {
    session_id: sessionId,
    user_message: userMessage,
    assistant_message: assistantMessage,
  }
}

export async function getMessages(sessionId: string): Promise<ChatHistory> {
  if (useMock) {
    return getMessagesMock(sessionId)
  }

  const { data } = await apiClient.get<ChatHistory>(
    `${API_V1_PREFIX}/chat/messages`,
    {
    params: { session_id: sessionId },
    },
  )
  return data
}

export async function sendMessage(
  payload: SendMessageRequest,
): Promise<SendMessageResponse> {
  if (useMock) {
    return sendMessageMock(payload)
  }

  const { data } = await apiClient.post<{
    reply: string
  }>(`${API_V1_PREFIX}/chat`, {
    session_id: payload.session_id,
    message: payload.message,
  })

  const now = new Date().toISOString()
  return {
    session_id: payload.session_id,
    user_message: {
      id: crypto.randomUUID(),
      role: 'user',
      content: payload.message,
      created_at: now,
    },
    assistant_message: {
      id: crypto.randomUUID(),
      role: 'assistant',
      content: data.reply,
      created_at: now,
    },
  }
}

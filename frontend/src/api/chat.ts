import { API_V1_PREFIX, apiClient } from "@/api/client";
import type {
  ChatHistory,
  SendMessageRequest,
  SendMessageResponse,
} from "@/api/types";

export async function getMessages(sessionId: string): Promise<ChatHistory> {
  const { data } = await apiClient.get<ChatHistory>(
    `${API_V1_PREFIX}/chat/messages`,
    {
      params: { session_id: sessionId },
    },
  );
  return data;
}

export async function sendMessage(
  payload: SendMessageRequest,
): Promise<SendMessageResponse> {
  const { data } = await apiClient.post<{
    reply: string;
  }>(`${API_V1_PREFIX}/chat`, {
    session_id: payload.session_id,
    message: payload.message,
  });

  const now = new Date().toISOString();
  return {
    session_id: payload.session_id,
    user_message: {
      id: crypto.randomUUID(),
      role: "user",
      content: payload.message,
      created_at: now,
    },
    assistant_message: {
      id: crypto.randomUUID(),
      role: "assistant",
      content: data.reply,
      created_at: now,
    },
  };
}

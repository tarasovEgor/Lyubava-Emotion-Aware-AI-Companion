import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { getMessages, sendMessage } from '@/api/chat'
import type { ChatHistory } from '@/api/types'
import { getSessionId } from '@/lib/session'

export function chatQueryKey(sessionId: string) {
  return ['chat', 'messages', sessionId] as const
}

export function useChat() {
  const sessionId = getSessionId()
  const queryClient = useQueryClient()

  const historyQuery = useQuery({
    queryKey: chatQueryKey(sessionId),
    queryFn: () => getMessages(sessionId),
  })

  const sendMutation = useMutation({
    mutationFn: (content: string) =>
      sendMessage({ session_id: sessionId, content }),
    onSuccess: (response) => {
      queryClient.setQueryData<ChatHistory>(
        chatQueryKey(sessionId),
        (current) => ({
          session_id: response.session_id,
          messages: [
            ...(current?.messages ?? []),
            response.user_message,
            response.assistant_message,
          ],
        }),
      )
    },
  })

  return {
    sessionId,
    messages: historyQuery.data?.messages ?? [],
    isLoading: historyQuery.isLoading,
    isError: historyQuery.isError,
    error: historyQuery.error,
    sendMessage: sendMutation.mutate,
    isSending: sendMutation.isPending,
    sendError: sendMutation.error,
  }
}

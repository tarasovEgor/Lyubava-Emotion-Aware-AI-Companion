import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { getMessages, sendMessage } from '@/api/chat'
import type { ChatHistory, ChatMessage } from '@/api/types'
import { getSessionId } from '@/lib/session'

export function chatQueryKey(sessionId: string) {
  return ['chat', 'messages', sessionId] as const
}

function isPendingMessage(message: ChatMessage) {
  return message.id.startsWith('pending-')
}

export function useChat() {
  const sessionId = getSessionId()
  const queryClient = useQueryClient()

  const historyQuery = useQuery({
    queryKey: chatQueryKey(sessionId),
    queryFn: () => getMessages(sessionId),
  })

  const sendMutation = useMutation({
    mutationFn: (message: string) =>
      sendMessage({ session_id: sessionId, message }),
    onMutate: async (message) => {
      await queryClient.cancelQueries({ queryKey: chatQueryKey(sessionId) })

      const previous = queryClient.getQueryData<ChatHistory>(
        chatQueryKey(sessionId),
      )

      const optimisticMessage: ChatMessage = {
        id: `pending-${crypto.randomUUID()}`,
        role: 'user',
        content: message,
        created_at: new Date().toISOString(),
      }

      queryClient.setQueryData<ChatHistory>(chatQueryKey(sessionId), (current) => ({
        session_id: sessionId,
        messages: [...(current?.messages ?? []), optimisticMessage],
      }))

      return { previous }
    },
    onSuccess: (response) => {
      queryClient.setQueryData<ChatHistory>(
        chatQueryKey(sessionId),
        (current) => {
          const messages = (current?.messages ?? []).filter(
            (message) => !isPendingMessage(message),
          )

          return {
            session_id: response.session_id,
            messages: [
              ...messages,
              response.user_message,
              response.assistant_message,
            ],
          }
        },
      )
    },
    onError: (_error, _message, context) => {
      if (context?.previous) {
        queryClient.setQueryData(chatQueryKey(sessionId), context.previous)
      }
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

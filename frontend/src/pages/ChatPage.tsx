import { ChatInput } from '@/components/chat/ChatInput'
import { MessageList } from '@/components/chat/MessageList'
import { useChat } from '@/hooks/use-chat'

export function ChatPage() {
  const {
    messages,
    isLoading,
    isError,
    sendMessage,
    isSending,
    sendError,
  } = useChat()

  return (
    <div className="flex h-full flex-col">
      <header className="border-b border-neutral-200 px-4 py-3">
        <h1 className="text-lg font-semibold">Lyubava</h1>
      </header>

      {isError && (
        <p className="px-4 py-2 text-sm text-red-600">
          Не удалось загрузить историю чата.
        </p>
      )}

      {sendError && (
        <p className="px-4 py-2 text-sm text-red-600">
          Не удалось отправить сообщение.
        </p>
      )}

      <MessageList
        messages={messages}
        isLoading={isLoading}
        isSending={isSending}
      />

      <ChatInput onSend={sendMessage} disabled={isSending || isLoading} />
    </div>
  )
}

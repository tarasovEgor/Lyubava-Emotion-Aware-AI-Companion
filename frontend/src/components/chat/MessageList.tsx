import { useEffect, useRef } from 'react'

import type { ChatMessage } from '@/api/types'
import { ChatLoader } from '@/components/chat/ChatLoader'
import { MessageBubble } from '@/components/chat/MessageBubble'
import { ScrollArea } from '@/components/ui/scroll-area'

interface MessageListProps {
  messages: ChatMessage[]
  isLoading?: boolean
  isSending?: boolean
}

export function MessageList({ messages, isLoading, isSending }: MessageListProps) {
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isLoading, isSending])

  if (isLoading) {
    return (
      <div className="flex flex-1 items-center justify-center text-sm text-neutral-500">
        Загрузка...
      </div>
    )
  }

  return (
    <ScrollArea className="flex-1">
      <div className="flex flex-col gap-3 p-4">
        {messages.map((message) => (
          <MessageBubble key={message.id} message={message} />
        ))}
        {isSending && <ChatLoader />}
        <div ref={bottomRef} />
      </div>
    </ScrollArea>
  )
}

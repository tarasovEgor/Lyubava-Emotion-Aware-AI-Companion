import { useState, type FormEvent } from 'react'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'

interface ChatInputProps {
  onSend: (content: string) => void
  disabled?: boolean
}

export function ChatInput({ onSend, disabled }: ChatInputProps) {
  const [text, setText] = useState('')

  function handleSubmit(event: FormEvent) {
    event.preventDefault()
    const trimmed = text.trim()
    if (!trimmed || disabled) {
      return
    }

    onSend(trimmed)
    setText('')
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="flex gap-2 border-t border-neutral-200 p-4"
    >
      <Input
        value={text}
        onChange={(event) => setText(event.target.value)}
        placeholder="Напишите сообщение..."
        disabled={disabled}
        autoComplete="off"
      />
      <Button type="submit" disabled={disabled || !text.trim()}>
        Отправить
      </Button>
    </form>
  )
}

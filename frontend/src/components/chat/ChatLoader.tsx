import { Loader2 } from 'lucide-react'

export function ChatLoader() {
  return (
    <div className="flex justify-start">
      <div className="flex items-center gap-2 rounded-lg bg-neutral-100 px-3 py-2 text-sm text-neutral-600">
        <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
        <span>Lyubava печатает...</span>
      </div>
    </div>
  )
}

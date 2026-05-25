import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

export function AdminPage() {
  return (
    <div className="mx-auto max-w-lg p-6">
      <h1 className="mb-6 text-lg font-semibold">Админ</h1>

      <Card>
        <CardHeader>
          <CardTitle>Метрики</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-sm text-neutral-600">
          <p>accuracy: —</p>
          <p>last train: —</p>
        </CardContent>
      </Card>

      <Button className="mt-4" disabled>
        Переобучить
      </Button>
      <p className="mt-2 text-xs text-neutral-500">
        Будет подключено к API позже.
      </p>
    </div>
  )
}

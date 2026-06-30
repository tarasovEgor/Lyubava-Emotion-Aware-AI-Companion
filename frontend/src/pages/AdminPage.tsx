import { useEffect, useMemo, useState } from 'react'

import {
  getAdminPredictions,
  getDriftSnapshot,
  getRetrainStatus,
  startRetrain,
} from '@/api/admin'
import type {
  AdminPredictionRow,
  DriftSnapshotResponse,
  RetrainStatusResponse,
} from '@/api/types'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

const DEFAULT_LIMIT = 50
const TEXT_PREVIEW_MAX_LENGTH = 80
const DRIFT_POLL_INTERVAL_MS = 30_000
const RETRAIN_POLL_INTERVAL_MS = 5_000

function formatTimestamp(isoValue: string): string {
  const date = new Date(isoValue)
  if (Number.isNaN(date.getTime())) {
    return isoValue
  }
  return date.toLocaleString()
}

function formatConfidence(value: number): string {
  return `${(value * 100).toFixed(1)}%`
}

function shortenText(text: string): string {
  if (text.length <= TEXT_PREVIEW_MAX_LENGTH) {
    return text
  }
  return `${text.slice(0, TEXT_PREVIEW_MAX_LENGTH)}...`
}

export function AdminPage() {
  const [predictions, setPredictions] = useState<AdminPredictionRow[]>([])
  const [isLoadingPredictions, setIsLoadingPredictions] = useState(true)
  const [predictionsError, setPredictionsError] = useState<string | null>(null)
  const [driftSnapshot, setDriftSnapshot] = useState<DriftSnapshotResponse | null>(
    null,
  )
  const [retrainStatus, setRetrainStatus] = useState<RetrainStatusResponse | null>(
    null,
  )
  const [isStartingRetrain, setIsStartingRetrain] = useState(false)

  useEffect(() => {
    let isCancelled = false

    const loadPredictions = async () => {
      setIsLoadingPredictions(true)
      setPredictionsError(null)
      try {
        const response = await getAdminPredictions(DEFAULT_LIMIT)
        if (!isCancelled) {
          setPredictions(response.items)
        }
      } catch (error) {
        console.error('Failed to load admin predictions', error)
        if (!isCancelled) {
          setPredictionsError('Не удалось загрузить предсказания.')
        }
      } finally {
        if (!isCancelled) {
          setIsLoadingPredictions(false)
        }
      }
    }

    void loadPredictions()

    return () => {
      isCancelled = true
    }
  }, [])

  useEffect(() => {
    let isCancelled = false
    let intervalId: number | null = null

    const loadRetrainStatus = async () => {
      try {
        const status = await getRetrainStatus()
        if (!isCancelled) {
          setRetrainStatus(status)
          if (status.state === 'running' && intervalId === null) {
            intervalId = window.setInterval(() => {
              void loadRetrainStatus()
            }, RETRAIN_POLL_INTERVAL_MS)
          }
          if (status.state !== 'running' && intervalId !== null) {
            window.clearInterval(intervalId)
            intervalId = null
          }
        }
      } catch (error) {
        console.error('Failed to load retrain status', error)
      }
    }

    void loadRetrainStatus()

    return () => {
      isCancelled = true
      if (intervalId !== null) {
        window.clearInterval(intervalId)
      }
    }
  }, [])

  useEffect(() => {
    let isCancelled = false

    const loadDriftSnapshot = async () => {
      try {
        const response = await getDriftSnapshot()
        if (!isCancelled) {
          setDriftSnapshot(response)
        }
      } catch (error) {
        console.error('Failed to load drift snapshot', error)
      }
    }

    void loadDriftSnapshot()
    const intervalId = window.setInterval(() => {
      void loadDriftSnapshot()
    }, DRIFT_POLL_INTERVAL_MS)

    return () => {
      isCancelled = true
      window.clearInterval(intervalId)
    }
  }, [])

  const dataDriftSection = driftSnapshot?.drift.data
  const shouldShowDataDriftAlert =
    dataDriftSection?.status === 'warn' || dataDriftSection?.status === 'critical'
  const dataDriftAlertClasses =
    dataDriftSection?.status === 'critical'
      ? 'border-red-300 bg-red-50 text-red-800'
      : 'border-amber-300 bg-amber-50 text-amber-800'
  const dataDriftAlertTitle =
    dataDriftSection?.status === 'critical'
      ? 'Критический data drift'
      : 'Предупреждение: data drift'
  const targetDriftSection = driftSnapshot?.drift.target
  const shouldShowTargetDriftAlert =
    targetDriftSection?.status === 'warn' ||
    targetDriftSection?.status === 'critical'
  const targetDriftAlertClasses =
    targetDriftSection?.status === 'critical'
      ? 'border-red-300 bg-red-50 text-red-800'
      : 'border-amber-300 bg-amber-50 text-amber-800'
  const targetDriftAlertTitle =
    targetDriftSection?.status === 'critical'
      ? 'Критический target drift'
      : 'Предупреждение: target drift'

  const predictionsContent = useMemo(() => {
    if (isLoadingPredictions) {
      return <p className="text-sm text-neutral-600">Загрузка предсказаний...</p>
    }
    if (predictionsError) {
      return <p className="text-sm text-red-600">{predictionsError}</p>
    }
    if (predictions.length === 0) {
      return <p className="text-sm text-neutral-600">Пока нет предсказаний.</p>
    }

    return (
      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs">
          <thead className="border-b text-neutral-500">
            <tr>
              <th className="px-2 py-2 font-medium">Время</th>
              <th className="px-2 py-2 font-medium">Session</th>
              <th className="px-2 py-2 font-medium">Текст</th>
              <th className="px-2 py-2 font-medium">Эмоция</th>
              <th className="px-2 py-2 font-medium">Confidence</th>
              <th className="px-2 py-2 font-medium">Model</th>
              <th className="px-2 py-2 font-medium">Provider</th>
            </tr>
          </thead>
          <tbody>
            {predictions.map((row) => (
              <tr key={`${row.timestamp}-${row.session_id}`} className="border-b">
                <td className="px-2 py-2 whitespace-nowrap">
                  {formatTimestamp(row.timestamp)}
                </td>
                <td className="px-2 py-2 whitespace-nowrap">{row.session_id}</td>
                <td className="max-w-xs px-2 py-2" title={row.text}>
                  {shortenText(row.text)}
                </td>
                <td className="px-2 py-2 whitespace-nowrap">
                  {row.predicted_emotion}
                </td>
                <td className="px-2 py-2 whitespace-nowrap">
                  {formatConfidence(row.confidence)}
                </td>
                <td className="px-2 py-2 whitespace-nowrap">{row.model}</td>
                <td className="px-2 py-2 whitespace-nowrap">{row.provider}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    )
  }, [isLoadingPredictions, predictionsError, predictions])

  const handleStartRetrain = async () => {
    setIsStartingRetrain(true)
    try {
      const status = await startRetrain()
      setRetrainStatus(status)
    } catch (error) {
      console.error('Failed to start retrain', error)
      setRetrainStatus({
        state: 'failed',
        started_at: null,
        finished_at: null,
        message: 'Не удалось запустить переобучение.',
        metrics: null,
      })
    } finally {
      setIsStartingRetrain(false)
    }
  }

  const retrainStateLabel = (() => {
    if (!retrainStatus) return 'Статус неизвестен'
    if (retrainStatus.state === 'running') return 'Выполняется'
    if (retrainStatus.state === 'succeeded') return 'Успешно завершено'
    if (retrainStatus.state === 'failed') return 'Ошибка'
    return 'Ожидание запуска'
  })()

  const lastTrainTimestamp =
    retrainStatus?.finished_at ?? retrainStatus?.started_at ?? null
  const lastTrainLabel = lastTrainTimestamp ? formatTimestamp(lastTrainTimestamp) : '—'

  return (
    <div className="mx-auto max-w-6xl p-6">
      <h1 className="mb-6 text-lg font-semibold">Админ</h1>

      {shouldShowDataDriftAlert && dataDriftSection && (
        <div className={`mb-4 rounded-md border px-4 py-3 text-sm ${dataDriftAlertClasses}`}>
          <p className="font-medium">{dataDriftAlertTitle}</p>
          <p className="mt-1">
            score: {dataDriftSection.score?.toFixed(3) ?? '—'}.
            {' '}Проверьте входящий поток данных и baseline.
          </p>
        </div>
      )}
      {shouldShowTargetDriftAlert && targetDriftSection && (
        <div className={`mb-4 rounded-md border px-4 py-3 text-sm ${targetDriftAlertClasses}`}>
          <p className="font-medium">{targetDriftAlertTitle}</p>
          <p className="mt-1">
            score: {targetDriftSection.score?.toFixed(3) ?? '—'}.
            {' '}Проверьте сдвиг распределения эмоций в проде.
          </p>
        </div>
      )}

      <Card>
        <CardHeader>
          <CardTitle>Метрики</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-sm text-neutral-600">
          <p>last train: {lastTrainLabel}</p>
        </CardContent>
      </Card>

      <Button
        className="mt-4"
        disabled={isStartingRetrain || retrainStatus?.state === 'running'}
        onClick={() => {
          void handleStartRetrain()
        }}
      >
        Переобучить
      </Button>
      <p className="mt-2 text-xs text-neutral-500">Статус: {retrainStateLabel}</p>
      {retrainStatus?.message && (
        <p className="mt-1 text-xs text-neutral-500">{retrainStatus.message}</p>
      )}

      <Card className="mt-6">
        <CardHeader>
          <CardTitle>Прод-предсказания</CardTitle>
        </CardHeader>
        <CardContent>{predictionsContent}</CardContent>
      </Card>
    </div>
  )
}

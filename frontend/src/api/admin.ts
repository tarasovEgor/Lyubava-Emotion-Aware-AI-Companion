import { API_V1_PREFIX, apiClient } from '@/api/client'
import type {
  AdminPredictionsResponse,
  DriftSnapshotResponse,
  RetrainStatusResponse,
} from '@/api/types'

export interface AdminMetrics {
  accuracy: number | null
  last_train: string | null
}

// TODO: wire when backend endpoints are ready
export async function getAdminMetrics(): Promise<AdminMetrics> {
  const { data } = await apiClient.get<AdminMetrics>(
    `${API_V1_PREFIX}/admin/metrics`,
  )
  return data
}

export async function startRetrain(): Promise<RetrainStatusResponse> {
  const { data } = await apiClient.post<RetrainStatusResponse>(
    `${API_V1_PREFIX}/admin/retrain`,
  )
  return data
}

export async function getRetrainStatus(): Promise<RetrainStatusResponse> {
  const { data } = await apiClient.get<RetrainStatusResponse>(
    `${API_V1_PREFIX}/admin/retrain`,
  )
  return data
}

export async function getAdminPredictions(
  limit = 50,
): Promise<AdminPredictionsResponse> {
  const { data } = await apiClient.get<AdminPredictionsResponse>(
    `${API_V1_PREFIX}/admin/predictions`,
    {
      params: { limit },
    },
  )
  return data
}

export async function getDriftSnapshot(): Promise<DriftSnapshotResponse> {
  const { data } = await apiClient.get<DriftSnapshotResponse>(
    `${API_V1_PREFIX}/monitoring/drift`,
  )
  return data
}

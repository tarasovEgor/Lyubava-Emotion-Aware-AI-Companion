import { apiClient } from '@/api/client'

export interface AdminMetrics {
  accuracy: number | null
  last_train: string | null
}

// TODO: wire when backend endpoints are ready
export async function getAdminMetrics(): Promise<AdminMetrics> {
  const { data } = await apiClient.get<AdminMetrics>('/admin/metrics')
  return data
}

export async function startRetrain(): Promise<void> {
  await apiClient.post('/admin/retrain')
}

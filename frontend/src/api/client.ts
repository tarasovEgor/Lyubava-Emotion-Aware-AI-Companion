import axios from 'axios'

export const API_V1_PREFIX = '/v1'

export const apiClient = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
})

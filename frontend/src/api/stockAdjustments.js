import apiClient from './client'

export async function listAdjustments(params = {}) {
  const { data } = await apiClient.get('/stock-adjustments', { params })
  return data
}

export async function getAdjustment(id) {
  const { data } = await apiClient.get(`/stock-adjustments/${id}`)
  return data
}

export async function createAdjustment(payload) {
  const { data } = await apiClient.post('/stock-adjustments', payload)
  return data
}

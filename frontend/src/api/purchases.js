import apiClient from './client'

export async function listPurchases(params = {}) {
  const { data } = await apiClient.get('/purchase-orders', { params })
  return data
}

export async function getPurchase(id) {
  const { data } = await apiClient.get(`/purchase-orders/${id}`)
  return data
}

export async function createPurchase(payload) {
  const { data } = await apiClient.post('/purchase-orders', payload)
  return data
}

export async function updatePurchase(id, payload) {
  const { data } = await apiClient.patch(`/purchase-orders/${id}`, payload)
  return data
}

export async function cancelPurchase(id) {
  const { data } = await apiClient.post(`/purchase-orders/${id}/cancel`)
  return data
}

export async function receivePurchase(id) {
  const { data } = await apiClient.post(`/purchase-orders/${id}/receive`)
  return data
}

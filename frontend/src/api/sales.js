import apiClient from './client'

export async function listSales(params = {}) {
  const { data } = await apiClient.get('/sales-orders', { params })
  return data
}

export async function getSale(id) {
  const { data } = await apiClient.get(`/sales-orders/${id}`)
  return data
}

export async function createSale(payload) {
  const { data } = await apiClient.post('/sales-orders', payload)
  return data
}

export async function updateSale(id, payload) {
  const { data } = await apiClient.patch(`/sales-orders/${id}`, payload)
  return data
}

export async function cancelSale(id) {
  const { data } = await apiClient.post(`/sales-orders/${id}/cancel`)
  return data
}

export async function confirmSale(id) {
  const { data } = await apiClient.post(`/sales-orders/${id}/confirm`)
  return data
}

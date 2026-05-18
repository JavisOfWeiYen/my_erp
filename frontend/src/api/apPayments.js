import apiClient from './client'

export async function listForPayable(apId) {
  const { data } = await apiClient.get('/ap-payments', {
    params: { accounts_payable_id: apId },
  })
  return data
}

export async function createPayment(payload) {
  const { data } = await apiClient.post('/ap-payments', payload)
  return data
}

export async function voidPayment(id, reason) {
  const { data } = await apiClient.post(`/ap-payments/${id}/void`, { reason })
  return data
}

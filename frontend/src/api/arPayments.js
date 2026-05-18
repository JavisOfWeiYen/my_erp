import apiClient from './client'

export async function listForReceivable(arId) {
  const { data } = await apiClient.get('/ar-payments', {
    params: { accounts_receivable_id: arId },
  })
  return data
}

export async function createPayment(payload) {
  const { data } = await apiClient.post('/ar-payments', payload)
  return data
}

export async function voidPayment(id, reason) {
  const { data } = await apiClient.post(`/ar-payments/${id}/void`, { reason })
  return data
}

import apiClient from './client'

export async function listReceivables(params = {}) {
  const { data } = await apiClient.get('/accounts-receivable', { params })
  return data
}

export async function getReceivable(id) {
  const { data } = await apiClient.get(`/accounts-receivable/${id}`)
  return data
}

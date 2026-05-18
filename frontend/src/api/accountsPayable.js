import apiClient from './client'

export async function listPayables(params = {}) {
  const { data } = await apiClient.get('/accounts-payable', { params })
  return data
}

export async function getPayable(id) {
  const { data } = await apiClient.get(`/accounts-payable/${id}`)
  return data
}

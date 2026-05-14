import apiClient from './client'

export async function listSuppliers(params = {}) {
  const { data } = await apiClient.get('/suppliers', { params })
  return data
}

export async function getSupplier(id) {
  const { data } = await apiClient.get(`/suppliers/${id}`)
  return data
}

export async function createSupplier(payload) {
  const { data } = await apiClient.post('/suppliers', payload)
  return data
}

export async function updateSupplier(id, payload) {
  const { data } = await apiClient.patch(`/suppliers/${id}`, payload)
  return data
}

export async function deleteSupplier(id) {
  await apiClient.delete(`/suppliers/${id}`)
}

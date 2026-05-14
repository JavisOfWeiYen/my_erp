import apiClient from './client'

export async function listProducts(params = {}) {
  const { data } = await apiClient.get('/products', { params })
  return data
}

export async function createProduct(payload) {
  const { data } = await apiClient.post('/products', payload)
  return data
}

export async function updateProduct(id, payload) {
  const { data } = await apiClient.patch(`/products/${id}`, payload)
  return data
}

export async function deleteProduct(id) {
  await apiClient.delete(`/products/${id}`)
}

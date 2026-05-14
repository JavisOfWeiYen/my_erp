import apiClient from './client'

export async function listCategories() {
  const { data } = await apiClient.get('/categories')
  return data
}

export async function createCategory(payload) {
  const { data } = await apiClient.post('/categories', payload)
  return data
}

export async function updateCategory(id, payload) {
  const { data } = await apiClient.patch(`/categories/${id}`, payload)
  return data
}

export async function deleteCategory(id) {
  await apiClient.delete(`/categories/${id}`)
}

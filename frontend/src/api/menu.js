import apiClient from './client'

export async function getMenu() {
  const { data } = await apiClient.get('/menu')
  return data
}

export async function getAdminMenu() {
  const { data } = await apiClient.get('/admin/menu')
  return data
}

export async function createMenuItem(payload) {
  const { data } = await apiClient.post('/admin/menu', payload)
  return data
}

export async function updateMenuItem(id, payload) {
  const { data } = await apiClient.patch(`/admin/menu/${id}`, payload)
  return data
}

export async function deleteMenuItem(id) {
  await apiClient.delete(`/admin/menu/${id}`)
}

export async function reorderMenu(entries) {
  await apiClient.post('/admin/menu/reorder', entries)
}

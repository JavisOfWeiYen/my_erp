import apiClient from './client'

export async function listUsers(params = {}) {
  const { data } = await apiClient.get('/users', { params })
  return data
}

export async function listStaff(params = {}) {
  const { data } = await apiClient.get('/users/staff', { params })
  return data
}

export async function createUser(payload) {
  const { data } = await apiClient.post('/users', payload)
  return data
}

export async function updateUser(id, payload) {
  const { data } = await apiClient.patch(`/users/${id}`, payload)
  return data
}

export async function deleteUser(id) {
  await apiClient.delete(`/users/${id}`)
}

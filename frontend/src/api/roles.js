import apiClient from './client'

export async function listRoles() {
  const { data } = await apiClient.get('/roles')
  return data
}

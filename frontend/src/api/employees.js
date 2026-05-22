import apiClient from './client'

export async function listEmployees(params = {}) {
  const { data } = await apiClient.get('/employees', { params })
  return data
}

export async function getEmployee(id) {
  const { data } = await apiClient.get(`/employees/${id}`)
  return data
}

export async function createEmployee(payload) {
  const { data } = await apiClient.post('/employees', payload)
  return data
}

export async function updateEmployee(id, payload) {
  const { data } = await apiClient.patch(`/employees/${id}`, payload)
  return data
}

export async function deleteEmployee(id) {
  await apiClient.delete(`/employees/${id}`)
}

export async function listSalaryRecords(employeeId) {
  const { data } = await apiClient.get(`/employees/${employeeId}/salary-records`)
  return data
}

export async function addSalaryRecord(employeeId, payload) {
  const { data } = await apiClient.post(
    `/employees/${employeeId}/salary-records`,
    payload,
  )
  return data
}

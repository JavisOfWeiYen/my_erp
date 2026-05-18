import apiClient from './client'

export async function arAging(asOf) {
  const params = asOf ? { as_of: asOf } : {}
  const { data } = await apiClient.get('/accounts-receivable/aging', { params })
  return data
}

export async function apAging(asOf) {
  const params = asOf ? { as_of: asOf } : {}
  const { data } = await apiClient.get('/accounts-payable/aging', { params })
  return data
}

import apiClient from './client'

export async function getMarginByProduct(params = {}) {
  const { data } = await apiClient.get('/analytics/margin/by-product', { params })
  return data
}

export async function getMarginByCustomer(params = {}) {
  const { data } = await apiClient.get('/analytics/margin/by-customer', { params })
  return data
}

export async function getMarginTrend(months = 12) {
  const { data } = await apiClient.get('/analytics/margin/trend', {
    params: { months },
  })
  return data
}

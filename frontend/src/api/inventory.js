import apiClient from './client'

export async function listStock(params = {}) {
  const { data } = await apiClient.get('/inventory/stock', { params })
  return data
}

export async function getMonthlyReport(year, month) {
  const { data } = await apiClient.get('/inventory/monthly-report', {
    params: { year, month },
  })
  return data
}

export async function downloadMonthlyReportXlsx(year, month) {
  const response = await apiClient.get('/inventory/monthly-report.xlsx', {
    params: { year, month },
    responseType: 'blob',
  })
  return response.data
}

export async function getSalespersonReport(year, month) {
  const { data } = await apiClient.get('/inventory/salesperson-report', {
    params: { year, month },
  })
  return data
}

export async function downloadSalespersonReportXlsx(year, month) {
  const response = await apiClient.get('/inventory/salesperson-report.xlsx', {
    params: { year, month },
    responseType: 'blob',
  })
  return response.data
}

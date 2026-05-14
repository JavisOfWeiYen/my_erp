import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import {
  Alert,
  Box,
  Button,
  CircularProgress,
  FormControl,
  InputLabel,
  MenuItem,
  Paper,
  Select,
  Stack,
  Tab,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Tabs,
  Typography,
} from '@mui/material'
import DownloadIcon from '@mui/icons-material/Download'

import * as inventoryApi from '@/api/inventory'

const MONTHS = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]

function defaultYear() {
  return new Date().getFullYear()
}

function defaultMonth() {
  return new Date().getMonth() + 1
}

function yearOptions() {
  const current = defaultYear()
  return [current - 1, current, current + 1]
}

function triggerDownload(blob, filename) {
  const url = window.URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  link.remove()
  window.URL.revokeObjectURL(url)
}

export default function ReportsPage() {
  const { t } = useTranslation()

  const [year, setYear] = useState(defaultYear())
  const [month, setMonth] = useState(defaultMonth())
  const [tab, setTab] = useState('inventory')

  const [inventoryReport, setInventoryReport] = useState(null)
  const [salespersonReport, setSalespersonReport] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [downloading, setDownloading] = useState(false)

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      setLoading(true)
      try {
        const [inv, sp] = await Promise.all([
          inventoryApi.getMonthlyReport(year, month),
          inventoryApi.getSalespersonReport(year, month),
        ])
        if (!cancelled) {
          setInventoryReport(inv)
          setSalespersonReport(sp)
          setError(null)
        }
      } catch (err) {
        if (!cancelled) setError(err.response?.data?.detail || err.message)
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [year, month])

  const handleDownload = async () => {
    setDownloading(true)
    try {
      const monthStr = String(month).padStart(2, '0')
      if (tab === 'inventory') {
        const blob = await inventoryApi.downloadMonthlyReportXlsx(year, month)
        triggerDownload(blob, `inventory-report-${year}-${monthStr}.xlsx`)
      } else {
        const blob = await inventoryApi.downloadSalespersonReportXlsx(year, month)
        triggerDownload(blob, `salesperson-report-${year}-${monthStr}.xlsx`)
      }
    } catch (err) {
      setError(err.response?.data?.detail || err.message)
    } finally {
      setDownloading(false)
    }
  }

  const totalAmountForShare = Number(salespersonReport?.total_amount || 0)

  return (
    <Box>
      <Stack direction="row" justifyContent="space-between" alignItems="center" mb={2}>
        <Typography variant="h4">{t('nav.reports')}</Typography>
        <Button
          variant="contained"
          size="small"
          startIcon={<DownloadIcon />}
          onClick={handleDownload}
          disabled={downloading || loading}
        >
          {downloading ? t('common.loading') : t('reports.exportExcel')}
        </Button>
      </Stack>

      <Paper sx={{ p: 2, mb: 2 }}>
        <Stack direction={{ xs: 'column', md: 'row' }} spacing={2} alignItems={{ md: 'center' }}>
          <FormControl size="small" sx={{ minWidth: 120 }}>
            <InputLabel>{t('reports.year')}</InputLabel>
            <Select label={t('reports.year')} value={year} onChange={(e) => setYear(Number(e.target.value))}>
              {yearOptions().map((y) => (
                <MenuItem key={y} value={y}>
                  {y}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          <FormControl size="small" sx={{ minWidth: 120 }}>
            <InputLabel>{t('reports.month')}</InputLabel>
            <Select label={t('reports.month')} value={month} onChange={(e) => setMonth(Number(e.target.value))}>
              {MONTHS.map((m) => (
                <MenuItem key={m} value={m}>
                  {m}
                </MenuItem>
              ))}
            </Select>
          </FormControl>

          {tab === 'inventory' && inventoryReport && (
            <Stack direction="row" spacing={3} alignItems="center" sx={{ ml: { md: 'auto' } }}>
              <Box>
                <Typography variant="caption" color="text.secondary">
                  {t('reports.totalPurchase')}
                </Typography>
                <Typography variant="subtitle1">{inventoryReport.total_purchase_amount}</Typography>
              </Box>
              <Box>
                <Typography variant="caption" color="text.secondary">
                  {t('reports.totalSales')}
                </Typography>
                <Typography variant="subtitle1">{inventoryReport.total_sales_amount}</Typography>
              </Box>
            </Stack>
          )}
          {tab === 'salesperson' && salespersonReport && (
            <Stack direction="row" spacing={3} alignItems="center" sx={{ ml: { md: 'auto' } }}>
              <Box>
                <Typography variant="caption" color="text.secondary">
                  {t('reports.salesperson.totalOrders')}
                </Typography>
                <Typography variant="subtitle1">{salespersonReport.total_order_count}</Typography>
              </Box>
              <Box>
                <Typography variant="caption" color="text.secondary">
                  {t('reports.salesperson.totalAmountSum')}
                </Typography>
                <Typography variant="subtitle1">{salespersonReport.total_amount}</Typography>
              </Box>
            </Stack>
          )}
        </Stack>
      </Paper>

      <Tabs
        value={tab}
        onChange={(_, v) => setTab(v)}
        sx={{ borderBottom: 1, borderColor: 'divider', mb: 2 }}
      >
        <Tab value="inventory" label={t('reports.tabInventory')} />
        <Tab value="salesperson" label={t('reports.tabSalesperson')} />
      </Tabs>

      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

      {tab === 'inventory' && (
        <TableContainer component={Paper}>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>{t('products.sku')}</TableCell>
                <TableCell>{t('products.name')}</TableCell>
                <TableCell>{t('products.category')}</TableCell>
                <TableCell align="right">{t('reports.opening')}</TableCell>
                <TableCell align="right">{t('reports.qtyIn')}</TableCell>
                <TableCell align="right">{t('reports.qtyOut')}</TableCell>
                <TableCell align="right">{t('reports.adjustment')}</TableCell>
                <TableCell align="right">{t('reports.closing')}</TableCell>
                <TableCell align="right">{t('reports.purchaseAmount')}</TableCell>
                <TableCell align="right">{t('reports.salesAmount')}</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {loading ? (
                <TableRow>
                  <TableCell colSpan={10} align="center">
                    <CircularProgress size={24} />
                  </TableCell>
                </TableRow>
              ) : !inventoryReport || inventoryReport.rows.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={10} align="center">
                    <Typography color="text.secondary">{t('common.noData')}</Typography>
                  </TableCell>
                </TableRow>
              ) : (
                inventoryReport.rows.map((row) => {
                  const adj = row.adjustment ?? 0
                  return (
                    <TableRow key={row.product_id} hover>
                      <TableCell>{row.sku}</TableCell>
                      <TableCell>{row.name}</TableCell>
                      <TableCell>{row.category_name || '—'}</TableCell>
                      <TableCell align="right">{row.opening_stock}</TableCell>
                      <TableCell align="right">{row.qty_in}</TableCell>
                      <TableCell align="right">{row.qty_out}</TableCell>
                      <TableCell align="right">
                        {adj === 0 ? (
                          <Typography component="span" color="text.secondary">—</Typography>
                        ) : (
                          <Typography
                            component="span"
                            sx={{ color: adj > 0 ? 'success.main' : 'error.main', fontWeight: 600 }}
                          >
                            {adj > 0 ? `+${adj}` : adj}
                          </Typography>
                        )}
                      </TableCell>
                      <TableCell align="right">{row.closing_stock}</TableCell>
                      <TableCell align="right">{row.purchase_amount}</TableCell>
                      <TableCell align="right">{row.sales_amount}</TableCell>
                    </TableRow>
                  )
                })
              )}
            </TableBody>
          </Table>
        </TableContainer>
      )}

      {tab === 'salesperson' && (
        <TableContainer component={Paper}>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>{t('reports.salesperson.name')}</TableCell>
                <TableCell>{t('reports.salesperson.role')}</TableCell>
                <TableCell align="right">{t('reports.salesperson.orderCount')}</TableCell>
                <TableCell align="right">{t('reports.salesperson.totalQty')}</TableCell>
                <TableCell align="right">{t('reports.salesperson.totalAmount')}</TableCell>
                <TableCell align="right">{t('reports.salesperson.share')}</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {loading ? (
                <TableRow>
                  <TableCell colSpan={6} align="center">
                    <CircularProgress size={24} />
                  </TableCell>
                </TableRow>
              ) : !salespersonReport || salespersonReport.rows.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={6} align="center">
                    <Typography color="text.secondary">{t('common.noData')}</Typography>
                  </TableCell>
                </TableRow>
              ) : (
                salespersonReport.rows.map((row) => {
                  const display = row.full_name || row.username
                  const share = totalAmountForShare > 0
                    ? (Number(row.total_amount) / totalAmountForShare) * 100
                    : 0
                  return (
                    <TableRow key={row.salesperson_id} hover>
                      <TableCell>
                        {display}
                        {row.username !== display && (
                          <Typography component="span" color="text.secondary" sx={{ ml: 1, fontSize: '0.8em' }}>
                            ({row.username})
                          </Typography>
                        )}
                      </TableCell>
                      <TableCell>
                        {row.role_name ? t(`roles.${row.role_name}`, row.role_name) : '—'}
                      </TableCell>
                      <TableCell align="right">{row.order_count}</TableCell>
                      <TableCell align="right">{row.total_qty}</TableCell>
                      <TableCell align="right">{row.total_amount}</TableCell>
                      <TableCell align="right">{share.toFixed(1)}%</TableCell>
                    </TableRow>
                  )
                })
              )}
            </TableBody>
          </Table>
        </TableContainer>
      )}
    </Box>
  )
}

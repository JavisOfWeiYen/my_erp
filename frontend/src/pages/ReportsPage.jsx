import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import {
  Alert,
  Box,
  Button,
  CircularProgress,
  FormControl,
  Grid,
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
  Tooltip,
  Typography,
} from '@mui/material'
import DownloadIcon from '@mui/icons-material/Download'

import * as inventoryApi from '@/api/inventory'
import * as analyticsApi from '@/api/analytics'

const MONTHS = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]
const MARGIN_TREND_MONTHS = 12
const MARGIN_TOP = 10

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

function formatPercent(rate) {
  // API returns Decimal as string, e.g. "0.6667"
  const num = Number(rate ?? 0)
  return `${(num * 100).toFixed(1)}%`
}

export default function ReportsPage() {
  const { t } = useTranslation()

  const [year, setYear] = useState(defaultYear())
  const [month, setMonth] = useState(defaultMonth())
  const [tab, setTab] = useState('inventory')

  const [inventoryReport, setInventoryReport] = useState(null)
  const [salespersonReport, setSalespersonReport] = useState(null)
  const [marginTrend, setMarginTrend] = useState(null)
  const [marginByProduct, setMarginByProduct] = useState(null)
  const [marginByCustomer, setMarginByCustomer] = useState(null)
  const [loading, setLoading] = useState(true)
  const [marginLoading, setMarginLoading] = useState(false)
  const [error, setError] = useState(null)
  const [downloading, setDownloading] = useState(false)

  // Inventory + salesperson share the year/month picker — refetch when those change.
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

  // Margin data fetched once when tab is first opened (no date picker dependency).
  useEffect(() => {
    if (tab !== 'margin') return
    if (marginTrend !== null) return // already loaded
    let cancelled = false
    ;(async () => {
      setMarginLoading(true)
      try {
        const [trend, byProduct, byCustomer] = await Promise.all([
          analyticsApi.getMarginTrend(MARGIN_TREND_MONTHS),
          analyticsApi.getMarginByProduct({ sort_by: 'gross_profit', top: MARGIN_TOP }),
          analyticsApi.getMarginByCustomer({ sort_by: 'gross_profit', top: MARGIN_TOP }),
        ])
        if (!cancelled) {
          setMarginTrend(trend)
          setMarginByProduct(byProduct)
          setMarginByCustomer(byCustomer)
        }
      } catch (err) {
        if (!cancelled) setError(err.response?.data?.detail || err.message)
      } finally {
        if (!cancelled) setMarginLoading(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [tab, marginTrend])

  const handleDownload = async () => {
    setDownloading(true)
    try {
      const monthStr = String(month).padStart(2, '0')
      if (tab === 'inventory') {
        const blob = await inventoryApi.downloadMonthlyReportXlsx(year, month)
        triggerDownload(blob, `inventory-report-${year}-${monthStr}.xlsx`)
      } else if (tab === 'salesperson') {
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
  const marginExportDisabled = tab === 'margin'

  return (
    <Box>
      <Stack direction="row" justifyContent="space-between" alignItems="center" mb={2}>
        <Typography variant="h4">{t('nav.reports')}</Typography>
        <Tooltip
          title={marginExportDisabled ? t('reports.exportNotAvailable') : ''}
          disableHoverListener={!marginExportDisabled}
        >
          <span>
            <Button
              variant="contained"
              size="small"
              startIcon={<DownloadIcon />}
              onClick={handleDownload}
              disabled={downloading || loading || marginExportDisabled}
            >
              {downloading ? t('common.loading') : t('reports.exportExcel')}
            </Button>
          </span>
        </Tooltip>
      </Stack>

      <Paper sx={{ p: 2, mb: 2 }}>
        {tab === 'margin' ? (
          <Typography variant="body2" color="text.secondary">
            {t('reports.margin.scopeHint')}
          </Typography>
        ) : (
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
        )}
      </Paper>

      <Tabs
        value={tab}
        onChange={(_, v) => setTab(v)}
        sx={{ borderBottom: 1, borderColor: 'divider', mb: 2 }}
      >
        <Tab value="inventory" label={t('reports.tabInventory')} />
        <Tab value="salesperson" label={t('reports.tabSalesperson')} />
        <Tab value="margin" label={t('reports.tabMargin')} />
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

      {tab === 'margin' && (
        <Stack spacing={2}>
          {marginByProduct && (
            <Paper sx={{ p: 2 }}>
              <Typography variant="overline" color="text.secondary">
                {t('reports.margin.overallTitle')}
              </Typography>
              <Stack direction={{ xs: 'column', sm: 'row' }} spacing={4} mt={1}>
                <Box>
                  <Typography variant="caption" color="text.secondary">
                    {t('reports.margin.totalRevenue')}
                  </Typography>
                  <Typography variant="h6">{marginByProduct.total_revenue}</Typography>
                </Box>
                <Box>
                  <Typography variant="caption" color="text.secondary">
                    {t('reports.margin.totalCost')}
                  </Typography>
                  <Typography variant="h6">{marginByProduct.total_cost}</Typography>
                </Box>
                <Box>
                  <Typography variant="caption" color="text.secondary">
                    {t('reports.margin.totalGrossProfit')}
                  </Typography>
                  <Typography variant="h6">{marginByProduct.total_gross_profit}</Typography>
                </Box>
                <Box>
                  <Typography variant="caption" color="text.secondary">
                    {t('reports.margin.overallMargin')}
                  </Typography>
                  <Typography
                    variant="h6"
                    sx={{
                      color:
                        Number(marginByProduct.overall_margin_rate) >= 0.2
                          ? 'success.main'
                          : Number(marginByProduct.overall_margin_rate) >= 0.1
                          ? 'warning.main'
                          : 'error.main',
                      fontWeight: 700,
                    }}
                  >
                    {formatPercent(marginByProduct.overall_margin_rate)}
                  </Typography>
                </Box>
              </Stack>
            </Paper>
          )}

          <Paper sx={{ p: 2 }}>
            <Typography variant="subtitle2" sx={{ mb: 1 }}>
              {t('reports.margin.trendTitle')}
            </Typography>
            <TableContainer>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>{t('reports.margin.yearMonth')}</TableCell>
                    <TableCell align="right">{t('reports.margin.qty')}</TableCell>
                    <TableCell align="right">{t('reports.margin.revenue')}</TableCell>
                    <TableCell align="right">{t('reports.margin.cost')}</TableCell>
                    <TableCell align="right">{t('reports.margin.grossProfit')}</TableCell>
                    <TableCell align="right">{t('reports.margin.marginRate')}</TableCell>
                    <TableCell align="right">{t('reports.margin.avgUnitPrice')}</TableCell>
                    <TableCell align="right">{t('reports.margin.avgUnitCost')}</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {marginLoading ? (
                    <TableRow>
                      <TableCell colSpan={8} align="center">
                        <CircularProgress size={24} />
                      </TableCell>
                    </TableRow>
                  ) : !marginTrend || marginTrend.rows.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={8} align="center">
                        <Typography color="text.secondary">{t('common.noData')}</Typography>
                      </TableCell>
                    </TableRow>
                  ) : (
                    marginTrend.rows.map((row) => (
                      <TableRow key={`${row.year}-${row.month}`} hover>
                        <TableCell>
                          {row.year}-{String(row.month).padStart(2, '0')}
                        </TableCell>
                        <TableCell align="right">{row.quantity}</TableCell>
                        <TableCell align="right">{row.revenue}</TableCell>
                        <TableCell align="right">{row.cost}</TableCell>
                        <TableCell align="right">{row.gross_profit}</TableCell>
                        <TableCell align="right">
                          <Typography
                            component="span"
                            sx={{
                              fontWeight: 600,
                              color:
                                row.quantity === 0
                                  ? 'text.disabled'
                                  : Number(row.margin_rate) >= 0.2
                                  ? 'success.main'
                                  : Number(row.margin_rate) >= 0.1
                                  ? 'warning.main'
                                  : 'error.main',
                            }}
                          >
                            {row.quantity === 0 ? '—' : formatPercent(row.margin_rate)}
                          </Typography>
                        </TableCell>
                        <TableCell align="right">{row.avg_unit_price}</TableCell>
                        <TableCell align="right">{row.avg_unit_cost}</TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            </TableContainer>
          </Paper>

          <Grid container spacing={2}>
            <Grid item xs={12} md={6}>
              <Paper sx={{ p: 2 }}>
                <Typography variant="subtitle2" sx={{ mb: 1 }}>
                  {t('reports.margin.byProductTitle')}
                </Typography>
                <TableContainer>
                  <Table size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell>{t('reports.margin.product')}</TableCell>
                        <TableCell align="right">{t('reports.margin.revenue')}</TableCell>
                        <TableCell align="right">{t('reports.margin.grossProfit')}</TableCell>
                        <TableCell align="right">{t('reports.margin.marginRate')}</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {marginLoading ? (
                        <TableRow>
                          <TableCell colSpan={4} align="center">
                            <CircularProgress size={24} />
                          </TableCell>
                        </TableRow>
                      ) : !marginByProduct || marginByProduct.rows.length === 0 ? (
                        <TableRow>
                          <TableCell colSpan={4} align="center">
                            <Typography color="text.secondary">{t('common.noData')}</Typography>
                          </TableCell>
                        </TableRow>
                      ) : (
                        marginByProduct.rows.map((row) => (
                          <TableRow key={row.product_id} hover>
                            <TableCell>
                              <Typography variant="body2" component="span">
                                {row.name}
                              </Typography>
                              <Typography
                                component="span"
                                color="text.secondary"
                                sx={{ ml: 1, fontSize: '0.8em' }}
                              >
                                ({row.sku})
                              </Typography>
                            </TableCell>
                            <TableCell align="right">{row.revenue}</TableCell>
                            <TableCell align="right">{row.gross_profit}</TableCell>
                            <TableCell align="right">{formatPercent(row.margin_rate)}</TableCell>
                          </TableRow>
                        ))
                      )}
                    </TableBody>
                  </Table>
                </TableContainer>
              </Paper>
            </Grid>
            <Grid item xs={12} md={6}>
              <Paper sx={{ p: 2 }}>
                <Typography variant="subtitle2" sx={{ mb: 1 }}>
                  {t('reports.margin.byCustomerTitle')}
                </Typography>
                <TableContainer>
                  <Table size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell>{t('reports.margin.customer')}</TableCell>
                        <TableCell align="right">{t('reports.margin.orderCount')}</TableCell>
                        <TableCell align="right">{t('reports.margin.revenue')}</TableCell>
                        <TableCell align="right">{t('reports.margin.grossProfit')}</TableCell>
                        <TableCell align="right">{t('reports.margin.marginRate')}</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {marginLoading ? (
                        <TableRow>
                          <TableCell colSpan={5} align="center">
                            <CircularProgress size={24} />
                          </TableCell>
                        </TableRow>
                      ) : !marginByCustomer || marginByCustomer.rows.length === 0 ? (
                        <TableRow>
                          <TableCell colSpan={5} align="center">
                            <Typography color="text.secondary">{t('common.noData')}</Typography>
                          </TableCell>
                        </TableRow>
                      ) : (
                        marginByCustomer.rows.map((row) => (
                          <TableRow key={row.customer_id} hover>
                            <TableCell>{row.customer_name}</TableCell>
                            <TableCell align="right">{row.order_count}</TableCell>
                            <TableCell align="right">{row.revenue}</TableCell>
                            <TableCell align="right">{row.gross_profit}</TableCell>
                            <TableCell align="right">{formatPercent(row.margin_rate)}</TableCell>
                          </TableRow>
                        ))
                      )}
                    </TableBody>
                  </Table>
                </TableContainer>
              </Paper>
            </Grid>
          </Grid>
        </Stack>
      )}
    </Box>
  )
}

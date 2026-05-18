import { useEffect, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import {
  Alert,
  Box,
  Chip,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Button,
  Divider,
  FormControl,
  FormControlLabel,
  IconButton,
  InputLabel,
  MenuItem,
  Paper,
  Select,
  Stack,
  Switch,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Tooltip,
  Typography,
} from '@mui/material'
import VisibilityIcon from '@mui/icons-material/Visibility'
import PaidIcon from '@mui/icons-material/Paid'

import * as arApi from '@/api/accountsReceivable'
import * as arPaymentsApi from '@/api/arPayments'
import * as customersApi from '@/api/customers'
import { useAuth } from '@/contexts/AuthContext'

const PAYMENT_METHODS = ['cash', 'bank_transfer', 'check', 'other']

function methodLabelKey(method) {
  const camel = method.replace(/_([a-z])/g, (_, c) => c.toUpperCase())
  return `accountsReceivable.paymentMethod${camel.charAt(0).toUpperCase()}${camel.slice(1)}`
}

function todayIsoDate() {
  const now = new Date()
  const offset = now.getTimezoneOffset()
  const local = new Date(now.getTime() - offset * 60 * 1000)
  return local.toISOString().slice(0, 10)
}

const STATUS_COLORS = {
  open: 'warning',
  partial: 'info',
  paid: 'success',
  voided: 'default',
}

function formatDate(value) {
  if (!value) return '—'
  try {
    return new Date(value).toLocaleDateString()
  } catch {
    return value
  }
}

function formatDateTime(value) {
  if (!value) return '—'
  try {
    return new Date(value).toLocaleString()
  } catch {
    return value
  }
}

function formatAmount(value) {
  if (value == null) return '—'
  const num = Number(value)
  if (!Number.isFinite(num)) return String(value)
  return num.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

export default function AccountsReceivablePage() {
  const { t } = useTranslation()
  const { hasRole } = useAuth()
  const canRecordPayment = hasRole('admin', 'manager', 'sales')

  const [rows, setRows] = useState([])
  const [customers, setCustomers] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [reloadToken, setReloadToken] = useState(0)

  const [search, setSearch] = useState('')
  const [filterStatus, setFilterStatus] = useState('')
  const [filterCustomer, setFilterCustomer] = useState('')
  const [overdueOnly, setOverdueOnly] = useState(false)

  const [detail, setDetail] = useState(null)
  // null = still loading (or no detail open). [] = loaded, empty list.
  const [payments, setPayments] = useState(null)
  const [paymentForm, setPaymentForm] = useState(null)
  const [paymentSubmitting, setPaymentSubmitting] = useState(false)
  const [paymentError, setPaymentError] = useState(null)
  const [voidForm, setVoidForm] = useState(null) // { payment, reason }
  const [voidSubmitting, setVoidSubmitting] = useState(false)
  const [voidError, setVoidError] = useState(null)
  const paymentsLoading = detail !== null && payments === null

  const customerMap = useMemo(
    () => Object.fromEntries(customers.map((c) => [c.id, c])),
    [customers],
  )

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      try {
        const params = {}
        if (search.trim()) params.search = search.trim()
        if (filterStatus) params.status_filter = filterStatus
        if (filterCustomer) params.customer_id = filterCustomer
        if (overdueOnly) params.overdue_only = true
        const [list, cust] = await Promise.all([
          arApi.listReceivables(params),
          customersApi.listCustomers(),
        ])
        if (!cancelled) {
          setRows(list)
          setCustomers(cust)
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
  }, [reloadToken, search, filterStatus, filterCustomer, overdueOnly])

  // Load payment history whenever the detail dialog opens.
  useEffect(() => {
    if (!detail) return
    let cancelled = false
    ;(async () => {
      try {
        const list = await arPaymentsApi.listForReceivable(detail.id)
        if (!cancelled) setPayments(list)
      } catch (err) {
        if (!cancelled) {
          setPaymentError(err.response?.data?.detail || err.message)
          setPayments([])
        }
      }
    })()
    return () => {
      cancelled = true
    }
  }, [detail])

  const openPaymentForm = () => {
    if (!detail) return
    const balance = Number(detail.balance) || 0
    setPaymentForm({
      amount: balance > 0 ? balance.toFixed(2) : '',
      method: 'bank_transfer',
      paid_at: todayIsoDate(),
      reference: '',
      notes: '',
    })
    setPaymentError(null)
  }

  const submitPayment = async (event) => {
    event.preventDefault()
    if (!detail || !paymentForm) return
    setPaymentSubmitting(true)
    setPaymentError(null)
    try {
      const paidAtIso = paymentForm.paid_at
        ? new Date(`${paymentForm.paid_at}T00:00:00`).toISOString()
        : undefined
      await arPaymentsApi.createPayment({
        accounts_receivable_id: detail.id,
        amount: paymentForm.amount,
        method: paymentForm.method,
        paid_at: paidAtIso,
        reference: paymentForm.reference.trim() || null,
        notes: paymentForm.notes.trim() || null,
      })
      setPaymentForm(null)
      // Refresh detail + payments + list.
      const refreshed = await arApi.getReceivable(detail.id)
      setDetail(refreshed)
      const list = await arPaymentsApi.listForReceivable(detail.id)
      setPayments(list)
      setReloadToken((t) => t + 1)
    } catch (err) {
      setPaymentError(err.response?.data?.detail || err.message)
    } finally {
      setPaymentSubmitting(false)
    }
  }

  const openVoidForm = (payment) => {
    setVoidForm({ payment, reason: '' })
    setVoidError(null)
  }

  const submitVoid = async (event) => {
    event.preventDefault()
    if (!voidForm || !detail) return
    setVoidSubmitting(true)
    setVoidError(null)
    try {
      await arPaymentsApi.voidPayment(voidForm.payment.id, voidForm.reason.trim() || null)
      setVoidForm(null)
      const refreshed = await arApi.getReceivable(detail.id)
      setDetail(refreshed)
      const list = await arPaymentsApi.listForReceivable(detail.id)
      setPayments(list)
      setReloadToken((t) => t + 1)
    } catch (err) {
      setVoidError(err.response?.data?.detail || err.message)
    } finally {
      setVoidSubmitting(false)
    }
  }

  const totals = useMemo(() => {
    let amountTotal = 0
    let balance = 0
    rows.forEach((r) => {
      amountTotal += Number(r.amount_total) || 0
      balance += Number(r.balance) || 0
    })
    return { amountTotal, balance, count: rows.length }
  }, [rows])

  return (
    <Box>
      <Stack direction="row" justifyContent="space-between" alignItems="center" mb={2}>
        <Typography variant="h4">{t('accountsReceivable.title')}</Typography>
      </Stack>

      <Paper sx={{ p: 2, mb: 2 }}>
        <Stack direction={{ xs: 'column', md: 'row' }} spacing={2} alignItems={{ md: 'center' }}>
          <TextField
            label={t('common.search')}
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder={t('accountsReceivable.searchPlaceholder')}
            size="small"
            sx={{ flexGrow: 1 }}
          />
          <FormControl size="small" sx={{ minWidth: 160 }}>
            <InputLabel>{t('accountsReceivable.customer')}</InputLabel>
            <Select
              label={t('accountsReceivable.customer')}
              value={filterCustomer}
              onChange={(e) => setFilterCustomer(e.target.value)}
            >
              <MenuItem value="">{t('common.all')}</MenuItem>
              {customers.map((c) => (
                <MenuItem key={c.id} value={String(c.id)}>
                  {c.name}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          <FormControl size="small" sx={{ minWidth: 140 }}>
            <InputLabel>{t('accountsReceivable.status')}</InputLabel>
            <Select
              label={t('accountsReceivable.status')}
              value={filterStatus}
              onChange={(e) => setFilterStatus(e.target.value)}
            >
              <MenuItem value="">{t('common.all')}</MenuItem>
              <MenuItem value="open">{t('accountsReceivable.statusOpen')}</MenuItem>
              <MenuItem value="partial">{t('accountsReceivable.statusPartial')}</MenuItem>
              <MenuItem value="paid">{t('accountsReceivable.statusPaid')}</MenuItem>
              <MenuItem value="voided">{t('accountsReceivable.statusVoided')}</MenuItem>
            </Select>
          </FormControl>
          <FormControlLabel
            control={
              <Switch
                checked={overdueOnly}
                onChange={(e) => setOverdueOnly(e.target.checked)}
              />
            }
            label={t('accountsReceivable.overdueOnly')}
            sx={{ whiteSpace: 'nowrap' }}
          />
        </Stack>
      </Paper>

      <Paper sx={{ p: 2, mb: 2 }}>
        <Stack direction="row" spacing={4}>
          <Box>
            <Typography variant="caption" color="text.secondary">
              {t('accountsReceivable.amountTotal')}
            </Typography>
            <Typography variant="h6">{formatAmount(totals.amountTotal)}</Typography>
          </Box>
          <Box>
            <Typography variant="caption" color="text.secondary">
              {t('accountsReceivable.balance')}
            </Typography>
            <Typography variant="h6" color={totals.balance > 0 ? 'warning.main' : 'text.primary'}>
              {formatAmount(totals.balance)}
            </Typography>
          </Box>
        </Stack>
      </Paper>

      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

      <TableContainer component={Paper}>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>{t('accountsReceivable.arNumber')}</TableCell>
              <TableCell>{t('accountsReceivable.salesOrder')}</TableCell>
              <TableCell>{t('accountsReceivable.customer')}</TableCell>
              <TableCell align="right">{t('accountsReceivable.amountUntaxed')}</TableCell>
              <TableCell align="right">{t('accountsReceivable.taxAmount')}</TableCell>
              <TableCell align="right">{t('accountsReceivable.amountTotal')}</TableCell>
              <TableCell align="right">{t('accountsReceivable.balance')}</TableCell>
              <TableCell>{t('accountsReceivable.status')}</TableCell>
              <TableCell>{t('accountsReceivable.dueDate')}</TableCell>
              <TableCell align="right">{t('common.actions')}</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {loading ? (
              <TableRow>
                <TableCell colSpan={10} align="center">
                  <CircularProgress size={24} />
                </TableCell>
              </TableRow>
            ) : rows.length === 0 ? (
              <TableRow>
                <TableCell colSpan={10} align="center">
                  <Typography color="text.secondary">{t('common.noData')}</Typography>
                </TableCell>
              </TableRow>
            ) : (
              rows.map((row) => (
                <TableRow key={row.id} hover>
                  <TableCell>{row.ar_number}</TableCell>
                  <TableCell>{row.sales_order?.so_number || '—'}</TableCell>
                  <TableCell>
                    {row.customer?.name || customerMap[row.customer_id]?.name || `#${row.customer_id}`}
                  </TableCell>
                  <TableCell align="right">{formatAmount(row.amount_untaxed)}</TableCell>
                  <TableCell align="right">{formatAmount(row.tax_amount)}</TableCell>
                  <TableCell align="right">{formatAmount(row.amount_total)}</TableCell>
                  <TableCell align="right">{formatAmount(row.balance)}</TableCell>
                  <TableCell>
                    <Stack direction="row" spacing={0.5} alignItems="center">
                      <Chip
                        size="small"
                        label={t(`accountsReceivable.status${row.status.charAt(0).toUpperCase()}${row.status.slice(1)}`)}
                        color={STATUS_COLORS[row.status] || 'default'}
                      />
                      {row.is_overdue && (
                        <Chip
                          size="small"
                          color="error"
                          label={t('accountsReceivable.overdueBadge')}
                        />
                      )}
                    </Stack>
                  </TableCell>
                  <TableCell>{formatDate(row.due_date)}</TableCell>
                  <TableCell align="right">
                    <Tooltip title={t('common.view')}>
                      <IconButton size="small" onClick={() => setDetail(row)}>
                        <VisibilityIcon fontSize="small" />
                      </IconButton>
                    </Tooltip>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </TableContainer>

      <Dialog open={Boolean(detail)} onClose={() => { setDetail(null); setPayments(null) }} fullWidth maxWidth="sm">
        <DialogTitle>
          {t('accountsReceivable.detailTitle')} — {detail?.ar_number}
        </DialogTitle>
        <DialogContent>
          {detail && (
            <Stack spacing={2} sx={{ mt: 1 }}>
              <Stack direction="row" justifyContent="space-between">
                <Typography variant="body2" color="text.secondary">
                  {t('accountsReceivable.customer')}
                </Typography>
                <Typography variant="body2">{detail.customer?.name || '—'}</Typography>
              </Stack>
              <Stack direction="row" justifyContent="space-between">
                <Typography variant="body2" color="text.secondary">
                  {t('accountsReceivable.salesOrder')}
                </Typography>
                <Typography variant="body2">{detail.sales_order?.so_number || '—'}</Typography>
              </Stack>
              <Stack direction="row" justifyContent="space-between">
                <Typography variant="body2" color="text.secondary">
                  {t('accountsReceivable.issuedAt')}
                </Typography>
                <Typography variant="body2">{formatDateTime(detail.issued_at)}</Typography>
              </Stack>
              <Stack direction="row" justifyContent="space-between">
                <Typography variant="body2" color="text.secondary">
                  {t('accountsReceivable.dueDate')}
                </Typography>
                <Typography variant="body2">{formatDate(detail.due_date)}</Typography>
              </Stack>
              <Divider />
              <Stack direction="row" justifyContent="space-between">
                <Typography variant="body2" color="text.secondary">
                  {t('accountsReceivable.amountUntaxed')}
                </Typography>
                <Typography variant="body2">{formatAmount(detail.amount_untaxed)}</Typography>
              </Stack>
              <Stack direction="row" justifyContent="space-between">
                <Typography variant="body2" color="text.secondary">
                  {t('accountsReceivable.taxAmount')}
                </Typography>
                <Typography variant="body2">{formatAmount(detail.tax_amount)}</Typography>
              </Stack>
              <Stack direction="row" justifyContent="space-between">
                <Typography variant="subtitle2">{t('accountsReceivable.amountTotal')}</Typography>
                <Typography variant="subtitle2">{formatAmount(detail.amount_total)}</Typography>
              </Stack>
              <Divider />
              <Stack direction="row" justifyContent="space-between">
                <Typography variant="body2" color="text.secondary">
                  {t('accountsReceivable.paidAmount')}
                </Typography>
                <Typography variant="body2">{formatAmount(detail.paid_amount)}</Typography>
              </Stack>
              <Stack direction="row" justifyContent="space-between">
                <Typography variant="subtitle2">{t('accountsReceivable.balance')}</Typography>
                <Typography variant="subtitle2" color={detail.balance > 0 ? 'warning.main' : 'text.primary'}>
                  {formatAmount(detail.balance)}
                </Typography>
              </Stack>

              <Divider />
              <Typography variant="subtitle2">{t('accountsReceivable.paymentHistory')}</Typography>
              {paymentsLoading || payments === null ? (
                <Box sx={{ textAlign: 'center', py: 1 }}>
                  <CircularProgress size={20} />
                </Box>
              ) : payments.length === 0 ? (
                <Typography variant="body2" color="text.secondary">
                  {t('accountsReceivable.noPayments')}
                </Typography>
              ) : (
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>{t('accountsReceivable.paymentNumber')}</TableCell>
                      <TableCell>{t('accountsReceivable.paidAt')}</TableCell>
                      <TableCell>{t('accountsReceivable.paymentMethod')}</TableCell>
                      <TableCell align="right">{t('accountsReceivable.paymentAmount')}</TableCell>
                      <TableCell>{t('accountsReceivable.operator')}</TableCell>
                      <TableCell align="right">{t('common.actions')}</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {payments.map((p) => {
                      const voided = p.is_voided
                      const cellSx = voided
                        ? { textDecoration: 'line-through', color: 'text.disabled' }
                        : {}
                      return (
                        <TableRow key={p.id}>
                          <TableCell sx={cellSx}>
                            <Stack direction="row" spacing={1} alignItems="center">
                              <span>{p.payment_number}</span>
                              {voided && (
                                <Tooltip
                                  title={
                                    p.void_reason
                                      ? `${p.void_reason} · ${p.voided_by?.full_name || p.voided_by?.username || ''}`
                                      : (p.voided_by?.full_name || p.voided_by?.username || '')
                                  }
                                >
                                  <Chip
                                    size="small"
                                    color="default"
                                    label={t('accountsReceivable.voidedBadge')}
                                  />
                                </Tooltip>
                              )}
                            </Stack>
                          </TableCell>
                          <TableCell sx={cellSx}>{formatDate(p.paid_at)}</TableCell>
                          <TableCell sx={cellSx}>{t(methodLabelKey(p.method))}</TableCell>
                          <TableCell align="right" sx={cellSx}>{formatAmount(p.amount)}</TableCell>
                          <TableCell sx={cellSx}>{p.operator?.full_name || p.operator?.username || '—'}</TableCell>
                          <TableCell align="right">
                            {!voided && canRecordPayment && (
                              <Button
                                size="small"
                                color="error"
                                onClick={() => openVoidForm(p)}
                              >
                                {t('accountsReceivable.voidPayment')}
                              </Button>
                            )}
                          </TableCell>
                        </TableRow>
                      )
                    })}
                  </TableBody>
                </Table>
              )}
            </Stack>
          )}
        </DialogContent>
        <DialogActions>
          {detail && canRecordPayment &&
            detail.status !== 'paid' &&
            detail.status !== 'voided' && (
            <Button startIcon={<PaidIcon />} onClick={openPaymentForm}>
              {t('accountsReceivable.recordPayment')}
            </Button>
          )}
          <Button onClick={() => { setDetail(null); setPayments(null) }}>{t('common.close')}</Button>
        </DialogActions>
      </Dialog>

      <Dialog
        open={Boolean(paymentForm)}
        onClose={() => setPaymentForm(null)}
        fullWidth
        maxWidth="xs"
      >
        <Box component="form" onSubmit={submitPayment}>
          <DialogTitle>{t('accountsReceivable.recordPayment')}</DialogTitle>
          <DialogContent>
            <Stack spacing={2} sx={{ mt: 1 }}>
              {paymentError && <Alert severity="error">{paymentError}</Alert>}
              <TextField
                label={t('accountsReceivable.paymentAmount')}
                value={paymentForm?.amount || ''}
                onChange={(e) => setPaymentForm({ ...paymentForm, amount: e.target.value })}
                type="number"
                inputProps={{ min: 0.01, step: '0.01' }}
                helperText={detail ? `${t('accountsReceivable.balance')}: ${formatAmount(detail.balance)}` : ''}
                required
                fullWidth
              />
              <FormControl fullWidth required>
                <InputLabel>{t('accountsReceivable.paymentMethod')}</InputLabel>
                <Select
                  label={t('accountsReceivable.paymentMethod')}
                  value={paymentForm?.method || 'bank_transfer'}
                  onChange={(e) => setPaymentForm({ ...paymentForm, method: e.target.value })}
                >
                  {PAYMENT_METHODS.map((m) => (
                    <MenuItem key={m} value={m}>
                      {t(methodLabelKey(m))}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
              <TextField
                label={t('accountsReceivable.paidAt')}
                value={paymentForm?.paid_at || ''}
                onChange={(e) => setPaymentForm({ ...paymentForm, paid_at: e.target.value })}
                type="date"
                InputLabelProps={{ shrink: true }}
                fullWidth
              />
              <TextField
                label={t('accountsReceivable.paymentReference')}
                value={paymentForm?.reference || ''}
                onChange={(e) => setPaymentForm({ ...paymentForm, reference: e.target.value })}
                fullWidth
              />
              <TextField
                label={t('accountsReceivable.paymentNotes')}
                value={paymentForm?.notes || ''}
                onChange={(e) => setPaymentForm({ ...paymentForm, notes: e.target.value })}
                multiline
                rows={2}
                fullWidth
              />
            </Stack>
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setPaymentForm(null)}>{t('common.cancel')}</Button>
            <Button type="submit" variant="contained" disabled={paymentSubmitting}>
              {paymentSubmitting ? t('common.loading') : t('common.save')}
            </Button>
          </DialogActions>
        </Box>
      </Dialog>

      <Dialog
        open={Boolean(voidForm)}
        onClose={() => setVoidForm(null)}
        fullWidth
        maxWidth="xs"
      >
        <Box component="form" onSubmit={submitVoid}>
          <DialogTitle>{t('accountsReceivable.voidTitle')}</DialogTitle>
          <DialogContent>
            <Stack spacing={2} sx={{ mt: 1 }}>
              {voidError && <Alert severity="error">{voidError}</Alert>}
              {voidForm && (
                <Typography variant="body2">
                  {t('accountsReceivable.voidConfirm', {
                    number: voidForm.payment.payment_number,
                    amount: formatAmount(voidForm.payment.amount),
                  })}
                </Typography>
              )}
              <TextField
                label={t('accountsReceivable.voidReason')}
                value={voidForm?.reason || ''}
                onChange={(e) => setVoidForm({ ...voidForm, reason: e.target.value })}
                helperText={t('accountsReceivable.voidReasonHint')}
                multiline
                rows={2}
                fullWidth
              />
            </Stack>
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setVoidForm(null)}>{t('common.cancel')}</Button>
            <Button
              type="submit"
              color="error"
              variant="contained"
              disabled={voidSubmitting}
            >
              {voidSubmitting ? t('common.loading') : t('accountsReceivable.voidPayment')}
            </Button>
          </DialogActions>
        </Box>
      </Dialog>
    </Box>
  )
}

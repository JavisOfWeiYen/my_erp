import { useEffect, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControl,
  IconButton,
  InputLabel,
  MenuItem,
  Paper,
  Select,
  Stack,
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
import AddIcon from '@mui/icons-material/Add'
import EditIcon from '@mui/icons-material/Edit'
import VisibilityIcon from '@mui/icons-material/Visibility'
import CheckCircleIcon from '@mui/icons-material/CheckCircle'
import CancelIcon from '@mui/icons-material/Cancel'
import DeleteIcon from '@mui/icons-material/DeleteOutlineOutlined'

import * as salesApi from '@/api/sales'
import * as customersApi from '@/api/customers'
import * as productsApi from '@/api/products'
import * as usersApi from '@/api/users'
import { useAuth } from '@/contexts/AuthContext'

const STATUS_COLORS = {
  draft: 'warning',
  confirmed: 'success',
  cancelled: 'default',
}

const EMPTY_ITEM = { product_id: '', quantity: '1', unit_price: '0' }

function newEmptyForm(defaultSalespersonId = '') {
  return {
    customer_id: '',
    salesperson_id: defaultSalespersonId ? String(defaultSalespersonId) : '',
    notes: '',
    items: [{ ...EMPTY_ITEM }],
  }
}

function saleToForm(sale) {
  return {
    customer_id: String(sale.customer_id || ''),
    salesperson_id: String(sale.salesperson_id || ''),
    notes: sale.notes || '',
    items: sale.items.map((it) => ({
      product_id: String(it.product_id),
      quantity: String(it.quantity),
      unit_price: String(it.unit_price),
    })),
  }
}

function formToPayload(form) {
  return {
    customer_id: Number(form.customer_id),
    salesperson_id: Number(form.salesperson_id),
    notes: form.notes.trim() || null,
    items: form.items.map((it) => ({
      product_id: Number(it.product_id),
      quantity: Number(it.quantity),
      unit_price: it.unit_price || '0',
    })),
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

export default function SalesPage() {
  const { t } = useTranslation()
  const { user, hasRole } = useAuth()
  const canWrite = hasRole('admin', 'manager', 'sales')

  const [rows, setRows] = useState([])
  const [customers, setCustomers] = useState([])
  const [products, setProducts] = useState([])
  const [staff, setStaff] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [reloadToken, setReloadToken] = useState(0)

  const [filterStatus, setFilterStatus] = useState('')
  const [filterCustomer, setFilterCustomer] = useState('')
  const [filterSalesperson, setFilterSalesperson] = useState('')
  const [search, setSearch] = useState('')

  const [editor, setEditor] = useState({ open: false, mode: 'create', id: null })
  const [form, setForm] = useState(newEmptyForm())
  const [submitting, setSubmitting] = useState(false)
  const [submitError, setSubmitError] = useState(null)

  const [detail, setDetail] = useState(null)
  const [actionTarget, setActionTarget] = useState(null) // { row, action: 'cancel' | 'confirm' }
  const [actionRunning, setActionRunning] = useState(false)

  const productMap = useMemo(
    () => Object.fromEntries(products.map((p) => [p.id, p])),
    [products],
  )
  const staffMap = useMemo(
    () => Object.fromEntries(staff.map((s) => [s.id, s])),
    [staff],
  )
  const staffLabel = (u) => u?.full_name || u?.username || `#${u?.id ?? ''}`

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      try {
        const params = {}
        if (search.trim()) params.search = search.trim()
        if (filterStatus) params.status_filter = filterStatus
        if (filterCustomer) params.customer_id = filterCustomer
        if (filterSalesperson) params.salesperson_id = filterSalesperson
        const [sales, cust, prod, stf] = await Promise.all([
          salesApi.listSales(params),
          customersApi.listCustomers({ is_active: true }),
          productsApi.listProducts({ is_active: true, limit: 1000 }),
          usersApi.listStaff({ active_only: true }),
        ])
        if (!cancelled) {
          setRows(sales)
          setCustomers(cust)
          setProducts(prod)
          setStaff(stf)
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
  }, [reloadToken, search, filterStatus, filterCustomer, filterSalesperson])

  const reload = () => setReloadToken((tk) => tk + 1)

  const totalForForm = useMemo(() => {
    let sum = 0
    for (const it of form.items) {
      const q = Number(it.quantity) || 0
      const p = Number(it.unit_price) || 0
      sum += q * p
    }
    return sum.toFixed(2)
  }, [form])

  const openCreate = () => {
    // default salesperson to the current user when they are themselves a salesperson;
    // otherwise leave blank so admin/manager must pick explicitly.
    const defaultSp = hasRole('sales') ? user?.id : ''
    setForm(newEmptyForm(defaultSp))
    setSubmitError(null)
    setEditor({ open: true, mode: 'create', id: null })
  }

  const openEdit = (row) => {
    setForm(saleToForm(row))
    setSubmitError(null)
    setEditor({ open: true, mode: 'edit', id: row.id })
  }

  const closeEditor = () => setEditor((e) => ({ ...e, open: false }))

  const updateItem = (idx, patch) => {
    setForm((prev) => {
      const items = prev.items.slice()
      items[idx] = { ...items[idx], ...patch }
      return { ...prev, items }
    })
  }

  const onProductSelected = (idx, productIdStr) => {
    const product = productMap[Number(productIdStr)]
    updateItem(idx, {
      product_id: productIdStr,
      ...(product ? { unit_price: String(product.unit_price ?? '0') } : {}),
    })
  }

  const addItem = () =>
    setForm((prev) => ({ ...prev, items: [...prev.items, { ...EMPTY_ITEM }] }))

  const removeItem = (idx) =>
    setForm((prev) => ({
      ...prev,
      items: prev.items.length > 1 ? prev.items.filter((_, i) => i !== idx) : prev.items,
    }))

  const handleSubmit = async (event) => {
    event.preventDefault()
    if (!form.customer_id) {
      setSubmitError(t('sales.errors.customerRequired'))
      return
    }
    if (!form.salesperson_id) {
      setSubmitError(t('sales.errors.salespersonRequired'))
      return
    }
    if (form.items.some((it) => !it.product_id || Number(it.quantity) <= 0)) {
      setSubmitError(t('sales.errors.itemInvalid'))
      return
    }
    setSubmitting(true)
    setSubmitError(null)
    try {
      const payload = formToPayload(form)
      if (editor.mode === 'create') {
        await salesApi.createSale(payload)
      } else {
        await salesApi.updateSale(editor.id, payload)
      }
      closeEditor()
      reload()
    } catch (err) {
      setSubmitError(err.response?.data?.detail || err.message)
    } finally {
      setSubmitting(false)
    }
  }

  const handleAction = async () => {
    if (!actionTarget) return
    setActionRunning(true)
    try {
      if (actionTarget.action === 'cancel') {
        await salesApi.cancelSale(actionTarget.row.id)
      } else {
        await salesApi.confirmSale(actionTarget.row.id)
      }
      setActionTarget(null)
      reload()
    } catch (err) {
      setError(err.response?.data?.detail || err.message)
      setActionTarget(null)
    } finally {
      setActionRunning(false)
    }
  }

  const openDetail = async (row) => {
    try {
      const fresh = await salesApi.getSale(row.id)
      setDetail(fresh)
    } catch (err) {
      setError(err.response?.data?.detail || err.message)
    }
  }

  const colSpan = 8

  return (
    <Box>
      <Stack direction="row" justifyContent="space-between" alignItems="center" mb={2}>
        <Typography variant="h4">{t('nav.sales')}</Typography>
        {canWrite && (
          <Button variant="contained" size="small" startIcon={<AddIcon />} onClick={openCreate} sx={{ ml: 'auto' }}>
            {t('common.create')}
          </Button>
        )}
      </Stack>

      <Paper sx={{ p: 2, mb: 2 }}>
        <Stack direction={{ xs: 'column', md: 'row' }} spacing={2}>
          <TextField
            label={t('common.search')}
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder={t('sales.searchPlaceholder')}
            size="small"
            sx={{ flexGrow: 1 }}
          />
          <FormControl size="small" sx={{ minWidth: 180 }}>
            <InputLabel>{t('sales.customer')}</InputLabel>
            <Select
              label={t('sales.customer')}
              value={filterCustomer}
              onChange={(e) => setFilterCustomer(e.target.value)}
            >
              <MenuItem value="">{t('common.all')}</MenuItem>
              {customers.map((c) => (
                <MenuItem key={c.id} value={c.id}>
                  {c.name}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          <FormControl size="small" sx={{ minWidth: 160 }}>
            <InputLabel>{t('sales.salesperson')}</InputLabel>
            <Select
              label={t('sales.salesperson')}
              value={filterSalesperson}
              onChange={(e) => setFilterSalesperson(e.target.value)}
            >
              <MenuItem value="">{t('common.all')}</MenuItem>
              {staff.map((s) => (
                <MenuItem key={s.id} value={s.id}>
                  {staffLabel(s)}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          <FormControl size="small" sx={{ minWidth: 140 }}>
            <InputLabel>{t('sales.status')}</InputLabel>
            <Select
              label={t('sales.status')}
              value={filterStatus}
              onChange={(e) => setFilterStatus(e.target.value)}
            >
              <MenuItem value="">{t('common.all')}</MenuItem>
              <MenuItem value="draft">{t('sales.statusDraft')}</MenuItem>
              <MenuItem value="confirmed">{t('sales.statusConfirmed')}</MenuItem>
              <MenuItem value="cancelled">{t('sales.statusCancelled')}</MenuItem>
            </Select>
          </FormControl>
        </Stack>
      </Paper>

      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

      <TableContainer component={Paper}>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>{t('sales.soNumber')}</TableCell>
              <TableCell>{t('sales.customer')}</TableCell>
              <TableCell>{t('sales.salesperson')}</TableCell>
              <TableCell>{t('sales.status')}</TableCell>
              <TableCell align="right">{t('sales.totalAmount')}</TableCell>
              <TableCell>{t('sales.orderedAt')}</TableCell>
              <TableCell>{t('sales.confirmedAt')}</TableCell>
              <TableCell align="right">{t('common.actions')}</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {loading ? (
              <TableRow>
                <TableCell colSpan={colSpan} align="center">
                  <CircularProgress size={24} />
                </TableCell>
              </TableRow>
            ) : rows.length === 0 ? (
              <TableRow>
                <TableCell colSpan={colSpan} align="center">
                  <Typography color="text.secondary">{t('common.noData')}</Typography>
                </TableCell>
              </TableRow>
            ) : (
              rows.map((row) => {
                const isDraft = row.status === 'draft'
                return (
                  <TableRow key={row.id} hover>
                    <TableCell>{row.so_number}</TableCell>
                    <TableCell>{row.customer?.name || '—'}</TableCell>
                    <TableCell>{staffLabel(row.salesperson || staffMap[row.salesperson_id])}</TableCell>
                    <TableCell>
                      <Chip
                        size="small"
                        label={t(`sales.status${row.status.charAt(0).toUpperCase()}${row.status.slice(1)}`)}
                        color={STATUS_COLORS[row.status] || 'default'}
                      />
                    </TableCell>
                    <TableCell align="right">{row.total_amount}</TableCell>
                    <TableCell>{formatDateTime(row.ordered_at)}</TableCell>
                    <TableCell>{formatDateTime(row.confirmed_at)}</TableCell>
                    <TableCell align="right">
                      <Tooltip title={t('common.view')}>
                        <IconButton size="small" onClick={() => openDetail(row)}>
                          <VisibilityIcon fontSize="small" />
                        </IconButton>
                      </Tooltip>
                      {canWrite && isDraft && (
                        <Tooltip title={t('common.edit')}>
                          <IconButton size="small" onClick={() => openEdit(row)}>
                            <EditIcon fontSize="small" />
                          </IconButton>
                        </Tooltip>
                      )}
                      {canWrite && isDraft && (
                        <Tooltip title={t('sales.confirm')}>
                          <IconButton
                            size="small"
                            color="success"
                            onClick={() => setActionTarget({ row, action: 'confirm' })}
                          >
                            <CheckCircleIcon fontSize="small" />
                          </IconButton>
                        </Tooltip>
                      )}
                      {canWrite && isDraft && (
                        <Tooltip title={t('sales.cancel')}>
                          <IconButton
                            size="small"
                            color="error"
                            onClick={() => setActionTarget({ row, action: 'cancel' })}
                          >
                            <CancelIcon fontSize="small" />
                          </IconButton>
                        </Tooltip>
                      )}
                    </TableCell>
                  </TableRow>
                )
              })
            )}
          </TableBody>
        </Table>
      </TableContainer>

      <Dialog open={editor.open} onClose={closeEditor} fullWidth maxWidth="md">
        <Box component="form" onSubmit={handleSubmit}>
          <DialogTitle>
            {editor.mode === 'create' ? t('sales.createTitle') : t('sales.editTitle')}
          </DialogTitle>
          <DialogContent>
            <Stack spacing={2} sx={{ mt: 1 }}>
              {submitError && <Alert severity="error">{submitError}</Alert>}
              <FormControl fullWidth required>
                <InputLabel>{t('sales.customer')}</InputLabel>
                <Select
                  label={t('sales.customer')}
                  value={form.customer_id}
                  onChange={(e) => setForm({ ...form, customer_id: e.target.value })}
                >
                  {customers.map((c) => (
                    <MenuItem key={c.id} value={String(c.id)}>
                      {c.name}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
              <FormControl fullWidth required>
                <InputLabel>{t('sales.salesperson')}</InputLabel>
                <Select
                  label={t('sales.salesperson')}
                  value={form.salesperson_id}
                  onChange={(e) => setForm({ ...form, salesperson_id: e.target.value })}
                >
                  {staff.map((s) => (
                    <MenuItem key={s.id} value={String(s.id)}>
                      {staffLabel(s)}
                      {s.role_name ? ` · ${t(`roles.${s.role_name}`, s.role_name)}` : ''}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
              <TextField
                label={t('sales.notes')}
                value={form.notes}
                onChange={(e) => setForm({ ...form, notes: e.target.value })}
                multiline
                rows={2}
                fullWidth
              />

              <Typography variant="subtitle1" sx={{ mt: 1 }}>
                {t('sales.items')}
              </Typography>
              <Stack spacing={1}>
                {form.items.map((item, idx) => {
                  const selectedProduct = productMap[Number(item.product_id)]
                  const onHand = selectedProduct?.stock_quantity ?? null
                  const qty = Number(item.quantity) || 0
                  const lowStock = onHand !== null && qty > onHand
                  return (
                    <Stack key={idx} direction={{ xs: 'column', sm: 'row' }} spacing={1} alignItems="center">
                      <FormControl size="small" sx={{ flexGrow: 1, minWidth: 220 }} required>
                        <InputLabel>{t('sales.product')}</InputLabel>
                        <Select
                          label={t('sales.product')}
                          value={item.product_id}
                          onChange={(e) => onProductSelected(idx, e.target.value)}
                        >
                          {products.map((p) => (
                            <MenuItem key={p.id} value={String(p.id)}>
                              {p.sku} — {p.name} ({t('sales.onHandShort', { qty: p.stock_quantity })})
                            </MenuItem>
                          ))}
                        </Select>
                      </FormControl>
                      <TextField
                        label={t('sales.quantity')}
                        type="number"
                        size="small"
                        inputProps={{ min: 1, step: 1 }}
                        value={item.quantity}
                        onChange={(e) => updateItem(idx, { quantity: e.target.value })}
                        sx={{ width: 110 }}
                        required
                        error={lowStock}
                        helperText={lowStock ? t('sales.shortStockHint', { qty: onHand }) : null}
                      />
                      <TextField
                        label={t('sales.unitPrice')}
                        type="number"
                        size="small"
                        inputProps={{ min: 0, step: '0.01' }}
                        value={item.unit_price}
                        onChange={(e) => updateItem(idx, { unit_price: e.target.value })}
                        sx={{ width: 140 }}
                        required
                      />
                      <Tooltip title={t('common.delete')}>
                        <span>
                          <IconButton
                            size="small"
                            disabled={form.items.length <= 1}
                            onClick={() => removeItem(idx)}
                          >
                            <DeleteIcon fontSize="small" />
                          </IconButton>
                        </span>
                      </Tooltip>
                    </Stack>
                  )
                })}
              </Stack>
              <Stack direction="row" justifyContent="space-between" alignItems="center">
                <Button startIcon={<AddIcon />} onClick={addItem} size="small">
                  {t('sales.addItem')}
                </Button>
                <Typography variant="subtitle2">
                  {t('sales.totalAmount')}: {totalForForm}
                </Typography>
              </Stack>
            </Stack>
          </DialogContent>
          <DialogActions>
            <Button onClick={closeEditor}>{t('common.cancel')}</Button>
            <Button type="submit" variant="contained" disabled={submitting}>
              {submitting ? t('common.loading') : t('common.save')}
            </Button>
          </DialogActions>
        </Box>
      </Dialog>

      <Dialog open={Boolean(detail)} onClose={() => setDetail(null)} fullWidth maxWidth="md">
        <DialogTitle>
          {t('sales.detailTitle')} — {detail?.so_number}
        </DialogTitle>
        <DialogContent>
          {detail && (
            <Stack spacing={2} sx={{ mt: 1 }}>
              <Stack direction={{ xs: 'column', sm: 'row' }} spacing={3}>
                <Box>
                  <Typography variant="caption" color="text.secondary">
                    {t('sales.customer')}
                  </Typography>
                  <Typography>{detail.customer?.name || '—'}</Typography>
                </Box>
                <Box>
                  <Typography variant="caption" color="text.secondary">
                    {t('sales.salesperson')}
                  </Typography>
                  <Typography>{staffLabel(detail.salesperson || staffMap[detail.salesperson_id])}</Typography>
                </Box>
                <Box>
                  <Typography variant="caption" color="text.secondary">
                    {t('sales.status')}
                  </Typography>
                  <Box>
                    <Chip
                      size="small"
                      label={t(`sales.status${detail.status.charAt(0).toUpperCase()}${detail.status.slice(1)}`)}
                      color={STATUS_COLORS[detail.status] || 'default'}
                    />
                  </Box>
                </Box>
                <Box>
                  <Typography variant="caption" color="text.secondary">
                    {t('sales.totalAmount')}
                  </Typography>
                  <Typography>{detail.total_amount}</Typography>
                </Box>
                <Box>
                  <Typography variant="caption" color="text.secondary">
                    {t('sales.orderedAt')}
                  </Typography>
                  <Typography>{formatDateTime(detail.ordered_at)}</Typography>
                </Box>
                <Box>
                  <Typography variant="caption" color="text.secondary">
                    {t('sales.confirmedAt')}
                  </Typography>
                  <Typography>{formatDateTime(detail.confirmed_at)}</Typography>
                </Box>
              </Stack>
              {detail.notes && (
                <Box>
                  <Typography variant="caption" color="text.secondary">
                    {t('sales.notes')}
                  </Typography>
                  <Typography>{detail.notes}</Typography>
                </Box>
              )}

              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>{t('sales.product')}</TableCell>
                    <TableCell align="right">{t('sales.quantity')}</TableCell>
                    <TableCell align="right">{t('sales.unitPrice')}</TableCell>
                    <TableCell align="right">{t('sales.subtotal')}</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {detail.items.map((it) => (
                    <TableRow key={it.id}>
                      <TableCell>
                        {it.product?.sku || productMap[it.product_id]?.sku || '#'}{' — '}
                        {it.product?.name || productMap[it.product_id]?.name || ''}
                      </TableCell>
                      <TableCell align="right">{it.quantity}</TableCell>
                      <TableCell align="right">{it.unit_price}</TableCell>
                      <TableCell align="right">{it.subtotal}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </Stack>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDetail(null)}>{t('common.close')}</Button>
        </DialogActions>
      </Dialog>

      <Dialog open={Boolean(actionTarget)} onClose={() => setActionTarget(null)}>
        <DialogTitle>
          {actionTarget?.action === 'confirm'
            ? t('sales.confirmTitle')
            : t('sales.cancelTitle')}
        </DialogTitle>
        <DialogContent>
          <Typography>
            {actionTarget?.action === 'confirm'
              ? t('sales.confirmHint', { so: actionTarget?.row.so_number })
              : t('sales.cancelHint', { so: actionTarget?.row.so_number })}
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setActionTarget(null)}>{t('common.cancel')}</Button>
          <Button
            onClick={handleAction}
            variant="contained"
            color={actionTarget?.action === 'confirm' ? 'success' : 'error'}
            disabled={actionRunning}
          >
            {actionRunning ? t('common.loading') : t('common.confirm')}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}

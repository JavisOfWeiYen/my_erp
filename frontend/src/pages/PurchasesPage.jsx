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
import AddIcon from '@mui/icons-material/Add'
import EditIcon from '@mui/icons-material/Edit'
import VisibilityIcon from '@mui/icons-material/Visibility'
import CheckCircleIcon from '@mui/icons-material/CheckCircle'
import CancelIcon from '@mui/icons-material/Cancel'
import DeleteIcon from '@mui/icons-material/DeleteOutlineOutlined'

import * as purchasesApi from '@/api/purchases'
import * as suppliersApi from '@/api/suppliers'
import * as productsApi from '@/api/products'
import { useAuth } from '@/contexts/AuthContext'

const STATUS_COLORS = {
  draft: 'warning',
  received: 'success',
  cancelled: 'default',
}

const EMPTY_ITEM = { product_id: '', quantity: '1', unit_cost: '0' }

function newEmptyForm() {
  return {
    supplier_id: '',
    is_tax_inclusive: false,
    notes: '',
    items: [{ ...EMPTY_ITEM }],
  }
}

function purchaseToForm(purchase) {
  return {
    supplier_id: String(purchase.supplier_id || ''),
    is_tax_inclusive: Boolean(purchase.is_tax_inclusive),
    notes: purchase.notes || '',
    items: purchase.items.map((it) => ({
      product_id: String(it.product_id),
      quantity: String(it.quantity),
      unit_cost: String(it.unit_cost),
    })),
  }
}

function formToPayload(form) {
  return {
    supplier_id: Number(form.supplier_id),
    is_tax_inclusive: Boolean(form.is_tax_inclusive),
    notes: form.notes.trim() || null,
    items: form.items.map((it) => ({
      product_id: Number(it.product_id),
      quantity: Number(it.quantity),
      unit_cost: it.unit_cost || '0',
    })),
  }
}

const TAX_RATE = 0.05

function computeTaxBreakdown(total, inclusive) {
  const t = Number(total) || 0
  if (inclusive) {
    const untaxed = Math.round((t / (1 + TAX_RATE)) * 100) / 100
    const tax = Math.round((t - untaxed) * 100) / 100
    return { untaxed, tax, total: t }
  }
  const tax = Math.round(t * TAX_RATE * 100) / 100
  return { untaxed: t, tax, total: t + tax }
}

function formatDateTime(value) {
  if (!value) return '—'
  try {
    return new Date(value).toLocaleString()
  } catch {
    return value
  }
}

export default function PurchasesPage() {
  const { t } = useTranslation()
  const { hasRole } = useAuth()
  const canWrite = hasRole('admin', 'manager')
  const canReceive = hasRole('admin', 'manager', 'warehouse')

  const [rows, setRows] = useState([])
  const [suppliers, setSuppliers] = useState([])
  const [products, setProducts] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [reloadToken, setReloadToken] = useState(0)

  const [filterStatus, setFilterStatus] = useState('')
  const [filterSupplier, setFilterSupplier] = useState('')
  const [search, setSearch] = useState('')

  const [editor, setEditor] = useState({ open: false, mode: 'create', id: null })
  const [form, setForm] = useState(newEmptyForm())
  const [submitting, setSubmitting] = useState(false)
  const [submitError, setSubmitError] = useState(null)

  const [detail, setDetail] = useState(null)
  const [actionTarget, setActionTarget] = useState(null) // { row, action: 'cancel' | 'receive' }
  const [actionRunning, setActionRunning] = useState(false)

  const productMap = useMemo(
    () => Object.fromEntries(products.map((p) => [p.id, p])),
    [products],
  )

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      try {
        const params = {}
        if (search.trim()) params.search = search.trim()
        if (filterStatus) params.status_filter = filterStatus
        if (filterSupplier) params.supplier_id = filterSupplier
        const [purchases, sup, prod] = await Promise.all([
          purchasesApi.listPurchases(params),
          suppliersApi.listSuppliers({ is_active: true }),
          productsApi.listProducts({ is_active: true, limit: 1000 }),
        ])
        if (!cancelled) {
          setRows(purchases)
          setSuppliers(sup)
          setProducts(prod)
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
  }, [reloadToken, search, filterStatus, filterSupplier])

  const reload = () => setReloadToken((tk) => tk + 1)

  const totalForForm = useMemo(() => {
    let sum = 0
    for (const it of form.items) {
      const q = Number(it.quantity) || 0
      const c = Number(it.unit_cost) || 0
      sum += q * c
    }
    return sum.toFixed(2)
  }, [form])

  const openCreate = () => {
    setForm(newEmptyForm())
    setSubmitError(null)
    setEditor({ open: true, mode: 'create', id: null })
  }

  const openEdit = (row) => {
    setForm(purchaseToForm(row))
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

  const addItem = () =>
    setForm((prev) => ({ ...prev, items: [...prev.items, { ...EMPTY_ITEM }] }))

  const removeItem = (idx) =>
    setForm((prev) => ({
      ...prev,
      items: prev.items.length > 1 ? prev.items.filter((_, i) => i !== idx) : prev.items,
    }))

  const handleSubmit = async (event) => {
    event.preventDefault()
    if (!form.supplier_id) {
      setSubmitError(t('purchases.errors.supplierRequired'))
      return
    }
    if (form.items.some((it) => !it.product_id || Number(it.quantity) <= 0)) {
      setSubmitError(t('purchases.errors.itemInvalid'))
      return
    }
    setSubmitting(true)
    setSubmitError(null)
    try {
      const payload = formToPayload(form)
      if (editor.mode === 'create') {
        await purchasesApi.createPurchase(payload)
      } else {
        await purchasesApi.updatePurchase(editor.id, payload)
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
        await purchasesApi.cancelPurchase(actionTarget.row.id)
      } else {
        await purchasesApi.receivePurchase(actionTarget.row.id)
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
      const fresh = await purchasesApi.getPurchase(row.id)
      setDetail(fresh)
    } catch (err) {
      setError(err.response?.data?.detail || err.message)
    }
  }

  const colSpan = 7

  return (
    <Box>
      <Stack direction="row" justifyContent="space-between" alignItems="center" mb={2}>
        <Typography variant="h4">{t('nav.purchases')}</Typography>
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
            placeholder={t('purchases.searchPlaceholder')}
            size="small"
            sx={{ flexGrow: 1 }}
          />
          <FormControl size="small" sx={{ minWidth: 180 }}>
            <InputLabel>{t('purchases.supplier')}</InputLabel>
            <Select
              label={t('purchases.supplier')}
              value={filterSupplier}
              onChange={(e) => setFilterSupplier(e.target.value)}
            >
              <MenuItem value="">{t('common.all')}</MenuItem>
              {suppliers.map((s) => (
                <MenuItem key={s.id} value={s.id}>
                  {s.name}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          <FormControl size="small" sx={{ minWidth: 140 }}>
            <InputLabel>{t('purchases.status')}</InputLabel>
            <Select
              label={t('purchases.status')}
              value={filterStatus}
              onChange={(e) => setFilterStatus(e.target.value)}
            >
              <MenuItem value="">{t('common.all')}</MenuItem>
              <MenuItem value="draft">{t('purchases.statusDraft')}</MenuItem>
              <MenuItem value="received">{t('purchases.statusReceived')}</MenuItem>
              <MenuItem value="cancelled">{t('purchases.statusCancelled')}</MenuItem>
            </Select>
          </FormControl>
        </Stack>
      </Paper>

      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

      <TableContainer component={Paper}>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>{t('purchases.poNumber')}</TableCell>
              <TableCell>{t('purchases.supplier')}</TableCell>
              <TableCell>{t('purchases.status')}</TableCell>
              <TableCell align="right">{t('purchases.totalAmount')}</TableCell>
              <TableCell>{t('purchases.orderedAt')}</TableCell>
              <TableCell>{t('purchases.receivedAt')}</TableCell>
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
                    <TableCell>{row.po_number}</TableCell>
                    <TableCell>{row.supplier?.name || '—'}</TableCell>
                    <TableCell>
                      <Chip
                        size="small"
                        label={t(`purchases.status${row.status.charAt(0).toUpperCase()}${row.status.slice(1)}`)}
                        color={STATUS_COLORS[row.status] || 'default'}
                      />
                    </TableCell>
                    <TableCell align="right">{row.total_amount}</TableCell>
                    <TableCell>{formatDateTime(row.ordered_at)}</TableCell>
                    <TableCell>{formatDateTime(row.received_at)}</TableCell>
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
                      {canReceive && isDraft && (
                        <Tooltip title={t('purchases.receive')}>
                          <IconButton
                            size="small"
                            color="success"
                            onClick={() => setActionTarget({ row, action: 'receive' })}
                          >
                            <CheckCircleIcon fontSize="small" />
                          </IconButton>
                        </Tooltip>
                      )}
                      {canWrite && isDraft && (
                        <Tooltip title={t('purchases.cancel')}>
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
            {editor.mode === 'create' ? t('purchases.createTitle') : t('purchases.editTitle')}
          </DialogTitle>
          <DialogContent>
            <Stack spacing={2} sx={{ mt: 1 }}>
              {submitError && <Alert severity="error">{submitError}</Alert>}
              <FormControl fullWidth required>
                <InputLabel>{t('purchases.supplier')}</InputLabel>
                <Select
                  label={t('purchases.supplier')}
                  value={form.supplier_id}
                  onChange={(e) => setForm({ ...form, supplier_id: e.target.value })}
                >
                  {suppliers.map((s) => (
                    <MenuItem key={s.id} value={String(s.id)}>
                      {s.name}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
              <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2} alignItems={{ sm: 'center' }}>
                <TextField
                  label={t('purchases.notes')}
                  value={form.notes}
                  onChange={(e) => setForm({ ...form, notes: e.target.value })}
                  multiline
                  rows={2}
                  sx={{ flexGrow: 1 }}
                />
                <FormControlLabel
                  control={
                    <Switch
                      checked={form.is_tax_inclusive}
                      onChange={(e) => setForm({ ...form, is_tax_inclusive: e.target.checked })}
                    />
                  }
                  label={t('purchases.taxInclusive')}
                  sx={{ whiteSpace: 'nowrap' }}
                  title={t('purchases.taxInclusiveHint')}
                />
              </Stack>

              <Typography variant="subtitle1" sx={{ mt: 1 }}>
                {t('purchases.items')}
              </Typography>
              <Stack spacing={1}>
                {form.items.map((item, idx) => (
                  <Stack key={idx} direction={{ xs: 'column', sm: 'row' }} spacing={1} alignItems="center">
                    <FormControl size="small" sx={{ flexGrow: 1, minWidth: 220 }} required>
                      <InputLabel>{t('purchases.product')}</InputLabel>
                      <Select
                        label={t('purchases.product')}
                        value={item.product_id}
                        onChange={(e) => updateItem(idx, { product_id: e.target.value })}
                      >
                        {products.map((p) => (
                          <MenuItem key={p.id} value={String(p.id)}>
                            {p.sku} — {p.name}
                          </MenuItem>
                        ))}
                      </Select>
                    </FormControl>
                    <TextField
                      label={t('purchases.quantity')}
                      type="number"
                      size="small"
                      inputProps={{ min: 1, step: 1 }}
                      value={item.quantity}
                      onChange={(e) => updateItem(idx, { quantity: e.target.value })}
                      sx={{ width: 110 }}
                      required
                    />
                    <TextField
                      label={t('purchases.unitCost')}
                      type="number"
                      size="small"
                      inputProps={{ min: 0, step: '0.01' }}
                      value={item.unit_cost}
                      onChange={(e) => updateItem(idx, { unit_cost: e.target.value })}
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
                ))}
              </Stack>
              <Stack direction="row" justifyContent="space-between" alignItems="center">
                <Button startIcon={<AddIcon />} onClick={addItem} size="small">
                  {t('purchases.addItem')}
                </Button>
                <Box sx={{ textAlign: 'right' }}>
                  {(() => {
                    const bd = computeTaxBreakdown(totalForForm, form.is_tax_inclusive)
                    return (
                      <>
                        <Typography variant="caption" color="text.secondary" display="block">
                          {t('purchases.untaxedSubtotal')}: {bd.untaxed.toFixed(2)} · {t('purchases.taxAmount')}: {bd.tax.toFixed(2)}
                        </Typography>
                        <Typography variant="subtitle2">
                          {t('purchases.totalWithTax')}: {bd.total.toFixed(2)}
                        </Typography>
                      </>
                    )
                  })()}
                </Box>
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
          {t('purchases.detailTitle')} — {detail?.po_number}
        </DialogTitle>
        <DialogContent>
          {detail && (
            <Stack spacing={2} sx={{ mt: 1 }}>
              <Stack direction={{ xs: 'column', sm: 'row' }} spacing={3}>
                <Box>
                  <Typography variant="caption" color="text.secondary">
                    {t('purchases.supplier')}
                  </Typography>
                  <Typography>{detail.supplier?.name || '—'}</Typography>
                </Box>
                <Box>
                  <Typography variant="caption" color="text.secondary">
                    {t('purchases.status')}
                  </Typography>
                  <Box>
                    <Chip
                      size="small"
                      label={t(`purchases.status${detail.status.charAt(0).toUpperCase()}${detail.status.slice(1)}`)}
                      color={STATUS_COLORS[detail.status] || 'default'}
                    />
                  </Box>
                </Box>
                <Box>
                  <Typography variant="caption" color="text.secondary">
                    {t('purchases.totalAmount')}
                  </Typography>
                  <Typography>{detail.total_amount}</Typography>
                </Box>
                <Box>
                  <Typography variant="caption" color="text.secondary">
                    {t('purchases.orderedAt')}
                  </Typography>
                  <Typography>{formatDateTime(detail.ordered_at)}</Typography>
                </Box>
                <Box>
                  <Typography variant="caption" color="text.secondary">
                    {t('purchases.receivedAt')}
                  </Typography>
                  <Typography>{formatDateTime(detail.received_at)}</Typography>
                </Box>
              </Stack>
              {detail.notes && (
                <Box>
                  <Typography variant="caption" color="text.secondary">
                    {t('purchases.notes')}
                  </Typography>
                  <Typography>{detail.notes}</Typography>
                </Box>
              )}

              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>{t('purchases.product')}</TableCell>
                    <TableCell align="right">{t('purchases.quantity')}</TableCell>
                    <TableCell align="right">{t('purchases.unitCost')}</TableCell>
                    <TableCell align="right">{t('purchases.subtotal')}</TableCell>
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
                      <TableCell align="right">{it.unit_cost}</TableCell>
                      <TableCell align="right">{it.subtotal}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>

              <Divider />
              {(() => {
                const bd = computeTaxBreakdown(detail.total_amount, detail.is_tax_inclusive)
                return (
                  <Box sx={{ alignSelf: 'flex-end', textAlign: 'right', minWidth: 240 }}>
                    <Stack direction="row" justifyContent="space-between">
                      <Typography variant="body2" color="text.secondary">
                        {t('purchases.untaxedSubtotal')}
                      </Typography>
                      <Typography variant="body2">{bd.untaxed.toFixed(2)}</Typography>
                    </Stack>
                    <Stack direction="row" justifyContent="space-between">
                      <Typography variant="body2" color="text.secondary">
                        {t('purchases.taxAmount')}
                      </Typography>
                      <Typography variant="body2">{bd.tax.toFixed(2)}</Typography>
                    </Stack>
                    <Stack direction="row" justifyContent="space-between" sx={{ mt: 0.5 }}>
                      <Typography variant="subtitle2">
                        {t('purchases.totalWithTax')}
                      </Typography>
                      <Typography variant="subtitle2">{bd.total.toFixed(2)}</Typography>
                    </Stack>
                  </Box>
                )
              })()}
            </Stack>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDetail(null)}>{t('common.close')}</Button>
        </DialogActions>
      </Dialog>

      <Dialog open={Boolean(actionTarget)} onClose={() => setActionTarget(null)}>
        <DialogTitle>
          {actionTarget?.action === 'receive'
            ? t('purchases.confirmReceive')
            : t('purchases.confirmCancel')}
        </DialogTitle>
        <DialogContent>
          <Typography>
            {actionTarget?.action === 'receive'
              ? t('purchases.receiveHint', { po: actionTarget?.row.po_number })
              : t('purchases.cancelHint', { po: actionTarget?.row.po_number })}
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setActionTarget(null)}>{t('common.cancel')}</Button>
          <Button
            onClick={handleAction}
            variant="contained"
            color={actionTarget?.action === 'receive' ? 'success' : 'error'}
            disabled={actionRunning}
          >
            {actionRunning ? t('common.loading') : t('common.confirm')}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}

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
  Typography,
} from '@mui/material'
import AddIcon from '@mui/icons-material/Add'

import * as adjApi from '@/api/stockAdjustments'
import * as productsApi from '@/api/products'
import { useAuth } from '@/contexts/AuthContext'

const REASONS = [
  { value: 'surplus',  i18n: 'reasonSurplus',  color: 'success' },
  { value: 'shortage', i18n: 'reasonShortage', color: 'warning' },
  { value: 'scrap',    i18n: 'reasonScrap',    color: 'error' },
  { value: 'other',    i18n: 'reasonOther',    color: 'default' },
]

function formatDateTime(value) {
  if (!value) return '—'
  try {
    return new Date(value).toLocaleString()
  } catch {
    return value
  }
}

function newEmptyForm() {
  return { product_id: '', change_qty: '', reason: 'shortage', notes: '' }
}

export default function StockAdjustmentsPage() {
  const { t } = useTranslation()
  const { hasRole } = useAuth()
  const canWrite = hasRole('admin', 'manager', 'warehouse')

  const [rows, setRows] = useState([])
  const [products, setProducts] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [reloadToken, setReloadToken] = useState(0)

  const [filterReason, setFilterReason] = useState('')
  const [filterProduct, setFilterProduct] = useState('')
  const [search, setSearch] = useState('')

  const [editor, setEditor] = useState({ open: false })
  const [form, setForm] = useState(newEmptyForm())
  const [submitting, setSubmitting] = useState(false)
  const [submitError, setSubmitError] = useState(null)

  const productMap = useMemo(
    () => Object.fromEntries(products.map((p) => [p.id, p])),
    [products],
  )

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      setLoading(true)
      try {
        const params = {}
        if (search.trim()) params.search = search.trim()
        if (filterReason) params.reason = filterReason
        if (filterProduct) params.product_id = filterProduct
        const [adjs, prods] = await Promise.all([
          adjApi.listAdjustments(params),
          productsApi.listProducts({ is_active: true, limit: 1000 }),
        ])
        if (!cancelled) {
          setRows(adjs)
          setProducts(prods)
          setError(null)
        }
      } catch (err) {
        if (!cancelled) setError(err.response?.data?.detail || err.message)
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()
    return () => { cancelled = true }
  }, [reloadToken, search, filterReason, filterProduct])

  const reload = () => setReloadToken((tk) => tk + 1)

  const openCreate = () => {
    setForm(newEmptyForm())
    setSubmitError(null)
    setEditor({ open: true })
  }
  const closeEditor = () => setEditor({ open: false })

  const selectedProduct = productMap[Number(form.product_id)]
  const currentStock = selectedProduct?.stock_quantity ?? null
  const changeNum = Number(form.change_qty)
  const previewAfter = currentStock !== null && form.change_qty !== '' && !Number.isNaN(changeNum)
    ? currentStock + changeNum
    : null
  const wouldGoNegative = previewAfter !== null && previewAfter < 0

  const handleSubmit = async (event) => {
    event.preventDefault()
    if (!form.product_id) {
      setSubmitError(t('adjustments.errors.productRequired'))
      return
    }
    if (form.change_qty === '' || changeNum === 0 || Number.isNaN(changeNum)) {
      setSubmitError(t('adjustments.errors.changeRequired'))
      return
    }
    if (wouldGoNegative) {
      setSubmitError(t('adjustments.errors.wouldGoNegative', { after: previewAfter }))
      return
    }
    setSubmitting(true)
    setSubmitError(null)
    try {
      await adjApi.createAdjustment({
        product_id: Number(form.product_id),
        change_qty: changeNum,
        reason: form.reason,
        notes: form.notes.trim() || null,
      })
      closeEditor()
      reload()
    } catch (err) {
      setSubmitError(err.response?.data?.detail || err.message)
    } finally {
      setSubmitting(false)
    }
  }

  const reasonChip = (reasonValue) => {
    const r = REASONS.find((x) => x.value === reasonValue)
    if (!r) return reasonValue
    return (
      <Chip
        size="small"
        label={t(`adjustments.${r.i18n}`)}
        color={r.color}
        variant={r.color === 'default' ? 'outlined' : 'filled'}
      />
    )
  }

  const colSpan = 8

  return (
    <Box>
      <Stack direction="row" justifyContent="space-between" alignItems="center" mb={2}>
        <Typography variant="h4">{t('nav.adjustments')}</Typography>
        {canWrite && (
          <Button
            variant="contained"
            size="small"
            startIcon={<AddIcon />}
            onClick={openCreate}
            sx={{ ml: 'auto' }}
          >
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
            placeholder={t('adjustments.searchPlaceholder')}
            size="small"
            sx={{ flexGrow: 1 }}
          />
          <FormControl size="small" sx={{ minWidth: 200 }}>
            <InputLabel>{t('adjustments.product')}</InputLabel>
            <Select
              label={t('adjustments.product')}
              value={filterProduct}
              onChange={(e) => setFilterProduct(e.target.value)}
            >
              <MenuItem value="">{t('common.all')}</MenuItem>
              {products.map((p) => (
                <MenuItem key={p.id} value={p.id}>
                  {p.sku} — {p.name}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          <FormControl size="small" sx={{ minWidth: 140 }}>
            <InputLabel>{t('adjustments.reason')}</InputLabel>
            <Select
              label={t('adjustments.reason')}
              value={filterReason}
              onChange={(e) => setFilterReason(e.target.value)}
            >
              <MenuItem value="">{t('common.all')}</MenuItem>
              {REASONS.map((r) => (
                <MenuItem key={r.value} value={r.value}>
                  {t(`adjustments.${r.i18n}`)}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
        </Stack>
      </Paper>

      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

      <TableContainer component={Paper}>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>{t('adjustments.adjNumber')}</TableCell>
              <TableCell>{t('adjustments.product')}</TableCell>
              <TableCell align="right">{t('adjustments.before')}</TableCell>
              <TableCell align="right">{t('adjustments.change')}</TableCell>
              <TableCell align="right">{t('adjustments.after')}</TableCell>
              <TableCell>{t('adjustments.reason')}</TableCell>
              <TableCell>{t('adjustments.operator')}</TableCell>
              <TableCell>{t('adjustments.adjustedAt')}</TableCell>
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
                const isPositive = row.change_qty > 0
                return (
                  <TableRow key={row.id} hover>
                    <TableCell>{row.adjustment_number}</TableCell>
                    <TableCell>
                      {row.product?.sku} — {row.product?.name}
                    </TableCell>
                    <TableCell align="right">{row.before_qty}</TableCell>
                    <TableCell align="right">
                      <Typography
                        component="span"
                        sx={{ color: isPositive ? 'success.main' : 'error.main', fontWeight: 600 }}
                      >
                        {isPositive ? `+${row.change_qty}` : row.change_qty}
                      </Typography>
                    </TableCell>
                    <TableCell align="right">{row.after_qty}</TableCell>
                    <TableCell>{reasonChip(row.reason)}</TableCell>
                    <TableCell>{row.operator?.full_name || row.operator?.username}</TableCell>
                    <TableCell>{formatDateTime(row.adjusted_at)}</TableCell>
                  </TableRow>
                )
              })
            )}
          </TableBody>
        </Table>
      </TableContainer>

      <Dialog open={editor.open} onClose={closeEditor} fullWidth maxWidth="sm">
        <Box component="form" onSubmit={handleSubmit}>
          <DialogTitle>{t('adjustments.createTitle')}</DialogTitle>
          <DialogContent>
            <Stack spacing={2} sx={{ mt: 1 }}>
              {submitError && <Alert severity="error">{submitError}</Alert>}

              <FormControl fullWidth required>
                <InputLabel>{t('adjustments.product')}</InputLabel>
                <Select
                  label={t('adjustments.product')}
                  value={form.product_id}
                  onChange={(e) => setForm({ ...form, product_id: e.target.value })}
                >
                  {products.map((p) => (
                    <MenuItem key={p.id} value={String(p.id)}>
                      {p.sku} — {p.name}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>

              {selectedProduct && (
                <Stack direction="row" spacing={3}>
                  <Box>
                    <Typography variant="caption" color="text.secondary">
                      {t('adjustments.currentStock')}
                    </Typography>
                    <Typography variant="subtitle1">{currentStock} {selectedProduct.unit}</Typography>
                  </Box>
                  {previewAfter !== null && (
                    <Box>
                      <Typography variant="caption" color="text.secondary">
                        {t('adjustments.afterPreview')}
                      </Typography>
                      <Typography
                        variant="subtitle1"
                        sx={{ color: wouldGoNegative ? 'error.main' : 'text.primary' }}
                      >
                        {previewAfter} {selectedProduct.unit}
                      </Typography>
                    </Box>
                  )}
                </Stack>
              )}

              <TextField
                label={t('adjustments.change')}
                type="number"
                value={form.change_qty}
                onChange={(e) => setForm({ ...form, change_qty: e.target.value })}
                helperText={t('adjustments.changeHint')}
                required
                inputProps={{ step: 1 }}
                fullWidth
              />

              <FormControl fullWidth required>
                <InputLabel>{t('adjustments.reason')}</InputLabel>
                <Select
                  label={t('adjustments.reason')}
                  value={form.reason}
                  onChange={(e) => setForm({ ...form, reason: e.target.value })}
                >
                  {REASONS.map((r) => (
                    <MenuItem key={r.value} value={r.value}>
                      {t(`adjustments.${r.i18n}`)}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>

              <TextField
                label={t('adjustments.notes')}
                value={form.notes}
                onChange={(e) => setForm({ ...form, notes: e.target.value })}
                multiline
                rows={2}
                fullWidth
              />
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
    </Box>
  )
}

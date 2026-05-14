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
import DeleteIcon from '@mui/icons-material/Delete'

import * as productsApi from '@/api/products'
import * as categoriesApi from '@/api/categories'
import { useAuth } from '@/contexts/AuthContext'

const EMPTY_FORM = {
  sku: '',
  name: '',
  barcode: '',
  description: '',
  unit: '個',
  unit_price: '0',
  cost_price: '0',
  low_stock_threshold: '0',
  category_id: '',
  is_active: true,
}

const NONE_CATEGORY = '__none__'

function toFormValues(product) {
  return {
    sku: product.sku || '',
    name: product.name || '',
    barcode: product.barcode || '',
    description: product.description || '',
    unit: product.unit || '個',
    unit_price: String(product.unit_price ?? '0'),
    cost_price: String(product.cost_price ?? '0'),
    low_stock_threshold: String(product.low_stock_threshold ?? '0'),
    category_id: product.category_id ? String(product.category_id) : '',
    is_active: Boolean(product.is_active),
  }
}

function toPayload(form) {
  return {
    sku: form.sku.trim(),
    name: form.name.trim(),
    barcode: form.barcode.trim() || null,
    description: form.description.trim() || null,
    unit: form.unit.trim() || '個',
    unit_price: form.unit_price || '0',
    cost_price: form.cost_price || '0',
    low_stock_threshold: Number(form.low_stock_threshold) || 0,
    category_id: form.category_id ? Number(form.category_id) : null,
    is_active: form.is_active,
  }
}

export default function ProductsPage() {
  const { t } = useTranslation()
  const { hasRole } = useAuth()
  const canWrite = hasRole('admin', 'manager')

  const [rows, setRows] = useState([])
  const [categories, setCategories] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [reloadToken, setReloadToken] = useState(0)

  const [search, setSearch] = useState('')
  const [filterCategory, setFilterCategory] = useState('')
  const [filterActive, setFilterActive] = useState('')

  const [dialog, setDialog] = useState({ open: false, mode: 'create', id: null })
  const [form, setForm] = useState(EMPTY_FORM)
  const [submitting, setSubmitting] = useState(false)
  const [submitError, setSubmitError] = useState(null)

  const [deleteTarget, setDeleteTarget] = useState(null)
  const [deleting, setDeleting] = useState(false)

  const categoryMap = useMemo(
    () => Object.fromEntries(categories.map((c) => [c.id, c])),
    [categories],
  )

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      try {
        const params = {}
        if (search.trim()) params.search = search.trim()
        if (filterCategory) params.category_id = filterCategory
        if (filterActive !== '') params.is_active = filterActive === 'true'
        const [products, cats] = await Promise.all([
          productsApi.listProducts(params),
          categoriesApi.listCategories(),
        ])
        if (!cancelled) {
          setRows(products)
          setCategories(cats)
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
  }, [reloadToken, search, filterCategory, filterActive])

  const reload = () => setReloadToken((t) => t + 1)

  const openCreate = () => {
    setForm(EMPTY_FORM)
    setSubmitError(null)
    setDialog({ open: true, mode: 'create', id: null })
  }

  const openEdit = (row) => {
    setForm(toFormValues(row))
    setSubmitError(null)
    setDialog({ open: true, mode: 'edit', id: row.id })
  }

  const closeDialog = () => setDialog((d) => ({ ...d, open: false }))

  const handleSubmit = async (event) => {
    event.preventDefault()
    setSubmitting(true)
    setSubmitError(null)
    try {
      const payload = toPayload(form)
      if (dialog.mode === 'create') {
        await productsApi.createProduct(payload)
      } else {
        await productsApi.updateProduct(dialog.id, payload)
      }
      closeDialog()
      await reload()
    } catch (err) {
      setSubmitError(err.response?.data?.detail || err.message)
    } finally {
      setSubmitting(false)
    }
  }

  const handleDelete = async () => {
    if (!deleteTarget) return
    setDeleting(true)
    try {
      await productsApi.deleteProduct(deleteTarget.id)
      setDeleteTarget(null)
      await reload()
    } catch (err) {
      setError(err.response?.data?.detail || err.message)
      setDeleteTarget(null)
    } finally {
      setDeleting(false)
    }
  }

  const colSpan = canWrite ? 8 : 7

  return (
    <Box>
      <Stack direction="row" justifyContent="space-between" alignItems="center" mb={2}>
        <Typography variant="h4">{t('nav.products')}</Typography>
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
            placeholder={t('products.searchPlaceholder')}
            size="small"
            sx={{ flexGrow: 1 }}
          />
          <FormControl size="small" sx={{ minWidth: 180 }}>
            <InputLabel>{t('products.category')}</InputLabel>
            <Select
              label={t('products.category')}
              value={filterCategory}
              onChange={(e) => setFilterCategory(e.target.value)}
            >
              <MenuItem value="">{t('common.all')}</MenuItem>
              {categories.map((c) => (
                <MenuItem key={c.id} value={c.id}>
                  {c.name}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          <FormControl size="small" sx={{ minWidth: 140 }}>
            <InputLabel>{t('products.status')}</InputLabel>
            <Select
              label={t('products.status')}
              value={filterActive}
              onChange={(e) => setFilterActive(e.target.value)}
            >
              <MenuItem value="">{t('common.all')}</MenuItem>
              <MenuItem value="true">{t('products.active')}</MenuItem>
              <MenuItem value="false">{t('products.inactive')}</MenuItem>
            </Select>
          </FormControl>
        </Stack>
      </Paper>

      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

      <TableContainer component={Paper}>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>{t('products.sku')}</TableCell>
              <TableCell>{t('products.name')}</TableCell>
              <TableCell>{t('products.category')}</TableCell>
              <TableCell>{t('products.unit')}</TableCell>
              <TableCell align="right">{t('products.unitPrice')}</TableCell>
              <TableCell align="right">{t('products.stock')}</TableCell>
              <TableCell>{t('products.status')}</TableCell>
              {canWrite && <TableCell align="right">{t('common.actions')}</TableCell>}
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
              rows.map((row) => (
                <TableRow key={row.id} hover>
                  <TableCell>{row.sku}</TableCell>
                  <TableCell>{row.name}</TableCell>
                  <TableCell>{row.category?.name || categoryMap[row.category_id]?.name || '—'}</TableCell>
                  <TableCell>{row.unit}</TableCell>
                  <TableCell align="right">{row.unit_price}</TableCell>
                  <TableCell align="right">
                    <Stack direction="row" spacing={0.5} justifyContent="flex-end" alignItems="center">
                      <span>{row.stock_quantity}</span>
                      {row.low_stock_threshold > 0 && row.stock_quantity <= row.low_stock_threshold && (
                        <Chip size="small" label={t('products.lowStockBadge')} color="warning" />
                      )}
                    </Stack>
                  </TableCell>
                  <TableCell>
                    <Chip
                      size="small"
                      label={row.is_active ? t('products.active') : t('products.inactive')}
                      color={row.is_active ? 'success' : 'default'}
                    />
                  </TableCell>
                  {canWrite && (
                    <TableCell align="right">
                      <Tooltip title={t('common.edit')}>
                        <IconButton size="small" onClick={() => openEdit(row)}>
                          <EditIcon fontSize="small" />
                        </IconButton>
                      </Tooltip>
                      <Tooltip title={t('common.delete')}>
                        <IconButton size="small" onClick={() => setDeleteTarget(row)}>
                          <DeleteIcon fontSize="small" />
                        </IconButton>
                      </Tooltip>
                    </TableCell>
                  )}
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </TableContainer>

      <Dialog open={dialog.open} onClose={closeDialog} fullWidth maxWidth="sm">
        <Box component="form" onSubmit={handleSubmit}>
          <DialogTitle>
            {dialog.mode === 'create' ? t('products.createTitle') : t('products.editTitle')}
          </DialogTitle>
          <DialogContent>
            <Stack spacing={2} sx={{ mt: 1 }}>
              {submitError && <Alert severity="error">{submitError}</Alert>}
              <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2}>
                <TextField
                  label={t('products.sku')}
                  value={form.sku}
                  onChange={(e) => setForm({ ...form, sku: e.target.value })}
                  required
                  fullWidth
                />
                <TextField
                  label={t('products.barcode')}
                  value={form.barcode}
                  onChange={(e) => setForm({ ...form, barcode: e.target.value })}
                  fullWidth
                />
              </Stack>
              <TextField
                label={t('products.name')}
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                required
                fullWidth
              />
              <TextField
                label={t('products.description')}
                value={form.description}
                onChange={(e) => setForm({ ...form, description: e.target.value })}
                multiline
                rows={2}
                fullWidth
              />
              <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2}>
                <FormControl fullWidth>
                  <InputLabel>{t('products.category')}</InputLabel>
                  <Select
                    label={t('products.category')}
                    value={form.category_id === '' ? NONE_CATEGORY : form.category_id}
                    onChange={(e) =>
                      setForm({
                        ...form,
                        category_id: e.target.value === NONE_CATEGORY ? '' : e.target.value,
                      })
                    }
                  >
                    <MenuItem value={NONE_CATEGORY}>{t('common.none')}</MenuItem>
                    {categories.map((c) => (
                      <MenuItem key={c.id} value={String(c.id)}>
                        {c.name}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
                <TextField
                  label={t('products.unit')}
                  value={form.unit}
                  onChange={(e) => setForm({ ...form, unit: e.target.value })}
                  required
                  sx={{ minWidth: 120 }}
                />
              </Stack>
              <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2}>
                <TextField
                  label={t('products.unitPrice')}
                  type="number"
                  inputProps={{ min: 0, step: '0.01' }}
                  value={form.unit_price}
                  onChange={(e) => setForm({ ...form, unit_price: e.target.value })}
                  required
                  fullWidth
                />
                <TextField
                  label={t('products.costPrice')}
                  type="number"
                  inputProps={{ min: 0, step: '0.01' }}
                  value={form.cost_price}
                  onChange={(e) => setForm({ ...form, cost_price: e.target.value })}
                  required
                  fullWidth
                />
              </Stack>
              <TextField
                label={t('products.lowStockThreshold')}
                type="number"
                inputProps={{ min: 0, step: 1 }}
                value={form.low_stock_threshold}
                onChange={(e) => setForm({ ...form, low_stock_threshold: e.target.value })}
                helperText={t('products.lowStockHint')}
                fullWidth
              />
              <FormControlLabel
                control={
                  <Switch
                    checked={form.is_active}
                    onChange={(e) => setForm({ ...form, is_active: e.target.checked })}
                  />
                }
                label={t('products.active')}
              />
              {dialog.mode === 'edit' && (
                <Typography variant="caption" color="text.secondary">
                  {t('products.stockReadOnlyHint')}
                </Typography>
              )}
            </Stack>
          </DialogContent>
          <DialogActions>
            <Button onClick={closeDialog}>{t('common.cancel')}</Button>
            <Button type="submit" variant="contained" disabled={submitting}>
              {submitting ? t('common.loading') : t('common.save')}
            </Button>
          </DialogActions>
        </Box>
      </Dialog>

      <Dialog open={Boolean(deleteTarget)} onClose={() => setDeleteTarget(null)}>
        <DialogTitle>{t('common.confirmDelete')}</DialogTitle>
        <DialogContent>
          <Typography>
            {t('products.deleteConfirm', { name: deleteTarget?.name })}
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteTarget(null)}>{t('common.cancel')}</Button>
          <Button onClick={handleDelete} color="error" variant="contained" disabled={deleting}>
            {deleting ? t('common.loading') : t('common.delete')}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}

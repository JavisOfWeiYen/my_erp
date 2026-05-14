import { useEffect, useState } from 'react'
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

import * as suppliersApi from '@/api/suppliers'
import { useAuth } from '@/contexts/AuthContext'

const EMPTY_FORM = {
  name: '',
  contact_name: '',
  phone: '',
  email: '',
  address: '',
  tax_id: '',
  notes: '',
  is_active: true,
}

function toFormValues(supplier) {
  return {
    name: supplier.name || '',
    contact_name: supplier.contact_name || '',
    phone: supplier.phone || '',
    email: supplier.email || '',
    address: supplier.address || '',
    tax_id: supplier.tax_id || '',
    notes: supplier.notes || '',
    is_active: Boolean(supplier.is_active),
  }
}

function toPayload(form) {
  return {
    name: form.name.trim(),
    contact_name: form.contact_name.trim() || null,
    phone: form.phone.trim() || null,
    email: form.email.trim() || null,
    address: form.address.trim() || null,
    tax_id: form.tax_id.trim() || null,
    notes: form.notes.trim() || null,
    is_active: form.is_active,
  }
}

export default function SuppliersPage() {
  const { t } = useTranslation()
  const { hasRole } = useAuth()
  const canWrite = hasRole('admin', 'manager')

  const [rows, setRows] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [reloadToken, setReloadToken] = useState(0)

  const [search, setSearch] = useState('')
  const [filterActive, setFilterActive] = useState('')

  const [dialog, setDialog] = useState({ open: false, mode: 'create', id: null })
  const [form, setForm] = useState(EMPTY_FORM)
  const [submitting, setSubmitting] = useState(false)
  const [submitError, setSubmitError] = useState(null)

  const [deleteTarget, setDeleteTarget] = useState(null)
  const [deleting, setDeleting] = useState(false)

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      try {
        const params = {}
        if (search.trim()) params.search = search.trim()
        if (filterActive !== '') params.is_active = filterActive === 'true'
        const data = await suppliersApi.listSuppliers(params)
        if (!cancelled) {
          setRows(data)
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
  }, [reloadToken, search, filterActive])

  const reload = () => setReloadToken((tk) => tk + 1)

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
        await suppliersApi.createSupplier(payload)
      } else {
        await suppliersApi.updateSupplier(dialog.id, payload)
      }
      closeDialog()
      reload()
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
      await suppliersApi.deleteSupplier(deleteTarget.id)
      setDeleteTarget(null)
      reload()
    } catch (err) {
      setError(err.response?.data?.detail || err.message)
      setDeleteTarget(null)
    } finally {
      setDeleting(false)
    }
  }

  const colSpan = canWrite ? 7 : 6

  return (
    <Box>
      <Stack direction="row" justifyContent="space-between" alignItems="center" mb={2}>
        <Typography variant="h4">{t('nav.suppliers')}</Typography>
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
            placeholder={t('suppliers.searchPlaceholder')}
            size="small"
            sx={{ flexGrow: 1 }}
          />
          <FormControl size="small" sx={{ minWidth: 140 }}>
            <InputLabel>{t('suppliers.status')}</InputLabel>
            <Select
              label={t('suppliers.status')}
              value={filterActive}
              onChange={(e) => setFilterActive(e.target.value)}
            >
              <MenuItem value="">{t('common.all')}</MenuItem>
              <MenuItem value="true">{t('suppliers.active')}</MenuItem>
              <MenuItem value="false">{t('suppliers.inactive')}</MenuItem>
            </Select>
          </FormControl>
        </Stack>
      </Paper>

      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

      <TableContainer component={Paper}>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>{t('suppliers.name')}</TableCell>
              <TableCell>{t('suppliers.contactName')}</TableCell>
              <TableCell>{t('suppliers.phone')}</TableCell>
              <TableCell>{t('suppliers.email')}</TableCell>
              <TableCell>{t('suppliers.taxId')}</TableCell>
              <TableCell>{t('suppliers.status')}</TableCell>
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
                  <TableCell>{row.name}</TableCell>
                  <TableCell>{row.contact_name || '—'}</TableCell>
                  <TableCell>{row.phone || '—'}</TableCell>
                  <TableCell>{row.email || '—'}</TableCell>
                  <TableCell>{row.tax_id || '—'}</TableCell>
                  <TableCell>
                    <Chip
                      size="small"
                      label={row.is_active ? t('suppliers.active') : t('suppliers.inactive')}
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
            {dialog.mode === 'create' ? t('suppliers.createTitle') : t('suppliers.editTitle')}
          </DialogTitle>
          <DialogContent>
            <Stack spacing={2} sx={{ mt: 1 }}>
              {submitError && <Alert severity="error">{submitError}</Alert>}
              <TextField
                label={t('suppliers.name')}
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                required
                fullWidth
              />
              <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2}>
                <TextField
                  label={t('suppliers.contactName')}
                  value={form.contact_name}
                  onChange={(e) => setForm({ ...form, contact_name: e.target.value })}
                  fullWidth
                />
                <TextField
                  label={t('suppliers.phone')}
                  value={form.phone}
                  onChange={(e) => setForm({ ...form, phone: e.target.value })}
                  fullWidth
                />
              </Stack>
              <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2}>
                <TextField
                  label={t('suppliers.email')}
                  type="email"
                  value={form.email}
                  onChange={(e) => setForm({ ...form, email: e.target.value })}
                  fullWidth
                />
                <TextField
                  label={t('suppliers.taxId')}
                  value={form.tax_id}
                  onChange={(e) => setForm({ ...form, tax_id: e.target.value })}
                  fullWidth
                />
              </Stack>
              <TextField
                label={t('suppliers.address')}
                value={form.address}
                onChange={(e) => setForm({ ...form, address: e.target.value })}
                fullWidth
              />
              <TextField
                label={t('suppliers.notes')}
                value={form.notes}
                onChange={(e) => setForm({ ...form, notes: e.target.value })}
                multiline
                rows={2}
                fullWidth
              />
              <FormControlLabel
                control={
                  <Switch
                    checked={form.is_active}
                    onChange={(e) => setForm({ ...form, is_active: e.target.checked })}
                  />
                }
                label={t('suppliers.active')}
              />
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
            {t('suppliers.deleteConfirm', { name: deleteTarget?.name })}
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

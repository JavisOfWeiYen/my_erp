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

import * as usersApi from '@/api/users'
import * as rolesApi from '@/api/roles'
import { useAuth } from '@/contexts/AuthContext'

function emptyCreateForm() {
  return {
    username: '',
    email: '',
    full_name: '',
    password: '',
    role_id: '',
    is_active: true,
  }
}

function emptyEditForm() {
  return {
    email: '',
    full_name: '',
    password: '',
    role_id: '',
    is_active: true,
  }
}

function toEditFormValues(user) {
  return {
    email: user.email || '',
    full_name: user.full_name || '',
    password: '',
    role_id: user.role_id ? String(user.role_id) : (user.role?.id ? String(user.role.id) : ''),
    is_active: Boolean(user.is_active),
  }
}

function createPayload(form) {
  return {
    username: form.username.trim(),
    email: form.email.trim(),
    full_name: form.full_name.trim() || null,
    password: form.password,
    role_id: Number(form.role_id),
    is_active: form.is_active,
  }
}

function editPayload(form) {
  const payload = {
    email: form.email.trim(),
    full_name: form.full_name.trim() || null,
    role_id: Number(form.role_id),
    is_active: form.is_active,
  }
  if (form.password) payload.password = form.password
  return payload
}

export default function UsersPage() {
  const { t } = useTranslation()
  const { user: currentUser } = useAuth()

  const [rows, setRows] = useState([])
  const [roles, setRoles] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [reloadToken, setReloadToken] = useState(0)

  const [search, setSearch] = useState('')
  const [filterRole, setFilterRole] = useState('')
  const [filterActive, setFilterActive] = useState('')

  const [dialog, setDialog] = useState({ open: false, mode: 'create', id: null })
  const [createForm, setCreateForm] = useState(emptyCreateForm())
  const [editForm, setEditForm] = useState(emptyEditForm())
  const [submitting, setSubmitting] = useState(false)
  const [submitError, setSubmitError] = useState(null)

  const [deleteTarget, setDeleteTarget] = useState(null)
  const [deleting, setDeleting] = useState(false)

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      try {
        const [users, rs] = await Promise.all([
          usersApi.listUsers(),
          rolesApi.listRoles(),
        ])
        if (!cancelled) {
          setRows(users)
          setRoles(rs)
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
  }, [reloadToken])

  const reload = () => setReloadToken((tk) => tk + 1)

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase()
    return rows.filter((u) => {
      if (q) {
        const hay = `${u.username} ${u.email} ${u.full_name || ''}`.toLowerCase()
        if (!hay.includes(q)) return false
      }
      if (filterRole && u.role?.id !== Number(filterRole)) return false
      if (filterActive !== '' && u.is_active !== (filterActive === 'true')) return false
      return true
    })
  }, [rows, search, filterRole, filterActive])

  const openCreate = () => {
    setCreateForm(emptyCreateForm())
    setSubmitError(null)
    setDialog({ open: true, mode: 'create', id: null })
  }

  const openEdit = (row) => {
    setEditForm(toEditFormValues(row))
    setSubmitError(null)
    setDialog({ open: true, mode: 'edit', id: row.id })
  }

  const closeDialog = () => setDialog((d) => ({ ...d, open: false }))

  const handleSubmit = async (event) => {
    event.preventDefault()
    const isCreate = dialog.mode === 'create'
    const form = isCreate ? createForm : editForm
    if (!form.role_id) {
      setSubmitError(t('users.errors.roleRequired'))
      return
    }
    setSubmitting(true)
    setSubmitError(null)
    try {
      if (isCreate) {
        await usersApi.createUser(createPayload(form))
      } else {
        await usersApi.updateUser(dialog.id, editPayload(form))
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
      await usersApi.deleteUser(deleteTarget.id)
      setDeleteTarget(null)
      reload()
    } catch (err) {
      setError(err.response?.data?.detail || err.message)
      setDeleteTarget(null)
    } finally {
      setDeleting(false)
    }
  }

  const colSpan = 6

  return (
    <Box>
      <Stack direction="row" justifyContent="space-between" alignItems="center" mb={2}>
        <Typography variant="h4">{t('nav.users')}</Typography>
        <Button variant="contained" size="small" startIcon={<AddIcon />} onClick={openCreate} sx={{ ml: 'auto' }}>
          {t('common.create')}
        </Button>
      </Stack>

      <Paper sx={{ p: 2, mb: 2 }}>
        <Stack direction={{ xs: 'column', md: 'row' }} spacing={2}>
          <TextField
            label={t('common.search')}
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder={t('users.searchPlaceholder')}
            size="small"
            sx={{ flexGrow: 1 }}
          />
          <FormControl size="small" sx={{ minWidth: 160 }}>
            <InputLabel>{t('users.role')}</InputLabel>
            <Select
              label={t('users.role')}
              value={filterRole}
              onChange={(e) => setFilterRole(e.target.value)}
            >
              <MenuItem value="">{t('common.all')}</MenuItem>
              {roles.map((r) => (
                <MenuItem key={r.id} value={r.id}>
                  {t(`roles.${r.name}`, r.name)}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          <FormControl size="small" sx={{ minWidth: 140 }}>
            <InputLabel>{t('users.status')}</InputLabel>
            <Select
              label={t('users.status')}
              value={filterActive}
              onChange={(e) => setFilterActive(e.target.value)}
            >
              <MenuItem value="">{t('common.all')}</MenuItem>
              <MenuItem value="true">{t('users.active')}</MenuItem>
              <MenuItem value="false">{t('users.inactive')}</MenuItem>
            </Select>
          </FormControl>
        </Stack>
      </Paper>

      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

      <TableContainer component={Paper}>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>{t('users.username')}</TableCell>
              <TableCell>{t('users.fullName')}</TableCell>
              <TableCell>{t('users.email')}</TableCell>
              <TableCell>{t('users.role')}</TableCell>
              <TableCell>{t('users.status')}</TableCell>
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
            ) : filtered.length === 0 ? (
              <TableRow>
                <TableCell colSpan={colSpan} align="center">
                  <Typography color="text.secondary">{t('common.noData')}</Typography>
                </TableCell>
              </TableRow>
            ) : (
              filtered.map((row) => {
                const isSelf = currentUser?.id === row.id
                return (
                  <TableRow key={row.id} hover>
                    <TableCell>
                      {row.username}
                      {isSelf && (
                        <Chip
                          size="small"
                          label={t('users.youBadge')}
                          color="primary"
                          variant="outlined"
                          sx={{ ml: 1 }}
                        />
                      )}
                    </TableCell>
                    <TableCell>{row.full_name || '—'}</TableCell>
                    <TableCell>{row.email}</TableCell>
                    <TableCell>{t(`roles.${row.role?.name}`, row.role?.name)}</TableCell>
                    <TableCell>
                      <Chip
                        size="small"
                        label={row.is_active ? t('users.active') : t('users.inactive')}
                        color={row.is_active ? 'success' : 'default'}
                      />
                    </TableCell>
                    <TableCell align="right">
                      <Tooltip title={t('common.edit')}>
                        <IconButton size="small" onClick={() => openEdit(row)}>
                          <EditIcon fontSize="small" />
                        </IconButton>
                      </Tooltip>
                      <Tooltip title={isSelf ? t('users.cannotDeleteSelf') : t('common.delete')}>
                        <span>
                          <IconButton
                            size="small"
                            disabled={isSelf}
                            onClick={() => setDeleteTarget(row)}
                          >
                            <DeleteIcon fontSize="small" />
                          </IconButton>
                        </span>
                      </Tooltip>
                    </TableCell>
                  </TableRow>
                )
              })
            )}
          </TableBody>
        </Table>
      </TableContainer>

      <Dialog open={dialog.open} onClose={closeDialog} fullWidth maxWidth="sm">
        <Box component="form" onSubmit={handleSubmit}>
          <DialogTitle>
            {dialog.mode === 'create' ? t('users.createTitle') : t('users.editTitle')}
          </DialogTitle>
          <DialogContent>
            <Stack spacing={2} sx={{ mt: 1 }}>
              {submitError && <Alert severity="error">{submitError}</Alert>}

              {dialog.mode === 'create' && (
                <TextField
                  label={t('users.username')}
                  value={createForm.username}
                  onChange={(e) => setCreateForm({ ...createForm, username: e.target.value })}
                  required
                  inputProps={{ minLength: 3, maxLength: 64 }}
                  fullWidth
                />
              )}

              <TextField
                label={t('users.email')}
                type="email"
                value={dialog.mode === 'create' ? createForm.email : editForm.email}
                onChange={(e) => {
                  if (dialog.mode === 'create') {
                    setCreateForm({ ...createForm, email: e.target.value })
                  } else {
                    setEditForm({ ...editForm, email: e.target.value })
                  }
                }}
                required
                fullWidth
              />

              <TextField
                label={t('users.fullName')}
                value={dialog.mode === 'create' ? createForm.full_name : editForm.full_name}
                onChange={(e) => {
                  if (dialog.mode === 'create') {
                    setCreateForm({ ...createForm, full_name: e.target.value })
                  } else {
                    setEditForm({ ...editForm, full_name: e.target.value })
                  }
                }}
                fullWidth
              />

              <FormControl fullWidth required>
                <InputLabel>{t('users.role')}</InputLabel>
                <Select
                  label={t('users.role')}
                  value={dialog.mode === 'create' ? createForm.role_id : editForm.role_id}
                  onChange={(e) => {
                    if (dialog.mode === 'create') {
                      setCreateForm({ ...createForm, role_id: e.target.value })
                    } else {
                      setEditForm({ ...editForm, role_id: e.target.value })
                    }
                  }}
                >
                  {roles.map((r) => (
                    <MenuItem key={r.id} value={String(r.id)}>
                      {t(`roles.${r.name}`, r.name)}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>

              <TextField
                label={dialog.mode === 'create' ? t('users.password') : t('users.newPassword')}
                type="password"
                value={dialog.mode === 'create' ? createForm.password : editForm.password}
                onChange={(e) => {
                  if (dialog.mode === 'create') {
                    setCreateForm({ ...createForm, password: e.target.value })
                  } else {
                    setEditForm({ ...editForm, password: e.target.value })
                  }
                }}
                required={dialog.mode === 'create'}
                inputProps={{ minLength: 8, maxLength: 128 }}
                helperText={
                  dialog.mode === 'create'
                    ? t('users.passwordHint')
                    : t('users.passwordEditHint')
                }
                fullWidth
              />

              <FormControlLabel
                control={
                  <Switch
                    checked={dialog.mode === 'create' ? createForm.is_active : editForm.is_active}
                    onChange={(e) => {
                      if (dialog.mode === 'create') {
                        setCreateForm({ ...createForm, is_active: e.target.checked })
                      } else {
                        setEditForm({ ...editForm, is_active: e.target.checked })
                      }
                    }}
                  />
                }
                label={t('users.active')}
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
            {t('users.deleteConfirm', { name: deleteTarget?.username })}
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

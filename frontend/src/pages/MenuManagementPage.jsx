import { useEffect, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import {
  Alert,
  Box,
  Button,
  Checkbox,
  Chip,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControl,
  FormControlLabel,
  IconButton,
  InputLabel,
  ListItemIcon,
  ListItemText,
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
import ArrowUpwardIcon from '@mui/icons-material/ArrowUpward'
import ArrowDownwardIcon from '@mui/icons-material/ArrowDownward'

import * as menuApi from '@/api/menu'
import { MenuIcon } from '@/components/iconMap'
import { ICON_NAMES } from '@/components/iconList'

const ROLES = ['admin', 'manager', 'sales', 'warehouse']

const EMPTY_FORM = {
  id: null,
  parent_id: '',
  label_key: '',
  custom_label: '',
  icon_name: '',
  route_path: '',
  required_roles: [], // array of role names; serialized as comma-separated on submit
  display_order: 0,
  is_active: true,
}

function flatten(tree, depth = 0, acc = []) {
  for (const node of tree) {
    acc.push({ ...node, depth })
    if (node.children?.length) flatten(node.children, depth + 1, acc)
  }
  return acc
}

function nodeToForm(node) {
  return {
    id: node.id,
    parent_id: node.parent_id ?? '',
    label_key: node.label_key || '',
    custom_label: node.custom_label || '',
    icon_name: node.icon_name || '',
    route_path: node.route_path || '',
    required_roles: node.required_roles
      ? node.required_roles.split(',').map((r) => r.trim()).filter(Boolean)
      : [],
    display_order: node.display_order ?? 0,
    is_active: Boolean(node.is_active),
  }
}

function formToPayload(form) {
  return {
    parent_id: form.parent_id === '' ? null : Number(form.parent_id),
    label_key: form.label_key.trim() || null,
    custom_label: form.custom_label.trim() || null,
    icon_name: form.icon_name || null,
    route_path: form.route_path.trim() || null,
    required_roles: form.required_roles.length ? form.required_roles.join(',') : null,
    display_order: Number(form.display_order) || 0,
    is_active: form.is_active,
  }
}

export default function MenuManagementPage() {
  const { t } = useTranslation()
  const [tree, setTree] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [reloadToken, setReloadToken] = useState(0)

  const [dialog, setDialog] = useState({ open: false, mode: 'create' })
  const [form, setForm] = useState(EMPTY_FORM)
  const [submitting, setSubmitting] = useState(false)
  const [submitError, setSubmitError] = useState(null)

  const [deleteTarget, setDeleteTarget] = useState(null)

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      try {
        const data = await menuApi.getAdminMenu()
        if (!cancelled) {
          setTree(data)
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

  const reload = () => setReloadToken((t) => t + 1)

  const flat = useMemo(() => flatten(tree), [tree])
  // Pool of nodes that can be a parent — only group nodes (route_path null).
  const groupOptions = useMemo(
    () => flat.filter((n) => !n.route_path),
    [flat],
  )

  const openCreate = (parentId = null) => {
    setForm({ ...EMPTY_FORM, parent_id: parentId ?? '' })
    setSubmitError(null)
    setDialog({ open: true, mode: 'create' })
  }

  const openEdit = (node) => {
    setForm(nodeToForm(node))
    setSubmitError(null)
    setDialog({ open: true, mode: 'edit' })
  }

  const closeDialog = () => setDialog({ open: false, mode: 'create' })

  const handleSubmit = async (event) => {
    event.preventDefault()
    if (!form.label_key.trim() && !form.custom_label.trim()) {
      setSubmitError(t('menuManagement.errors.labelRequired'))
      return
    }
    setSubmitting(true)
    setSubmitError(null)
    try {
      const payload = formToPayload(form)
      if (dialog.mode === 'create') {
        await menuApi.createMenuItem(payload)
      } else {
        await menuApi.updateMenuItem(form.id, payload)
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
    try {
      await menuApi.deleteMenuItem(deleteTarget.id)
      setDeleteTarget(null)
      reload()
    } catch (err) {
      setError(err.response?.data?.detail || err.message)
      setDeleteTarget(null)
    }
  }

  const moveSibling = async (node, direction) => {
    // Find siblings at the same parent level. Swap display_order with the
    // adjacent one. If at boundary, no-op.
    const siblings = flat.filter((n) => n.parent_id === node.parent_id)
    siblings.sort((a, b) => a.display_order - b.display_order || a.id - b.id)
    const idx = siblings.findIndex((s) => s.id === node.id)
    const targetIdx = direction === 'up' ? idx - 1 : idx + 1
    if (targetIdx < 0 || targetIdx >= siblings.length) return
    const other = siblings[targetIdx]
    try {
      await menuApi.reorderMenu([
        { id: node.id, parent_id: node.parent_id, display_order: other.display_order },
        { id: other.id, parent_id: other.parent_id, display_order: node.display_order },
      ])
      reload()
    } catch (err) {
      setError(err.response?.data?.detail || err.message)
    }
  }

  return (
    <Box>
      <Stack direction="row" justifyContent="space-between" alignItems="center" mb={2}>
        <Box>
          <Typography variant="h4">{t('menuManagement.title')}</Typography>
          <Typography variant="body2" color="text.secondary">
            {t('menuManagement.subtitle')}
          </Typography>
        </Box>
        <Stack direction="row" spacing={1}>
          <Button
            variant="outlined"
            size="small"
            startIcon={<AddIcon />}
            onClick={() => openCreate(null)}
          >
            {t('menuManagement.addItem')}
          </Button>
        </Stack>
      </Stack>

      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

      <TableContainer component={Paper}>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>{t('menuManagement.labelKey')} / {t('menuManagement.customLabel')}</TableCell>
              <TableCell>{t('menuManagement.icon')}</TableCell>
              <TableCell>{t('menuManagement.routePath')}</TableCell>
              <TableCell>{t('menuManagement.requiredRoles')}</TableCell>
              <TableCell align="center">{t('menuManagement.active')}</TableCell>
              <TableCell align="right">{t('common.actions')}</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {loading ? (
              <TableRow>
                <TableCell colSpan={6} align="center">
                  <Typography color="text.secondary">{t('common.loading')}</Typography>
                </TableCell>
              </TableRow>
            ) : flat.length === 0 ? (
              <TableRow>
                <TableCell colSpan={6} align="center">
                  <Typography color="text.secondary">{t('common.noData')}</Typography>
                </TableCell>
              </TableRow>
            ) : (
              flat.map((node) => {
                const isGroup = !node.route_path
                const label = node.custom_label || node.label_key || `#${node.id}`
                return (
                  <TableRow key={node.id} hover>
                    <TableCell>
                      <Stack direction="row" alignItems="center" spacing={1} sx={{ pl: node.depth * 2 }}>
                        <MenuIcon name={node.icon_name} fontSize="small" />
                        <Box>
                          <Typography variant="body2" sx={{ fontWeight: isGroup ? 600 : 400 }}>
                            {label}
                          </Typography>
                          {node.custom_label && node.label_key && (
                            <Typography variant="caption" color="text.secondary">
                              {node.label_key}
                            </Typography>
                          )}
                        </Box>
                        {isGroup && (
                          <Chip size="small" label={t('menuManagement.isGroup')} />
                        )}
                      </Stack>
                    </TableCell>
                    <TableCell>
                      <Typography variant="caption" color="text.secondary">
                        {node.icon_name || '—'}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Typography variant="caption">
                        {node.route_path || '—'}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Stack direction="row" spacing={0.5} flexWrap="wrap">
                        {node.required_roles
                          ? node.required_roles.split(',').map((r) => (
                              <Chip key={r} size="small" label={t(`roles.${r.trim()}`, r.trim())} />
                            ))
                          : <Typography variant="caption" color="text.secondary">—</Typography>}
                      </Stack>
                    </TableCell>
                    <TableCell align="center">
                      <Chip
                        size="small"
                        color={node.is_active ? 'success' : 'default'}
                        label={node.is_active ? '✓' : '✗'}
                      />
                    </TableCell>
                    <TableCell align="right">
                      <Tooltip title={t('menuManagement.moveUp')}>
                        <IconButton size="small" onClick={() => moveSibling(node, 'up')}>
                          <ArrowUpwardIcon fontSize="small" />
                        </IconButton>
                      </Tooltip>
                      <Tooltip title={t('menuManagement.moveDown')}>
                        <IconButton size="small" onClick={() => moveSibling(node, 'down')}>
                          <ArrowDownwardIcon fontSize="small" />
                        </IconButton>
                      </Tooltip>
                      {isGroup && (
                        <Tooltip title={t('menuManagement.addChild')}>
                          <IconButton size="small" onClick={() => openCreate(node.id)}>
                            <AddIcon fontSize="small" />
                          </IconButton>
                        </Tooltip>
                      )}
                      <Tooltip title={t('menuManagement.edit')}>
                        <IconButton size="small" onClick={() => openEdit(node)}>
                          <EditIcon fontSize="small" />
                        </IconButton>
                      </Tooltip>
                      <Tooltip title={t('menuManagement.delete')}>
                        <IconButton size="small" onClick={() => setDeleteTarget(node)}>
                          <DeleteIcon fontSize="small" />
                        </IconButton>
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
            {dialog.mode === 'create'
              ? t('menuManagement.createTitle')
              : t('menuManagement.editTitle')}
          </DialogTitle>
          <DialogContent>
            <Stack spacing={2} sx={{ mt: 1 }}>
              {submitError && <Alert severity="error">{submitError}</Alert>}
              <FormControl fullWidth>
                <InputLabel>{t('menuManagement.parent')}</InputLabel>
                <Select
                  label={t('menuManagement.parent')}
                  value={form.parent_id}
                  onChange={(e) => setForm({ ...form, parent_id: e.target.value })}
                >
                  <MenuItem value="">{t('menuManagement.noParent')}</MenuItem>
                  {groupOptions
                    .filter((g) => g.id !== form.id)
                    .map((g) => (
                      <MenuItem key={g.id} value={g.id}>
                        {'  '.repeat(g.depth)}
                        {g.custom_label || g.label_key}
                      </MenuItem>
                    ))}
                </Select>
              </FormControl>
              <TextField
                label={t('menuManagement.labelKey')}
                value={form.label_key}
                onChange={(e) => setForm({ ...form, label_key: e.target.value })}
                helperText={t('menuManagement.labelKeyHint')}
                fullWidth
              />
              <TextField
                label={t('menuManagement.customLabel')}
                value={form.custom_label}
                onChange={(e) => setForm({ ...form, custom_label: e.target.value })}
                helperText={t('menuManagement.customLabelHint')}
                fullWidth
              />
              <FormControl fullWidth>
                <InputLabel>{t('menuManagement.icon')}</InputLabel>
                <Select
                  label={t('menuManagement.icon')}
                  value={form.icon_name}
                  onChange={(e) => setForm({ ...form, icon_name: e.target.value })}
                  renderValue={(value) =>
                    value ? (
                      <Stack direction="row" spacing={1} alignItems="center">
                        <MenuIcon name={value} fontSize="small" />
                        <span>{value}</span>
                      </Stack>
                    ) : (
                      <span style={{ color: '#999' }}>—</span>
                    )
                  }
                >
                  <MenuItem value="">—</MenuItem>
                  {ICON_NAMES.map((name) => (
                    <MenuItem key={name} value={name}>
                      <ListItemIcon>
                        <MenuIcon name={name} fontSize="small" />
                      </ListItemIcon>
                      <ListItemText primary={name} />
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
              <TextField
                label={t('menuManagement.routePath')}
                value={form.route_path}
                onChange={(e) => setForm({ ...form, route_path: e.target.value })}
                helperText={t('menuManagement.routePathHint')}
                fullWidth
              />
              <FormControl fullWidth>
                <InputLabel>{t('menuManagement.requiredRoles')}</InputLabel>
                <Select
                  multiple
                  label={t('menuManagement.requiredRoles')}
                  value={form.required_roles}
                  onChange={(e) =>
                    setForm({
                      ...form,
                      required_roles:
                        typeof e.target.value === 'string'
                          ? e.target.value.split(',')
                          : e.target.value,
                    })
                  }
                  renderValue={(selected) =>
                    selected.length === 0
                      ? '—'
                      : selected.map((r) => t(`roles.${r}`, r)).join(', ')
                  }
                >
                  {ROLES.map((r) => (
                    <MenuItem key={r} value={r}>
                      <Checkbox checked={form.required_roles.includes(r)} />
                      <ListItemText primary={t(`roles.${r}`, r)} />
                    </MenuItem>
                  ))}
                </Select>
                <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5, ml: 1.5 }}>
                  {t('menuManagement.requiredRolesHint')}
                </Typography>
              </FormControl>
              <Stack direction="row" spacing={2}>
                <TextField
                  label={t('menuManagement.displayOrder')}
                  type="number"
                  inputProps={{ min: 0, step: 1 }}
                  value={form.display_order}
                  onChange={(e) => setForm({ ...form, display_order: e.target.value })}
                  sx={{ width: 140 }}
                />
                <FormControlLabel
                  control={
                    <Switch
                      checked={form.is_active}
                      onChange={(e) => setForm({ ...form, is_active: e.target.checked })}
                    />
                  }
                  label={t('menuManagement.active')}
                />
              </Stack>
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
            {t('menuManagement.deleteConfirm', {
              label: deleteTarget?.custom_label || deleteTarget?.label_key || '',
            })}
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteTarget(null)}>{t('common.cancel')}</Button>
          <Button onClick={handleDelete} color="error" variant="contained">
            {t('common.delete')}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}

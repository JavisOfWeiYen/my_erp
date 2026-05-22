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
import PaidIcon from '@mui/icons-material/Paid'

import * as employeesApi from '@/api/employees'
import * as usersApi from '@/api/users'

const DEPARTMENTS = ['sales', 'warehouse', 'accounting', 'management', 'it']
const EMPLOYMENT_TYPES = ['full_time', 'part_time', 'contractor']
const SALARY_REASONS = ['promotion', 'adjustment', 'correction']

const formatMoney = (value) =>
  value == null ? '—' : Number(value).toLocaleString('zh-TW', { minimumFractionDigits: 0 })

function emptyCreateForm() {
  return {
    user_id: '',
    department: 'sales',
    title: '',
    hire_date: new Date().toISOString().slice(0, 10),
    termination_date: '',
    employment_type: 'full_time',
    initial_salary: '',
    notes: '',
  }
}

function emptyEditForm() {
  return {
    user_id: '',
    department: 'sales',
    title: '',
    hire_date: '',
    termination_date: '',
    employment_type: 'full_time',
    notes: '',
  }
}

function toEditFormValues(emp) {
  return {
    user_id: emp.user_id ? String(emp.user_id) : '',
    department: emp.department,
    title: emp.title || '',
    hire_date: emp.hire_date || '',
    termination_date: emp.termination_date || '',
    employment_type: emp.employment_type,
    notes: emp.notes || '',
  }
}

function createPayload(form) {
  return {
    user_id: form.user_id ? Number(form.user_id) : null,
    department: form.department,
    title: form.title.trim(),
    hire_date: form.hire_date,
    termination_date: form.termination_date || null,
    employment_type: form.employment_type,
    initial_salary: form.initial_salary,
    notes: form.notes.trim() || null,
  }
}

function editPayload(form) {
  return {
    user_id: form.user_id ? Number(form.user_id) : null,
    department: form.department,
    title: form.title.trim(),
    hire_date: form.hire_date,
    termination_date: form.termination_date || null,
    employment_type: form.employment_type,
    notes: form.notes.trim() || null,
  }
}

function emptySalaryForm() {
  return {
    effective_date: new Date().toISOString().slice(0, 10),
    amount: '',
    reason: 'adjustment',
    notes: '',
  }
}

export default function EmployeesPage() {
  const { t } = useTranslation()

  const [rows, setRows] = useState([])
  const [allUsers, setAllUsers] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [reloadToken, setReloadToken] = useState(0)

  const [search, setSearch] = useState('')
  const [filterDept, setFilterDept] = useState('')
  const [includeTerminated, setIncludeTerminated] = useState(false)

  const [dialog, setDialog] = useState({ open: false, mode: 'create', id: null })
  const [createForm, setCreateForm] = useState(emptyCreateForm())
  const [editForm, setEditForm] = useState(emptyEditForm())
  const [submitting, setSubmitting] = useState(false)
  const [submitError, setSubmitError] = useState(null)

  const [deleteTarget, setDeleteTarget] = useState(null)
  const [deleting, setDeleting] = useState(false)

  const [salaryTarget, setSalaryTarget] = useState(null)
  const [salaryRecords, setSalaryRecords] = useState([])
  const [salaryLoading, setSalaryLoading] = useState(false)
  const [salaryForm, setSalaryForm] = useState(emptySalaryForm())
  const [salaryError, setSalaryError] = useState(null)
  const [salarySubmitting, setSalarySubmitting] = useState(false)

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      setLoading(true)
      try {
        const [emps, users] = await Promise.all([
          employeesApi.listEmployees({ include_terminated: includeTerminated }),
          usersApi.listUsers(),
        ])
        if (!cancelled) {
          setRows(emps)
          setAllUsers(users)
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
  }, [reloadToken, includeTerminated])

  const reload = () => setReloadToken((tk) => tk + 1)

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase()
    return rows.filter((emp) => {
      if (filterDept && emp.department !== filterDept) return false
      if (q) {
        const hay = `${emp.employee_number} ${emp.title} ${emp.user?.full_name || ''} ${emp.user?.username || ''}`.toLowerCase()
        if (!hay.includes(q)) return false
      }
      return true
    })
  }, [rows, search, filterDept])

  const linkedUserIds = useMemo(() => {
    const s = new Set()
    for (const r of rows) {
      if (r.user_id) s.add(r.user_id)
    }
    return s
  }, [rows])

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
    if (!form.title.trim()) {
      setSubmitError(t('employees.errors.titleRequired'))
      return
    }
    if (isCreate && (!form.initial_salary || Number(form.initial_salary) < 0)) {
      setSubmitError(t('employees.errors.initialSalaryRequired'))
      return
    }
    setSubmitting(true)
    setSubmitError(null)
    try {
      if (isCreate) {
        await employeesApi.createEmployee(createPayload(form))
      } else {
        await employeesApi.updateEmployee(dialog.id, editPayload(form))
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
      await employeesApi.deleteEmployee(deleteTarget.id)
      setDeleteTarget(null)
      reload()
    } catch (err) {
      setError(err.response?.data?.detail || err.message)
      setDeleteTarget(null)
    } finally {
      setDeleting(false)
    }
  }

  const openSalary = async (emp) => {
    setSalaryTarget(emp)
    setSalaryForm(emptySalaryForm())
    setSalaryError(null)
    setSalaryLoading(true)
    try {
      const records = await employeesApi.listSalaryRecords(emp.id)
      setSalaryRecords(records)
    } catch (err) {
      setSalaryError(err.response?.data?.detail || err.message)
      setSalaryRecords([])
    } finally {
      setSalaryLoading(false)
    }
  }

  const closeSalary = () => {
    setSalaryTarget(null)
    setSalaryRecords([])
  }

  const handleAddSalary = async (event) => {
    event.preventDefault()
    if (!salaryTarget) return
    if (!salaryForm.amount || Number(salaryForm.amount) < 0) {
      setSalaryError(t('employees.errors.amountRequired'))
      return
    }
    setSalarySubmitting(true)
    setSalaryError(null)
    try {
      await employeesApi.addSalaryRecord(salaryTarget.id, {
        effective_date: salaryForm.effective_date,
        amount: salaryForm.amount,
        reason: salaryForm.reason,
        notes: salaryForm.notes.trim() || null,
      })
      const records = await employeesApi.listSalaryRecords(salaryTarget.id)
      setSalaryRecords(records)
      setSalaryForm(emptySalaryForm())
      reload()
    } catch (err) {
      setSalaryError(err.response?.data?.detail || err.message)
    } finally {
      setSalarySubmitting(false)
    }
  }

  const form = dialog.mode === 'create' ? createForm : editForm
  const setForm = dialog.mode === 'create' ? setCreateForm : setEditForm

  const colSpan = 8

  return (
    <Box>
      <Stack direction="row" justifyContent="space-between" alignItems="center" mb={2}>
        <Typography variant="h4">{t('nav.employees')}</Typography>
        <Button variant="contained" size="small" startIcon={<AddIcon />} onClick={openCreate} sx={{ ml: 'auto' }}>
          {t('common.create')}
        </Button>
      </Stack>

      <Paper sx={{ p: 2, mb: 2 }}>
        <Stack direction={{ xs: 'column', md: 'row' }} spacing={2} alignItems="center">
          <TextField
            label={t('common.search')}
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder={t('employees.searchPlaceholder')}
            size="small"
            sx={{ flexGrow: 1 }}
          />
          <FormControl size="small" sx={{ minWidth: 160 }}>
            <InputLabel>{t('employees.fields.department')}</InputLabel>
            <Select
              label={t('employees.fields.department')}
              value={filterDept}
              onChange={(e) => setFilterDept(e.target.value)}
            >
              <MenuItem value="">{t('common.all')}</MenuItem>
              {DEPARTMENTS.map((d) => (
                <MenuItem key={d} value={d}>{t(`employees.departments.${d}`)}</MenuItem>
              ))}
            </Select>
          </FormControl>
          <FormControlLabel
            control={
              <Switch
                checked={includeTerminated}
                onChange={(e) => setIncludeTerminated(e.target.checked)}
              />
            }
            label={t('employees.includeTerminated')}
          />
        </Stack>
      </Paper>

      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

      <TableContainer component={Paper}>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>{t('employees.fields.employeeNumber')}</TableCell>
              <TableCell>{t('employees.fields.linkedUser')}</TableCell>
              <TableCell>{t('employees.fields.department')}</TableCell>
              <TableCell>{t('employees.fields.title')}</TableCell>
              <TableCell>{t('employees.fields.hireDate')}</TableCell>
              <TableCell align="right">{t('employees.fields.baseSalary')}</TableCell>
              <TableCell>{t('employees.fields.status')}</TableCell>
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
              filtered.map((row) => (
                <TableRow key={row.id} hover>
                  <TableCell>{row.employee_number}</TableCell>
                  <TableCell>
                    {row.user
                      ? `${row.user.full_name || row.user.username} (${row.user.username})`
                      : '—'}
                  </TableCell>
                  <TableCell>{t(`employees.departments.${row.department}`)}</TableCell>
                  <TableCell>{row.title}</TableCell>
                  <TableCell>{row.hire_date}</TableCell>
                  <TableCell align="right">{formatMoney(row.base_salary)}</TableCell>
                  <TableCell>
                    {row.termination_date ? (
                      <Chip
                        size="small"
                        label={t('employees.status.terminated')}
                        color="default"
                      />
                    ) : (
                      <Chip
                        size="small"
                        label={t('employees.status.active')}
                        color="success"
                      />
                    )}
                  </TableCell>
                  <TableCell align="right">
                    <Tooltip title={t('employees.salaryHistory')}>
                      <IconButton size="small" onClick={() => openSalary(row)}>
                        <PaidIcon fontSize="small" />
                      </IconButton>
                    </Tooltip>
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
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </TableContainer>

      <Dialog open={dialog.open} onClose={closeDialog} fullWidth maxWidth="sm">
        <Box component="form" onSubmit={handleSubmit}>
          <DialogTitle>
            {dialog.mode === 'create' ? t('employees.createTitle') : t('employees.editTitle')}
          </DialogTitle>
          <DialogContent>
            <Stack spacing={2} sx={{ mt: 1 }}>
              {submitError && <Alert severity="error">{submitError}</Alert>}

              <FormControl fullWidth size="small">
                <InputLabel>{t('employees.fields.linkedUser')}</InputLabel>
                <Select
                  label={t('employees.fields.linkedUser')}
                  value={form.user_id}
                  onChange={(e) => setForm({ ...form, user_id: e.target.value })}
                >
                  <MenuItem value="">{t('employees.noLinkedUser')}</MenuItem>
                  {allUsers.map((u) => {
                    const isLinked = linkedUserIds.has(u.id)
                    const isCurrent = dialog.mode === 'edit' && Number(form.user_id) === u.id
                    if (isLinked && !isCurrent) return null
                    return (
                      <MenuItem key={u.id} value={String(u.id)}>
                        {u.full_name || u.username} ({u.username})
                      </MenuItem>
                    )
                  })}
                </Select>
              </FormControl>

              <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2}>
                <FormControl fullWidth size="small">
                  <InputLabel>{t('employees.fields.department')}</InputLabel>
                  <Select
                    label={t('employees.fields.department')}
                    value={form.department}
                    onChange={(e) => setForm({ ...form, department: e.target.value })}
                  >
                    {DEPARTMENTS.map((d) => (
                      <MenuItem key={d} value={d}>{t(`employees.departments.${d}`)}</MenuItem>
                    ))}
                  </Select>
                </FormControl>
                <FormControl fullWidth size="small">
                  <InputLabel>{t('employees.fields.employmentType')}</InputLabel>
                  <Select
                    label={t('employees.fields.employmentType')}
                    value={form.employment_type}
                    onChange={(e) => setForm({ ...form, employment_type: e.target.value })}
                  >
                    {EMPLOYMENT_TYPES.map((et) => (
                      <MenuItem key={et} value={et}>{t(`employees.employmentTypes.${et}`)}</MenuItem>
                    ))}
                  </Select>
                </FormControl>
              </Stack>

              <TextField
                label={t('employees.fields.title')}
                value={form.title}
                onChange={(e) => setForm({ ...form, title: e.target.value })}
                required
                inputProps={{ maxLength: 64 }}
                fullWidth
                size="small"
              />

              <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2}>
                <TextField
                  label={t('employees.fields.hireDate')}
                  type="date"
                  value={form.hire_date}
                  onChange={(e) => setForm({ ...form, hire_date: e.target.value })}
                  required
                  slotProps={{
                    inputLabel: { shrink: true },
                    input: { notched: true },
                  }}
                  fullWidth
                  size="small"
                />
                <TextField
                  label={t('employees.fields.terminationDate')}
                  type="date"
                  value={form.termination_date}
                  onChange={(e) => setForm({ ...form, termination_date: e.target.value })}
                  slotProps={{
                    inputLabel: { shrink: true },
                    input: { notched: true },
                  }}
                  fullWidth
                  size="small"
                />
              </Stack>

              {dialog.mode === 'create' && (
                <TextField
                  label={t('employees.fields.initialSalary')}
                  type="number"
                  value={createForm.initial_salary}
                  onChange={(e) => setCreateForm({ ...createForm, initial_salary: e.target.value })}
                  required
                  inputProps={{ min: 0, step: '0.01' }}
                  fullWidth
                  size="small"
                  helperText={t('employees.initialSalaryHint')}
                />
              )}

              <TextField
                label={t('employees.fields.notes')}
                value={form.notes}
                onChange={(e) => setForm({ ...form, notes: e.target.value })}
                multiline
                minRows={2}
                maxRows={4}
                inputProps={{ maxLength: 500 }}
                fullWidth
                size="small"
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
            {t('employees.deleteConfirm', { number: deleteTarget?.employee_number })}
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteTarget(null)}>{t('common.cancel')}</Button>
          <Button onClick={handleDelete} color="error" variant="contained" disabled={deleting}>
            {deleting ? t('common.loading') : t('common.delete')}
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog open={Boolean(salaryTarget)} onClose={closeSalary} fullWidth maxWidth="md">
        <DialogTitle>
          {t('employees.salaryHistoryTitle', {
            number: salaryTarget?.employee_number || '',
            name: salaryTarget?.user?.full_name || salaryTarget?.user?.username || salaryTarget?.title || '',
          })}
        </DialogTitle>
        <DialogContent>
          {salaryError && <Alert severity="error" sx={{ mb: 2 }}>{salaryError}</Alert>}

          <Typography variant="subtitle2" gutterBottom>{t('employees.currentBaseSalary')}: {formatMoney(salaryTarget?.base_salary)}</Typography>

          <Box component="form" onSubmit={handleAddSalary} sx={{ mt: 2, mb: 3 }}>
            <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2} alignItems="flex-start">
              <TextField
                label={t('employees.salary.effectiveDate')}
                type="date"
                value={salaryForm.effective_date}
                onChange={(e) => setSalaryForm({ ...salaryForm, effective_date: e.target.value })}
                required
                slotProps={{
                  inputLabel: { shrink: true },
                  input: { notched: true },
                }}
                size="small"
              />
              <TextField
                label={t('employees.salary.amount')}
                type="number"
                value={salaryForm.amount}
                onChange={(e) => setSalaryForm({ ...salaryForm, amount: e.target.value })}
                required
                inputProps={{ min: 0, step: '0.01' }}
                size="small"
              />
              <FormControl size="small" sx={{ minWidth: 140 }}>
                <InputLabel>{t('employees.salary.reason')}</InputLabel>
                <Select
                  label={t('employees.salary.reason')}
                  value={salaryForm.reason}
                  onChange={(e) => setSalaryForm({ ...salaryForm, reason: e.target.value })}
                >
                  {SALARY_REASONS.map((r) => (
                    <MenuItem key={r} value={r}>{t(`employees.salaryReasons.${r}`)}</MenuItem>
                  ))}
                </Select>
              </FormControl>
              <TextField
                label={t('employees.salary.notes')}
                value={salaryForm.notes}
                onChange={(e) => setSalaryForm({ ...salaryForm, notes: e.target.value })}
                size="small"
                sx={{ flexGrow: 1 }}
              />
              <Button type="submit" variant="contained" disabled={salarySubmitting}>
                {salarySubmitting ? t('common.loading') : t('employees.salary.add')}
              </Button>
            </Stack>
          </Box>

          <TableContainer component={Paper} variant="outlined">
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>{t('employees.salary.effectiveDate')}</TableCell>
                  <TableCell align="right">{t('employees.salary.amount')}</TableCell>
                  <TableCell>{t('employees.salary.reason')}</TableCell>
                  <TableCell>{t('employees.salary.notes')}</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {salaryLoading ? (
                  <TableRow>
                    <TableCell colSpan={4} align="center">
                      <CircularProgress size={20} />
                    </TableCell>
                  </TableRow>
                ) : salaryRecords.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={4} align="center">
                      <Typography color="text.secondary">{t('common.noData')}</Typography>
                    </TableCell>
                  </TableRow>
                ) : (
                  salaryRecords.map((rec) => (
                    <TableRow key={rec.id}>
                      <TableCell>{rec.effective_date}</TableCell>
                      <TableCell align="right">{formatMoney(rec.amount)}</TableCell>
                      <TableCell>{t(`employees.salaryReasons.${rec.reason}`, rec.reason)}</TableCell>
                      <TableCell>{rec.notes || '—'}</TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </TableContainer>
        </DialogContent>
        <DialogActions>
          <Button onClick={closeSalary}>{t('common.close')}</Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}

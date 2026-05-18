import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import {
  Alert,
  Box,
  CircularProgress,
  Paper,
  Stack,
  Tab,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableFooter,
  TableHead,
  TableRow,
  Tabs,
  TextField,
  Typography,
} from '@mui/material'

import * as agingApi from '@/api/aging'

const BUCKETS = [
  { key: 'not_due', i18n: 'aging.notDue' },
  { key: 'd1_30', i18n: 'aging.d1_30' },
  { key: 'd31_60', i18n: 'aging.d31_60' },
  { key: 'd61_90', i18n: 'aging.d61_90' },
  { key: 'd90_plus', i18n: 'aging.d90Plus' },
]

function todayIsoDate() {
  const now = new Date()
  const offset = now.getTimezoneOffset()
  const local = new Date(now.getTime() - offset * 60 * 1000)
  return local.toISOString().slice(0, 10)
}

function formatAmount(value) {
  if (value == null) return '—'
  const n = Number(value)
  if (!Number.isFinite(n)) return String(value)
  return n.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

export default function AgingPage() {
  const { t } = useTranslation()
  const [tab, setTab] = useState('ar')
  const [asOf, setAsOf] = useState(todayIsoDate())
  const [arReport, setArReport] = useState(null)
  const [apReport, setApReport] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      try {
        if (tab === 'ar') {
          const data = await agingApi.arAging(asOf)
          if (!cancelled) {
            setArReport(data)
            setError(null)
          }
        } else {
          const data = await agingApi.apAging(asOf)
          if (!cancelled) {
            setApReport(data)
            setError(null)
          }
        }
      } catch (err) {
        if (!cancelled) setError(err.response?.data?.detail || err.message)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [tab, asOf])

  const report = tab === 'ar' ? arReport : apReport
  const isAR = tab === 'ar'

  return (
    <Box>
      <Stack direction="row" justifyContent="space-between" alignItems="center" mb={2}>
        <Typography variant="h4">{t('aging.title')}</Typography>
      </Stack>

      <Paper sx={{ p: 2, mb: 2 }}>
        <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2} alignItems={{ sm: 'center' }}>
          <TextField
            label={t('aging.asOf')}
            value={asOf}
            onChange={(e) => setAsOf(e.target.value)}
            type="date"
            InputLabelProps={{ shrink: true }}
            size="small"
          />
        </Stack>
      </Paper>

      <Tabs
        value={tab}
        onChange={(_, v) => setTab(v)}
        sx={{ borderBottom: 1, borderColor: 'divider', mb: 2 }}
      >
        <Tab value="ar" label={t('aging.tabAR')} />
        <Tab value="ap" label={t('aging.tabAP')} />
      </Tabs>

      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

      {!report ? (
        <Box sx={{ textAlign: 'center', py: 4 }}>
          <CircularProgress />
        </Box>
      ) : (
        <TableContainer component={Paper}>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>{isAR ? t('aging.customer') : t('aging.supplier')}</TableCell>
                {BUCKETS.map((b) => (
                  <TableCell key={b.key} align="right">
                    {t(b.i18n)}
                  </TableCell>
                ))}
                <TableCell align="right" sx={{ fontWeight: 600 }}>
                  {t('aging.total')}
                </TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {report.rows.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={BUCKETS.length + 2} align="center">
                    <Typography color="text.secondary">
                      {t('common.noData')}
                    </Typography>
                  </TableCell>
                </TableRow>
              ) : (
                report.rows.map((row) => (
                  <TableRow key={isAR ? row.customer_id : row.supplier_id} hover>
                    <TableCell>
                      {isAR ? row.customer_name : row.supplier_name}
                    </TableCell>
                    {BUCKETS.map((b) => (
                      <TableCell key={b.key} align="right">
                        {formatAmount(row.buckets[b.key])}
                      </TableCell>
                    ))}
                    <TableCell align="right" sx={{ fontWeight: 600 }}>
                      {formatAmount(row.buckets.total)}
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
            {report.rows.length > 0 && (
              <TableFooter>
                <TableRow sx={{ bgcolor: 'action.hover' }}>
                  <TableCell sx={{ fontWeight: 600 }}>{t('aging.rowsTotal')}</TableCell>
                  {BUCKETS.map((b) => (
                    <TableCell key={b.key} align="right" sx={{ fontWeight: 600 }}>
                      {formatAmount(report.totals[b.key])}
                    </TableCell>
                  ))}
                  <TableCell align="right" sx={{ fontWeight: 700 }}>
                    {formatAmount(report.totals.total)}
                  </TableCell>
                </TableRow>
              </TableFooter>
            )}
          </Table>
        </TableContainer>
      )}
    </Box>
  )
}

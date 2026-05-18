import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link as RouterLink } from 'react-router-dom'
import {
  Alert,
  Box,
  Card,
  CardActionArea,
  CardContent,
  CircularProgress,
  Grid,
  Stack,
  Typography,
} from '@mui/material'
import TrendingUpIcon from '@mui/icons-material/TrendingUp'
import LocalShippingIcon from '@mui/icons-material/LocalShipping'
import WarningAmberIcon from '@mui/icons-material/WarningAmber'
import ReceiptLongIcon from '@mui/icons-material/ReceiptLong'
import InboxIcon from '@mui/icons-material/Inbox'
import RequestQuoteIcon from '@mui/icons-material/RequestQuote'
import PaymentsIcon from '@mui/icons-material/Payments'
import Inventory2Icon from '@mui/icons-material/Inventory2'
import StorefrontIcon from '@mui/icons-material/Storefront'
import GroupsIcon from '@mui/icons-material/Groups'
import PointOfSaleIcon from '@mui/icons-material/PointOfSale'
import WarehouseIcon from '@mui/icons-material/Warehouse'
import AssessmentIcon from '@mui/icons-material/Assessment'

import * as dashboardApi from '@/api/dashboard'
import { useAuth } from '@/contexts/AuthContext'

function formatCurrency(value) {
  const n = Number(value || 0)
  return n.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

function KpiCard({ icon, label, value, sub, accent }) {
  return (
    <Card sx={{ height: '100%', position: 'relative', overflow: 'hidden' }}>
      <Box
        sx={{
          position: 'absolute',
          left: 0,
          top: 0,
          bottom: 0,
          width: 3,
          bgcolor: accent || 'primary.main',
        }}
      />
      <CardContent sx={{ p: 2.5 }}>
        <Stack direction="row" alignItems="flex-start" justifyContent="space-between" spacing={2}>
          <Box>
            <Typography variant="caption" color="text.secondary" sx={{ textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              {label}
            </Typography>
            <Typography variant="h4" sx={{ mt: 0.5, fontWeight: 700, color: 'text.primary' }}>
              {value}
            </Typography>
            {sub && (
              <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5, display: 'block' }}>
                {sub}
              </Typography>
            )}
          </Box>
          <Box sx={{ color: 'text.secondary', mt: 0.25, flexShrink: 0 }}>{icon}</Box>
        </Stack>
      </CardContent>
    </Card>
  )
}

function QuickLink({ to, icon, label }) {
  return (
    <Card sx={{ height: '100%' }}>
      <CardActionArea component={RouterLink} to={to} sx={{ height: '100%', p: 2 }}>
        <Stack direction="row" spacing={1.5} alignItems="center">
          <Box sx={{ color: 'text.secondary', flexShrink: 0, display: 'flex' }}>{icon}</Box>
          <Typography sx={{ fontWeight: 600 }}>{label}</Typography>
        </Stack>
      </CardActionArea>
    </Card>
  )
}

export default function HomePage() {
  const { t } = useTranslation()
  const { user, hasRole } = useAuth()

  const [summary, setSummary] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      try {
        const data = await dashboardApi.getSummary()
        if (!cancelled) {
          setSummary(data)
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
  }, [])

  const quickLinks = [
    { to: '/products', icon: <Inventory2Icon />, key: 'products' },
    { to: '/suppliers', icon: <StorefrontIcon />, key: 'suppliers' },
    { to: '/purchases', icon: <LocalShippingIcon />, key: 'purchases' },
    { to: '/customers', icon: <GroupsIcon />, key: 'customers' },
    { to: '/sales', icon: <PointOfSaleIcon />, key: 'sales' },
    { to: '/inventory', icon: <WarehouseIcon />, key: 'inventory' },
    { to: '/reports', icon: <AssessmentIcon />, key: 'reports' },
  ].filter((it) => {
    if (it.key === 'categories' && !hasRole('admin', 'manager')) return false
    return true
  })

  return (
    <Stack spacing={3}>
      <Box>
        <Typography variant="h4" sx={{ fontWeight: 700 }}>
          {t('home.greeting', { name: user?.full_name || user?.username || '' })}
        </Typography>
        <Typography variant="body1" color="text.secondary" sx={{ mt: 0.5 }}>
          {summary
            ? t('home.subtitleMonth', { month: summary.current_month })
            : t('home.subtitle')}
        </Typography>
      </Box>

      {error && <Alert severity="error">{error}</Alert>}

      {loading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 6 }}>
          <CircularProgress />
        </Box>
      ) : summary ? (
        <Grid container spacing={2}>
          <Grid item xs={12} sm={6} md={4} lg={2.4}>
            <KpiCard
              icon={<TrendingUpIcon />}
              label={t('home.kpi.monthSales')}
              value={formatCurrency(summary.month_sales_amount)}
              sub={summary.current_month}
              accent="success.main"
            />
          </Grid>
          <Grid item xs={12} sm={6} md={4} lg={2.4}>
            <KpiCard
              icon={<LocalShippingIcon />}
              label={t('home.kpi.monthPurchase')}
              value={formatCurrency(summary.month_purchase_amount)}
              sub={summary.current_month}
              accent="info.main"
            />
          </Grid>
          <Grid item xs={12} sm={6} md={4} lg={2.4}>
            <KpiCard
              icon={<WarningAmberIcon />}
              label={t('home.kpi.lowStock')}
              value={summary.low_stock_count}
              sub={t('home.kpi.lowStockSub')}
              accent="warning.main"
            />
          </Grid>
          <Grid item xs={12} sm={6} md={4} lg={2.4}>
            <KpiCard
              icon={<ReceiptLongIcon />}
              label={t('home.kpi.draftSales')}
              value={summary.draft_sales_count}
              sub={t('home.kpi.draftSalesSub')}
              accent="text.secondary"
            />
          </Grid>
          <Grid item xs={12} sm={6} md={4} lg={2.4}>
            <KpiCard
              icon={<InboxIcon />}
              label={t('home.kpi.draftPurchases')}
              value={summary.draft_purchases_count}
              sub={t('home.kpi.draftPurchasesSub')}
              accent="text.secondary"
            />
          </Grid>
          <Grid item xs={12} sm={6} md={4} lg={2.4}>
            <KpiCard
              icon={<RequestQuoteIcon />}
              label={t('home.kpi.arBalance')}
              value={formatCurrency(summary.ar_balance_total)}
              sub={
                summary.ar_overdue_count > 0
                  ? t('home.kpi.arOverdueSub', {
                      amount: formatCurrency(summary.ar_overdue_balance),
                      count: summary.ar_overdue_count,
                    })
                  : t('home.kpi.arNoneOverdue')
              }
              accent={summary.ar_overdue_count > 0 ? 'error.main' : 'primary.main'}
            />
          </Grid>
          <Grid item xs={12} sm={6} md={4} lg={2.4}>
            <KpiCard
              icon={<PaymentsIcon />}
              label={t('home.kpi.apBalance')}
              value={formatCurrency(summary.ap_balance_total)}
              sub={
                summary.ap_overdue_count > 0
                  ? t('home.kpi.apOverdueSub', {
                      amount: formatCurrency(summary.ap_overdue_balance),
                      count: summary.ap_overdue_count,
                    })
                  : t('home.kpi.apNoneOverdue')
              }
              accent={summary.ap_overdue_count > 0 ? 'error.main' : 'primary.main'}
            />
          </Grid>
        </Grid>
      ) : null}

      <Box>
        <Typography variant="h6" sx={{ mb: 1.5, fontWeight: 600 }}>
          {t('home.quickLinks')}
        </Typography>
        <Grid container spacing={2}>
          {quickLinks.map((link) => (
            <Grid key={link.key} item xs={12} sm={6} md={4} lg={3}>
              <QuickLink to={link.to} icon={link.icon} label={t(`nav.${link.key}`)} />
            </Grid>
          ))}
        </Grid>
      </Box>
    </Stack>
  )
}

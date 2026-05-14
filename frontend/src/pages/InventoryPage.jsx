import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import {
  Alert,
  Box,
  Chip,
  CircularProgress,
  FormControl,
  FormControlLabel,
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
  Typography,
} from '@mui/material'

import * as inventoryApi from '@/api/inventory'
import * as categoriesApi from '@/api/categories'

export default function InventoryPage() {
  const { t } = useTranslation()

  const [rows, setRows] = useState([])
  const [categories, setCategories] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const [search, setSearch] = useState('')
  const [filterCategory, setFilterCategory] = useState('')
  const [lowOnly, setLowOnly] = useState(false)

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      try {
        const params = {}
        if (search.trim()) params.search = search.trim()
        if (filterCategory) params.category_id = filterCategory
        if (lowOnly) params.low_only = true
        const [stock, cats] = await Promise.all([
          inventoryApi.listStock(params),
          categoriesApi.listCategories(),
        ])
        if (!cancelled) {
          setRows(stock)
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
  }, [search, filterCategory, lowOnly])

  const colSpan = 7

  return (
    <Box>
      <Typography variant="h4" mb={2}>
        {t('nav.inventory')}
      </Typography>

      <Paper sx={{ p: 2, mb: 2 }}>
        <Stack direction={{ xs: 'column', md: 'row' }} spacing={2} alignItems={{ md: 'center' }}>
          <TextField
            label={t('common.search')}
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder={t('inventory.searchPlaceholder')}
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
          <FormControlLabel
            control={
              <Switch checked={lowOnly} onChange={(e) => setLowOnly(e.target.checked)} />
            }
            label={t('inventory.lowOnly')}
          />
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
              <TableCell align="right">{t('inventory.stockQuantity')}</TableCell>
              <TableCell align="right">{t('inventory.threshold')}</TableCell>
              <TableCell>{t('inventory.alert')}</TableCell>
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
                <TableRow key={row.product_id} hover sx={row.is_low ? { bgcolor: 'warning.light' } : undefined}>
                  <TableCell>{row.sku}</TableCell>
                  <TableCell>{row.name}</TableCell>
                  <TableCell>{row.category_name || '—'}</TableCell>
                  <TableCell>{row.unit}</TableCell>
                  <TableCell align="right">{row.stock_quantity}</TableCell>
                  <TableCell align="right">
                    {row.low_stock_threshold > 0 ? row.low_stock_threshold : '—'}
                  </TableCell>
                  <TableCell>
                    {row.is_low && (
                      <Chip size="small" label={t('inventory.lowBadge')} color="warning" />
                    )}
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </TableContainer>
    </Box>
  )
}

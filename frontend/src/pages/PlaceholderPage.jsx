import { useTranslation } from 'react-i18next'
import { Box, Typography } from '@mui/material'

export default function PlaceholderPage({ titleKey }) {
  const { t } = useTranslation()
  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        {t(titleKey)}
      </Typography>
      <Typography color="text.secondary">🚧 尚未實作 / Not implemented yet</Typography>
    </Box>
  )
}

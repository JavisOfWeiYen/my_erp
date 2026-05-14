import { Link as RouterLink } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { Box, Button, Typography } from '@mui/material'

export default function NotFoundPage() {
  const { t } = useTranslation()
  return (
    <Box sx={{ textAlign: 'center', mt: 8 }}>
      <Typography variant="h2">404</Typography>
      <Typography variant="h6" sx={{ mt: 2 }}>
        {t('errors.notFound')}
      </Typography>
      <Button component={RouterLink} to="/" sx={{ mt: 3 }} variant="contained">
        {t('nav.home')}
      </Button>
    </Box>
  )
}

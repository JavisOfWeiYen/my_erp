import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { Box, CircularProgress } from '@mui/material'

import { useAuth } from '@/contexts/AuthContext'

export default function ProtectedRoute({ roles }) {
  const { isAuthenticated, loading, user, hasRole } = useAuth()
  const location = useLocation()

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
        <CircularProgress />
      </Box>
    )
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />
  }

  if (roles && roles.length > 0 && user && !hasRole(...roles)) {
    return <Navigate to="/" replace />
  }

  return <Outlet />
}

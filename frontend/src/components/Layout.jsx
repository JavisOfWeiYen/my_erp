import { useState } from 'react'
import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import {
  AppBar,
  Avatar,
  Box,
  CssBaseline,
  Divider,
  Drawer,
  IconButton,
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Menu,
  MenuItem,
  Select,
  Toolbar,
  Tooltip,
  Typography,
} from '@mui/material'
import MenuIcon from '@mui/icons-material/Menu'
import HomeIcon from '@mui/icons-material/Home'
import Inventory2Icon from '@mui/icons-material/Inventory2'
import CategoryIcon from '@mui/icons-material/Category'
import LocalShippingIcon from '@mui/icons-material/LocalShipping'
import StorefrontIcon from '@mui/icons-material/Storefront'
import GroupsIcon from '@mui/icons-material/Groups'
import PointOfSaleIcon from '@mui/icons-material/PointOfSale'
import WarehouseIcon from '@mui/icons-material/Warehouse'
import TuneIcon from '@mui/icons-material/Tune'
import AssessmentIcon from '@mui/icons-material/Assessment'
import PeopleIcon from '@mui/icons-material/People'

import { SUPPORTED_LANGUAGES } from '@/i18n'
import { useAuth } from '@/contexts/AuthContext'

const drawerWidth = 248

const navItems = [
  { to: '/', key: 'home', icon: <HomeIcon /> },
  { to: '/products', key: 'products', icon: <Inventory2Icon /> },
  { to: '/categories', key: 'categories', icon: <CategoryIcon />, roles: ['admin', 'manager'] },
  { to: '/suppliers', key: 'suppliers', icon: <StorefrontIcon /> },
  { to: '/purchases', key: 'purchases', icon: <LocalShippingIcon /> },
  { to: '/customers', key: 'customers', icon: <GroupsIcon /> },
  { to: '/sales', key: 'sales', icon: <PointOfSaleIcon /> },
  { to: '/inventory', key: 'inventory', icon: <WarehouseIcon /> },
  { to: '/adjustments', key: 'adjustments', icon: <TuneIcon />, roles: ['admin', 'manager', 'warehouse'] },
  { to: '/reports', key: 'reports', icon: <AssessmentIcon /> },
  { to: '/users', key: 'users', icon: <PeopleIcon />, roles: ['admin'] },
]

export default function Layout() {
  const { t, i18n } = useTranslation()
  const navigate = useNavigate()
  const { user, logout, hasRole } = useAuth()
  const [mobileOpen, setMobileOpen] = useState(false)
  const [userMenuAnchor, setUserMenuAnchor] = useState(null)

  const handleDrawerToggle = () => setMobileOpen((prev) => !prev)

  const handleLanguageChange = (event) => {
    i18n.changeLanguage(event.target.value)
  }

  const handleLogout = () => {
    setUserMenuAnchor(null)
    logout()
    navigate('/login', { replace: true })
  }

  const visibleNavItems = navItems.filter(
    (item) => !item.roles || hasRole(...item.roles),
  )

  const userInitials = (user?.full_name || user?.username || '?')
    .split(' ')
    .map((part) => part.charAt(0))
    .slice(0, 2)
    .join('')
    .toUpperCase()

  const drawerContent = (
    <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <Toolbar
        sx={{
          px: 3,
          borderBottom: (theme) => `1px solid ${theme.palette.sidebar.border}`,
        }}
      >
        <Typography
          variant="h6"
          noWrap
          sx={{
            color: 'sidebar.text',
            fontWeight: 700,
            letterSpacing: '0.02em',
          }}
        >
          {t('app.shortTitle')}
        </Typography>
      </Toolbar>
      <List sx={{ flexGrow: 1, px: 1.5, py: 2 }}>
        {visibleNavItems.map((item) => (
          <ListItem key={item.key} disablePadding sx={{ mb: 0.5 }}>
            <ListItemButton
              component={NavLink}
              to={item.to}
              end={item.to === '/'}
              onClick={() => setMobileOpen(false)}
              sx={{
                borderRadius: 1.5,
                color: 'sidebar.textMuted',
                px: 1.5,
                py: 1,
                '& .MuiListItemIcon-root': {
                  color: 'sidebar.textMuted',
                  minWidth: 36,
                },
                '&:hover': {
                  bgcolor: 'sidebar.bgHover',
                  color: 'sidebar.text',
                  '& .MuiListItemIcon-root': { color: 'sidebar.text' },
                },
                '&.active': {
                  bgcolor: 'sidebar.bgActive',
                  color: 'sidebar.accent',
                  fontWeight: 600,
                  '& .MuiListItemIcon-root': { color: 'sidebar.accent' },
                  '& .MuiListItemText-primary': { fontWeight: 600 },
                },
              }}
            >
              <ListItemIcon>{item.icon}</ListItemIcon>
              <ListItemText
                primary={t(`nav.${item.key}`)}
                primaryTypographyProps={{ fontSize: '0.92rem' }}
              />
            </ListItemButton>
          </ListItem>
        ))}
      </List>
      <Box
        sx={{
          px: 2.5,
          py: 2,
          borderTop: (theme) => `1px solid ${theme.palette.sidebar.border}`,
          color: 'sidebar.textMuted',
          fontSize: '0.72rem',
        }}
      >
        v1.0 · MVP
      </Box>
    </Box>
  )

  return (
    <Box sx={{ display: 'flex' }}>
      <CssBaseline />
      <AppBar
        position="fixed"
        sx={{
          width: { md: `calc(100% - ${drawerWidth}px)` },
          ml: { md: `${drawerWidth}px` },
        }}
      >
        <Toolbar>
          <IconButton
            color="inherit"
            edge="start"
            onClick={handleDrawerToggle}
            sx={{ mr: 2, display: { md: 'none' } }}
          >
            <MenuIcon />
          </IconButton>
          <Typography
            variant="h6"
            sx={{ flexGrow: 1, color: 'text.primary', fontWeight: 600 }}
          >
            {t('app.title')}
          </Typography>
          <Select
            value={i18n.language?.startsWith('zh') ? 'zh-TW' : 'en'}
            onChange={handleLanguageChange}
            variant="standard"
            disableUnderline
            sx={{
              color: 'text.secondary',
              mr: 2,
              fontSize: '0.875rem',
              '& .MuiSelect-icon': { color: 'text.secondary' },
            }}
          >
            {SUPPORTED_LANGUAGES.map((lang) => (
              <MenuItem key={lang.code} value={lang.code}>
                {lang.label}
              </MenuItem>
            ))}
          </Select>
          {user && (
            <>
              <Tooltip title={user.full_name || user.username}>
                <IconButton
                  onClick={(e) => setUserMenuAnchor(e.currentTarget)}
                  sx={{ p: 0 }}
                >
                  <Avatar
                    sx={{
                      bgcolor: 'secondary.main',
                      width: 36,
                      height: 36,
                      fontSize: '0.875rem',
                      fontWeight: 600,
                    }}
                  >
                    {userInitials}
                  </Avatar>
                </IconButton>
              </Tooltip>
              <Menu
                anchorEl={userMenuAnchor}
                open={Boolean(userMenuAnchor)}
                onClose={() => setUserMenuAnchor(null)}
              >
                <MenuItem disabled>
                  <Box>
                    <Typography variant="body2" fontWeight={600}>
                      {user.full_name || user.username}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      {t(`roles.${user.role?.name}`, user.role?.name)}
                    </Typography>
                  </Box>
                </MenuItem>
                <Divider />
                <MenuItem onClick={handleLogout}>{t('common.logout')}</MenuItem>
              </Menu>
            </>
          )}
        </Toolbar>
      </AppBar>

      <Box component="nav" sx={{ width: { md: drawerWidth }, flexShrink: { md: 0 } }}>
        <Drawer
          variant="temporary"
          open={mobileOpen}
          onClose={handleDrawerToggle}
          ModalProps={{ keepMounted: true }}
          sx={{
            display: { xs: 'block', md: 'none' },
            '& .MuiDrawer-paper': {
              width: drawerWidth,
              bgcolor: 'sidebar.bg',
              color: 'sidebar.text',
            },
          }}
        >
          {drawerContent}
        </Drawer>
        <Drawer
          variant="permanent"
          sx={{
            display: { xs: 'none', md: 'block' },
            '& .MuiDrawer-paper': {
              width: drawerWidth,
              boxSizing: 'border-box',
              bgcolor: 'sidebar.bg',
              color: 'sidebar.text',
              borderRight: (theme) => `1px solid ${theme.palette.sidebar.border}`,
            },
          }}
          open
        >
          {drawerContent}
        </Drawer>
      </Box>

      <Box
        component="main"
        sx={{
          flexGrow: 1,
          p: { xs: 2, md: 3 },
          width: { md: `calc(100% - ${drawerWidth}px)` },
          minHeight: '100vh',
          bgcolor: 'background.default',
        }}
      >
        <Toolbar />
        <Outlet />
      </Box>
    </Box>
  )
}

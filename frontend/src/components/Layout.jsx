import { useEffect, useMemo, useState } from 'react'
import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import {
  AppBar,
  Avatar,
  Box,
  Collapse,
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
import ExpandLessIcon from '@mui/icons-material/ExpandLess'
import ExpandMoreIcon from '@mui/icons-material/ExpandMore'

import { SUPPORTED_LANGUAGES } from '@/i18n'
import { useAuth } from '@/contexts/AuthContext'
import * as menuApi from '@/api/menu'
import { MenuIcon as SidebarIcon } from '@/components/iconMap'

const drawerWidth = 248
const EXPANDED_STORAGE_KEY = 'sidebar.expanded'

function readExpandedFromStorage() {
  try {
    const raw = localStorage.getItem(EXPANDED_STORAGE_KEY)
    if (!raw) return new Set()
    const arr = JSON.parse(raw)
    return new Set(Array.isArray(arr) ? arr : [])
  } catch {
    return new Set()
  }
}

function writeExpandedToStorage(set) {
  try {
    localStorage.setItem(EXPANDED_STORAGE_KEY, JSON.stringify([...set]))
  } catch {
    // localStorage may be unavailable; ignore.
  }
}

function collectAncestorIds(items, currentPath) {
  // Walk the tree; for any leaf whose route_path matches the current path, return
  // the chain of ancestor group ids so they can be auto-expanded.
  const result = new Set()
  const walk = (node, ancestors) => {
    if (node.route_path === currentPath) {
      ancestors.forEach((id) => result.add(id))
    }
    if (node.children?.length) {
      const next = [...ancestors, node.id]
      node.children.forEach((c) => walk(c, next))
    }
  }
  items.forEach((root) => walk(root, []))
  return result
}

function labelForNode(node, t) {
  if (node.custom_label) return node.custom_label
  if (node.label_key) return t(node.label_key, node.label_key)
  return `#${node.id}`
}

function NavLeaf({ node, t, onNavigate }) {
  return (
    <ListItem disablePadding sx={{ mb: 0.5 }}>
      <ListItemButton
        component={NavLink}
        to={node.route_path}
        end={node.route_path === '/'}
        onClick={onNavigate}
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
        <ListItemIcon>
          <SidebarIcon name={node.icon_name} />
        </ListItemIcon>
        <ListItemText
          primary={labelForNode(node, t)}
          primaryTypographyProps={{ fontSize: '0.92rem' }}
        />
      </ListItemButton>
    </ListItem>
  )
}

function NavGroup({ node, depth, t, onNavigate, isExpanded, toggle }) {
  const open = isExpanded(node.id)
  return (
    <>
      <ListItem disablePadding sx={{ mb: 0.5 }}>
        <ListItemButton
          onClick={() => toggle(node.id)}
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
          }}
        >
          <ListItemIcon>
            <SidebarIcon name={node.icon_name} />
          </ListItemIcon>
          <ListItemText
            primary={labelForNode(node, t)}
            primaryTypographyProps={{ fontSize: '0.88rem', fontWeight: 600, letterSpacing: '0.02em' }}
          />
          {open ? <ExpandLessIcon fontSize="small" /> : <ExpandMoreIcon fontSize="small" />}
        </ListItemButton>
      </ListItem>
      <Collapse in={open} timeout="auto" unmountOnExit>
        <Box sx={{ pl: depth + 1 }}>
          {node.children.map((child) => (
            <NavNode
              key={child.id}
              node={child}
              depth={depth + 1}
              t={t}
              onNavigate={onNavigate}
              isExpanded={isExpanded}
              toggle={toggle}
            />
          ))}
        </Box>
      </Collapse>
    </>
  )
}

function NavNode({ node, depth, t, onNavigate, isExpanded, toggle }) {
  const isGroup = !node.route_path
  if (isGroup) {
    return (
      <NavGroup
        node={node}
        depth={depth}
        t={t}
        onNavigate={onNavigate}
        isExpanded={isExpanded}
        toggle={toggle}
      />
    )
  }
  return <NavLeaf node={node} t={t} onNavigate={onNavigate} />
}

export default function Layout() {
  const { t, i18n } = useTranslation()
  const navigate = useNavigate()
  const location = useLocation()
  const { user, logout } = useAuth()
  const [mobileOpen, setMobileOpen] = useState(false)
  const [userMenuAnchor, setUserMenuAnchor] = useState(null)
  const [tree, setTree] = useState([])
  const [expanded, setExpanded] = useState(() => readExpandedFromStorage())

  useEffect(() => {
    if (!user) return
    let cancelled = false
    ;(async () => {
      try {
        const data = await menuApi.getMenu()
        if (!cancelled) setTree(data)
      } catch {
        // If menu fetch fails the user simply sees an empty sidebar; auth still works.
      }
    })()
    return () => {
      cancelled = true
    }
  }, [user])

  // Auto-expand any group whose subtree contains the current route.
  const ancestorsForCurrentRoute = useMemo(
    () => collectAncestorIds(tree, location.pathname),
    [tree, location.pathname],
  )
  // Derived "what's actually open" = user-toggled ∪ ancestors-of-current-route.
  // We keep user-toggled state separate (in `expanded`) so persistence + manual
  // collapse still work; the route-derived expansion is layered on top each render.
  const effectiveExpanded = useMemo(() => {
    const next = new Set(expanded)
    ancestorsForCurrentRoute.forEach((id) => next.add(id))
    return next
  }, [expanded, ancestorsForCurrentRoute])

  const isExpanded = (id) => effectiveExpanded.has(id)
  const toggleExpanded = (id) => {
    setExpanded((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      writeExpandedToStorage(next)
      return next
    })
  }

  const handleDrawerToggle = () => setMobileOpen((prev) => !prev)
  const handleLanguageChange = (event) => i18n.changeLanguage(event.target.value)
  const handleLogout = () => {
    setUserMenuAnchor(null)
    logout()
    navigate('/login', { replace: true })
  }

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
          sx={{ color: 'sidebar.text', fontWeight: 700, letterSpacing: '0.02em' }}
        >
          {t('app.shortTitle')}
        </Typography>
      </Toolbar>
      <List sx={{ flexGrow: 1, px: 1.5, py: 2, overflowY: 'auto' }}>
        {tree.map((node) => (
          <NavNode
            key={node.id}
            node={node}
            depth={0}
            t={t}
            onNavigate={() => setMobileOpen(false)}
            isExpanded={isExpanded}
            toggle={toggleExpanded}
          />
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
          <Typography variant="h6" sx={{ flexGrow: 1, color: 'text.primary', fontWeight: 600 }}>
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
                <IconButton onClick={(e) => setUserMenuAnchor(e.currentTarget)} sx={{ p: 0 }}>
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

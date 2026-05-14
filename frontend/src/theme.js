import { createTheme } from '@mui/material/styles'

// Muted, warm, near-flat palette inspired by a minimalist learning-app reference.
// Primary = slate gray-blue, accent = soft sky-blue, neutrals on the stone scale.
const palette = {
  mode: 'light',
  primary: {
    main: '#475569',
    light: '#64748B',
    dark: '#334155',
    contrastText: '#FFFFFF',
  },
  secondary: {
    main: '#0EA5E9',
    light: '#38BDF8',
    dark: '#0284C7',
    contrastText: '#FFFFFF',
  },
  success: { main: '#16A34A', light: '#22C55E', dark: '#15803D' },
  warning: { main: '#CA8A04', light: '#EAB308', dark: '#A16207' },
  error:   { main: '#DC2626', light: '#EF4444', dark: '#B91C1C' },
  info:    { main: '#0EA5E9', light: '#38BDF8', dark: '#0284C7' },
  background: {
    default: '#FAFAF9',
    paper: '#FFFFFF',
  },
  text: {
    primary: '#1C1917',
    secondary: '#57534E',
    disabled: '#A8A29E',
  },
  divider: '#E7E5E4',
}

// Sidebar tokens — consumed by Layout via `theme.palette.sidebar.*`.
// Light sidebar variant: white surface, warm hover, stone-tinted active state.
const sidebar = {
  bg: '#FFFFFF',
  bgHover: 'rgba(28, 25, 23, 0.04)',
  bgActive: '#F5F5F4',
  border: '#E7E5E4',
  text: '#1C1917',
  textMuted: '#78716C',
  accent: '#0EA5E9',
}

const fontStack = [
  '-apple-system',
  'BlinkMacSystemFont',
  'Inter',
  '"Segoe UI"',
  'Roboto',
  '"Noto Sans TC"',
  '"PingFang TC"',
  '"Microsoft JhengHei"',
  'sans-serif',
].join(',')

const theme = createTheme({
  palette: { ...palette, sidebar },
  shape: { borderRadius: 8 },
  typography: {
    fontFamily: fontStack,
    fontSize: 14,
    h4: { fontWeight: 600, letterSpacing: '-0.015em' },
    h5: { fontWeight: 600, letterSpacing: '-0.01em' },
    h6: { fontWeight: 600, letterSpacing: '-0.005em' },
    subtitle1: { fontWeight: 600 },
    subtitle2: { fontWeight: 500, letterSpacing: '0.04em', textTransform: 'uppercase', color: palette.text.disabled },
    button: { textTransform: 'none', fontWeight: 500 },
  },
  shadows: [
    'none',
    '0 1px 2px rgba(28, 25, 23, 0.04)',
    '0 1px 2px rgba(28, 25, 23, 0.05), 0 1px 1px rgba(28, 25, 23, 0.03)',
    '0 2px 4px rgba(28, 25, 23, 0.05), 0 1px 2px rgba(28, 25, 23, 0.03)',
    '0 4px 8px rgba(28, 25, 23, 0.06), 0 2px 4px rgba(28, 25, 23, 0.03)',
    '0 6px 12px rgba(28, 25, 23, 0.07), 0 3px 6px rgba(28, 25, 23, 0.04)',
    '0 8px 16px rgba(28, 25, 23, 0.08), 0 4px 8px rgba(28, 25, 23, 0.04)',
    '0 12px 24px rgba(28, 25, 23, 0.09), 0 6px 12px rgba(28, 25, 23, 0.04)',
    '0 16px 32px rgba(28, 25, 23, 0.10), 0 8px 16px rgba(28, 25, 23, 0.05)',
    '0 20px 40px rgba(28, 25, 23, 0.11), 0 10px 20px rgba(28, 25, 23, 0.05)',
    '0 24px 48px rgba(28, 25, 23, 0.12), 0 12px 24px rgba(28, 25, 23, 0.05)',
    '0 28px 56px rgba(28, 25, 23, 0.13), 0 14px 28px rgba(28, 25, 23, 0.06)',
    '0 32px 64px rgba(28, 25, 23, 0.14), 0 16px 32px rgba(28, 25, 23, 0.06)',
    '0 36px 72px rgba(28, 25, 23, 0.15), 0 18px 36px rgba(28, 25, 23, 0.06)',
    '0 40px 80px rgba(28, 25, 23, 0.16), 0 20px 40px rgba(28, 25, 23, 0.07)',
    '0 44px 88px rgba(28, 25, 23, 0.17), 0 22px 44px rgba(28, 25, 23, 0.07)',
    '0 48px 96px rgba(28, 25, 23, 0.18), 0 24px 48px rgba(28, 25, 23, 0.07)',
    '0 52px 104px rgba(28, 25, 23, 0.19), 0 26px 52px rgba(28, 25, 23, 0.08)',
    '0 56px 112px rgba(28, 25, 23, 0.20), 0 28px 56px rgba(28, 25, 23, 0.08)',
    '0 60px 120px rgba(28, 25, 23, 0.21), 0 30px 60px rgba(28, 25, 23, 0.08)',
    '0 64px 128px rgba(28, 25, 23, 0.22), 0 32px 64px rgba(28, 25, 23, 0.09)',
    '0 68px 136px rgba(28, 25, 23, 0.23), 0 34px 68px rgba(28, 25, 23, 0.09)',
    '0 72px 144px rgba(28, 25, 23, 0.24), 0 36px 72px rgba(28, 25, 23, 0.09)',
    '0 76px 152px rgba(28, 25, 23, 0.25), 0 38px 76px rgba(28, 25, 23, 0.10)',
    '0 80px 160px rgba(28, 25, 23, 0.26), 0 40px 80px rgba(28, 25, 23, 0.10)',
  ],
  components: {
    MuiCssBaseline: {
      styleOverrides: {
        body: {
          backgroundColor: palette.background.default,
        },
      },
    },
    MuiAppBar: {
      defaultProps: { elevation: 0, color: 'inherit' },
      styleOverrides: {
        root: {
          backgroundColor: '#FFFFFF',
          color: palette.text.primary,
          borderBottom: `1px solid ${palette.divider}`,
        },
      },
    },
    MuiDrawer: {
      styleOverrides: {
        paper: { borderRight: 'none' },
      },
    },
    MuiPaper: {
      defaultProps: { elevation: 0 },
      styleOverrides: {
        root: { backgroundImage: 'none' },
        outlined: { borderColor: palette.divider },
      },
    },
    MuiCard: {
      defaultProps: { elevation: 0 },
      styleOverrides: {
        root: {
          border: `1px solid ${palette.divider}`,
          borderRadius: 12,
        },
      },
    },
    MuiButton: {
      defaultProps: { disableElevation: true },
      styleOverrides: {
        root: {
          borderRadius: 8,
          paddingInline: 16,
        },
        containedPrimary: {
          '&:hover': { backgroundColor: palette.primary.dark },
        },
        outlined: {
          borderColor: '#D6D3D1',
          '&:hover': {
            borderColor: palette.text.secondary,
            backgroundColor: 'rgba(28, 25, 23, 0.03)',
          },
        },
      },
    },
    MuiTableHead: {
      styleOverrides: {
        root: {
          backgroundColor: '#F5F5F4',
          '& .MuiTableCell-head': {
            fontWeight: 600,
            color: palette.text.primary,
            borderBottom: `1px solid ${palette.divider}`,
            letterSpacing: '0.01em',
          },
        },
      },
    },
    MuiTableCell: {
      styleOverrides: {
        root: { borderColor: palette.divider },
      },
    },
    MuiTableRow: {
      styleOverrides: {
        root: {
          '&:hover': { backgroundColor: 'rgba(28, 25, 23, 0.025)' },
        },
      },
    },
    MuiChip: {
      styleOverrides: {
        root: { fontWeight: 500, borderRadius: 6 },
      },
    },
    MuiTextField: {
      defaultProps: { variant: 'outlined' },
    },
    MuiOutlinedInput: {
      styleOverrides: {
        root: {
          backgroundColor: '#FFFFFF',
          borderRadius: 8,
          '& fieldset': { borderColor: '#D6D3D1' },
          '&:hover fieldset': { borderColor: palette.text.secondary },
        },
      },
    },
    MuiTooltip: {
      styleOverrides: {
        tooltip: {
          backgroundColor: palette.text.primary,
          fontSize: '0.75rem',
        },
      },
    },
  },
})

export default theme

import { createTheme } from '@mui/material/styles'

// ── Claude-inspired light theme ──────────────────────────────────────────────
// Warm ivory surfaces, warm-gray text, ONE accent (terracotta). Light-only by
// explicit brief; no theme switcher. Shape lock: cards 12px, buttons 8px,
// chips pill (MUI Chip default). No glow shadows; shadows tinted warm.
const TERRACOTTA = '#B14E2E'
const TERRACOTTA_DARK = '#8F3D24'

const theme = createTheme({
  palette: {
    mode: 'light',
    background: {
      default: '#FAF9F5', // warm ivory page
      paper: '#FFFFFF',
    },
    text: {
      primary: '#1F1E1D', // warm near-black
      secondary: '#6B6560',
      disabled: '#A8A29A',
    },
    primary: {
      main: TERRACOTTA,
      dark: TERRACOTTA_DARK,
      light: '#D4693F',
      contrastText: '#FFFFFF',
    },
    divider: '#E8E2D8',
    // Memory-type accents (muted to sit inside the warm theme)
    memory: {
      identity: '#6B5CA5',
      episodic: '#2E7D5B',
      emotional: TERRACOTTA,
    },
  },
  shape: {
    borderRadius: 12,
  },
  typography: {
    fontFamily: "'Outfit', system-ui, -apple-system, sans-serif",
    monoFamily: "'JetBrains Mono', 'Fira Code', monospace",
    h6: { fontWeight: 600, letterSpacing: '-0.2px' },
  },
  components: {
    MuiCssBaseline: {
      styleOverrides: {
        body: {
          backgroundColor: '#FAF9F5',
          // Viewport stability: dynamic viewport units, no page scroll
          minHeight: '100dvh',
          overflow: 'hidden',
        },
      },
    },
    MuiPaper: {
      styleOverrides: {
        root: {
          // Warm-tinted shadow instead of pure-black drop shadow
          boxShadow: '0 1px 2px rgba(62, 44, 28, 0.05), 0 4px 16px rgba(62, 44, 28, 0.06)',
        },
      },
    },
    MuiButton: {
      styleOverrides: {
        root: {
          borderRadius: 8,
          textTransform: 'none',
          fontWeight: 500,
        },
      },
    },
    MuiChip: {
      styleOverrides: {
        root: {
          fontWeight: 500,
        },
      },
    },
    // Tactile feedback on press (no motion library; transform-only)
    MuiIconButton: {
      styleOverrides: {
        root: {
          transition: 'transform 0.12s ease, background-color 0.12s ease',
          '&:active': { transform: 'scale(0.96)' },
        },
      },
    },
  },
})

export default theme
export { TERRACOTTA, TERRACOTTA_DARK }

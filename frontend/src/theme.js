import { createTheme } from '@mui/material/styles'

// ── Dark starlight theme ─────────────────────────────────────────────────────
// Deep-space surfaces, starlight-gold single accent, warm-gray text.
// Light-only by explicit brief (no switcher). Shape lock: cards 12px,
// buttons 8px, chips pill. Shadows tinted warm, never pure black.
const STARLIGHT = '#E3B76B'
const STARLIGHT_DEEP = '#B98A3E'

const theme = createTheme({
  palette: {
    mode: 'dark',
    background: {
      default: '#05070C', // deep space page
      paper: '#0B0E15',   // panel surface
    },
    text: {
      primary: '#EDF1F8',
      secondary: '#9AA3B5',
      disabled: '#5B6373',
    },
    primary: {
      main: STARLIGHT,
      dark: STARLIGHT_DEEP,
      light: '#F2D194',
      contrastText: '#1A1206',
    },
    divider: 'rgba(255, 255, 255, 0.08)',
    // Memory-type accents (muted to sit inside the night theme)
    memory: {
      identity: '#A78BFA',
      episodic: '#34D399',
      emotional: '#F5B453',
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
          backgroundColor: '#05070C',
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
          boxShadow: '0 1px 2px rgba(0, 0, 0, 0.4), 0 8px 28px rgba(0, 0, 0, 0.35)',
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
export { STARLIGHT, STARLIGHT_DEEP }

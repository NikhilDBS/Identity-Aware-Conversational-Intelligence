import { createTheme } from '@mui/material/styles'

// ── Buffer/orb theme ─────────────────────────────────────────────────────────
// Matches the GradientOrb loader: near-black space, nebula-violet single
// accent, ice-blue / emerald / ember memory tints. Shape lock: cards 12px,
// buttons 8px, chips pill. Shadows never pure black.
const NEBULA = '#9D7BFF'
const NEBULA_DEEP = '#6F5BD7'

const theme = createTheme({
  palette: {
    mode: 'dark',
    background: {
      default: '#0A0A0A', // orb canvas black
      paper: '#0D1017',   // panel base (used translucently over the sky)
    },
    text: {
      primary: '#EDF1F8',
      secondary: '#9AA3B5',
      disabled: '#5B6373',
    },
    primary: {
      main: NEBULA,
      dark: NEBULA_DEEP,
      light: '#C0B6FF',
      contrastText: '#0B0B12',
    },
    divider: 'rgba(255, 255, 255, 0.08)',
    // Memory-type accents (orb family: ice blue / emerald / ember orange)
    memory: {
      identity: '#6FC3FF',
      episodic: '#34D399',
      emotional: '#FF8A3D',
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
          backgroundColor: '#0A0A0A',
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
export { NEBULA as STARLIGHT, NEBULA_DEEP as STARLIGHT_DEEP }

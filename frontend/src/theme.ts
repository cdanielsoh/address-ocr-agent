import { createTheme } from '@mui/material/styles';

export const theme = createTheme({
  palette: {
    mode: 'light',
    primary: {
      main: '#2c2c2c',
      light: '#4f4f4f',
      dark: '#1a1a1a',
      contrastText: '#ffffff',
    },
    secondary: {
      main: '#6b6b6b',
      light: '#9e9e9e',
      dark: '#424242',
      contrastText: '#ffffff',
    },
    background: {
      default: '#f8f9fa',
      paper: '#ffffff',
    },
    text: {
      primary: '#2c2c2c',
      secondary: '#6b6b6b',
    },
    success: {
      main: '#4caf50',
      light: '#81c784',
      dark: '#388e3c',
    },
    warning: {
      main: '#ff9800',
      light: '#ffb74d',
      dark: '#f57c00',
    },
    error: {
      main: '#f44336',
      light: '#e57373',
      dark: '#d32f2f',
    },
    grey: {
      50: '#fafafa',
      100: '#f5f5f5',
      200: '#eeeeee',
      300: '#e0e0e0',
      400: '#bdbdbd',
      500: '#9e9e9e',
      600: '#757575',
      700: '#616161',
      800: '#424242',
      900: '#212121',
    },
  },
  typography: {
    fontFamily: '"Inter", "Roboto", "Helvetica", "Arial", sans-serif',
    h1: {
      fontWeight: 700,
      fontSize: '2.5rem',
      lineHeight: 1.2,
      color: '#2c2c2c',
    },
    h2: {
      fontWeight: 600,
      fontSize: '2rem',
      lineHeight: 1.3,
      color: '#2c2c2c',
    },
    h3: {
      fontWeight: 600,
      fontSize: '1.75rem',
      lineHeight: 1.4,
      color: '#2c2c2c',
    },
    h4: {
      fontWeight: 600,
      fontSize: '1.5rem',
      lineHeight: 1.4,
      color: '#2c2c2c',
    },
    h5: {
      fontWeight: 600,
      fontSize: '1.25rem',
      lineHeight: 1.5,
      color: '#2c2c2c',
    },
    h6: {
      fontWeight: 600,
      fontSize: '1.125rem',
      lineHeight: 1.5,
      color: '#2c2c2c',
    },
    body1: {
      fontSize: '1rem',
      lineHeight: 1.6,
      color: '#2c2c2c',
    },
    body2: {
      fontSize: '0.875rem',
      lineHeight: 1.6,
      color: '#6b6b6b',
    },
    button: {
      fontWeight: 600,
      textTransform: 'none',
    },
  },
  shape: {
    borderRadius: 12,
  },
  components: {
    MuiCard: {
      styleOverrides: {
        root: {
          boxShadow: '0 2px 8px rgba(0, 0, 0, 0.06)',
          border: '1px solid #e0e0e0',
          borderRadius: 12,
          transition: 'all 0.2s ease-in-out',
          '&:hover': {
            boxShadow: '0 4px 16px rgba(0, 0, 0, 0.1)',
            transform: 'translateY(-2px)',
          },
        },
      },
    },
    MuiButton: {
      styleOverrides: {
        root: {
          borderRadius: 8,
          padding: '8px 20px',
          fontWeight: 600,
          boxShadow: 'none',
          textTransform: 'none',
          '&:hover': {
            boxShadow: '0 2px 8px rgba(0, 0, 0, 0.15)',
          },
        },
        contained: {
          background: 'linear-gradient(135deg, #2c2c2c 0%, #1a1a1a 100%)',
          '&:hover': {
            background: 'linear-gradient(135deg, #1a1a1a 0%, #0d0d0d 100%)',
          },
        },
        outlined: {
          borderColor: '#e0e0e0',
          color: '#2c2c2c',
          '&:hover': {
            borderColor: '#2c2c2c',
            backgroundColor: 'rgba(44, 44, 44, 0.04)',
          },
        },
      },
    },
    MuiChip: {
      styleOverrides: {
        root: {
          borderRadius: 6,
          fontWeight: 500,
        },
        colorPrimary: {
          backgroundColor: '#2c2c2c',
          color: '#ffffff',
        },
        colorSecondary: {
          backgroundColor: '#f5f5f5',
          color: '#6b6b6b',
        },
      },
    },
    MuiTableCell: {
      styleOverrides: {
        head: {
          backgroundColor: '#f8f9fa',
          fontWeight: 600,
          color: '#2c2c2c',
        },
      },
    },
    MuiAlert: {
      styleOverrides: {
        root: {
          borderRadius: 8,
        },
      },
    },
  },
});
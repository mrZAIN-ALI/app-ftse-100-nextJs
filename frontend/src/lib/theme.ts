"use client"
import { createTheme } from "@mui/material/styles"

const theme = createTheme({
  palette: {
    mode: "light",
    primary: { main: "#1565c0" },   // modern blue
    secondary: { main: "#7c4dff" }, // accent
    background: { default: "#fafafa", paper: "#fff" }
  },
  shape: { borderRadius: 12 },
  typography: {
    fontFamily: `"Inter", "Roboto", "Helvetica", "Arial", sans-serif`,
    h4: { fontWeight: 700, letterSpacing: 0.2 },
    h6: { fontWeight: 600 }
  },
  components: {
    MuiButton: { defaultProps: { disableElevation: true }, styleOverrides: { root: { textTransform: "none" } } },
    MuiCard: { styleOverrides: { root: { borderRadius: 14 } } }
  }
})

export default theme

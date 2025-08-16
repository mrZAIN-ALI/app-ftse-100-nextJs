"use client";

import * as React from "react";
import { createTheme, CssBaseline, ThemeProvider } from "@mui/material";

type Mode = "light" | "dark";
type ThemeCtx = { mode: Mode; toggle: () => void };
const ThemeModeContext = React.createContext<ThemeCtx>({ mode: "light", toggle: () => {} });
export function useThemeMode() { return React.useContext(ThemeModeContext); }

export default function AppThemeProvider({ children }: { children: React.ReactNode }) {
  const [mode, setMode] = React.useState<Mode>("light");

  React.useEffect(() => {
    const saved = (typeof window !== "undefined" && localStorage.getItem("ftse-theme")) as Mode | null;
    if (saved === "light" || saved === "dark") setMode(saved);
  }, []);
  React.useEffect(() => {
    if (typeof window !== "undefined") localStorage.setItem("ftse-theme", mode);
  }, [mode]);

  const theme = React.useMemo(
    () =>
      createTheme({
        palette: { mode },
        shape: { borderRadius: 16 },
        components: {
          MuiButton: {
            styleOverrides: {
              root: { borderRadius: 14, textTransform: "none", fontWeight: 600 },
            },
          },
          MuiPaper: {
            styleOverrides: {
              root: { borderRadius: 16 },
            },
          },
          MuiListItemButton: {
            styleOverrides: {
              root: { borderRadius: 12 },
            },
          },
          MuiDrawer: {
            styleOverrides: {
              // ❗ no function per-prop; use a string or compute in the slot
              paper: {
                borderRight: "1px solid var(--mui-palette-divider)",
              },
            },
          },
        },
      }),
    [mode]
  );

  const ctx = React.useMemo<ThemeCtx>(() => ({ mode, toggle: () => setMode((m) => (m === "light" ? "dark" : "light")) }), [mode]);

  return (
    <ThemeModeContext.Provider value={ctx}>
      <ThemeProvider theme={theme}>
        <CssBaseline />
        {children}
      </ThemeProvider>
    </ThemeModeContext.Provider>
  );
}

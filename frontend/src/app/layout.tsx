import "./globals.css"
import Providers from "./providers"
import AppTopBar from "./components/AppTopBar"
import { CssBaseline, ThemeProvider } from "@mui/material"
import theme from "@/lib/theme"

export const metadata = { title: "FTSE100 Forecast" }

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <ThemeProvider theme={theme}>
          <CssBaseline />
          <Providers>
            <AppTopBar />
            {children}
          </Providers>
        </ThemeProvider>
      </body>
    </html>
  )
}

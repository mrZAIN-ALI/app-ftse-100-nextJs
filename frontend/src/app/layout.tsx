import './globals.css'
import Providers from './providers'
import AppTopBar from './components/AppTopBar'
import ThemeRegistry from './ThemeRegistry'

export const metadata = { title: 'FTSE100 Forecast' }

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <ThemeRegistry>
          <Providers>
            <AppTopBar />
            {children}
          </Providers>
        </ThemeRegistry>
      </body>
    </html>
  )
}

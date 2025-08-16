import type { Metadata } from "next";
// import ThemeRegistry from "@/ThemeRegistry";
import AppThemeProvider from "@/lib/theme/ThemeProvider";
import "./globals.css";
import ThemeRegistry from "./ThemeRegistry";

export const metadata: Metadata = {
  title: "ftse100 Forecast",
  description: "FTSE-100 predictions & backtests",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <ThemeRegistry>
          <AppThemeProvider>{children}</AppThemeProvider>
        </ThemeRegistry>
      </body>
    </html>
  );
}

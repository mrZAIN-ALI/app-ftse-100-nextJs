"use client"
import * as React from "react"
import { AppBar, Toolbar, Typography, Box, Button, Container } from "@mui/material"
import Link from "next/link"
import { usePathname } from "next/navigation"

const NavButton = ({ href, children }:{ href:string; children:React.ReactNode }) => {
  const path = usePathname()
  const active = path?.startsWith(href)
  return (
    <Button component={Link} href={href} color={active ? "secondary" : "inherit"} sx={{ fontWeight: active ? 700 : 500 }}>
      {children}
    </Button>
  )
}

export default function AppTopBar() {
  return (
    <AppBar position="sticky" color="primary">
      <Container maxWidth="lg">
        <Toolbar disableGutters sx={{ gap: 2 }}>
          <Typography variant="h6" sx={{ mr: 2, fontWeight: 800 }}>FTSE100</Typography>
          <Box sx={{ flexGrow: 1 }}>
            <NavButton href="/dashboard">Dashboard</NavButton>
            {/* placeholders for next steps */}
            <NavButton href="/history">History</NavButton>
            <NavButton href="/backtest">Backtest</NavButton>
          </Box>
          <Box>
            {/* auth later */}
          </Box>
        </Toolbar>
      </Container>
    </AppBar>
  )
}

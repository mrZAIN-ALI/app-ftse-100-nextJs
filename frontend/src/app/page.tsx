"use client"
import Link from "next/link"
import { Container, Stack, Button, Typography } from "@mui/material"

export default function Home() {
  return (
    <Container sx={{ mt: 8 }}>
      <Stack spacing={2}>
        <Typography variant="h4">FTSE100 Forecast</Typography>
        <Typography color="text.secondary">Next-day forecast on the FTSE 100 using an LSTM model.</Typography>
        <Button variant="contained" component={Link} href="/dashboard" sx={{ width: 220 }}>
          Open Dashboard
        </Button>
      </Stack>
    </Container>
  )
}

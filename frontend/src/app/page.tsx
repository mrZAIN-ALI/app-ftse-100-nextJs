'use client'
import { useState } from 'react'
import { Button, Container, Stack, Typography, Alert } from '@mui/material'

export default function Home() {
  const [msg, setMsg] = useState<string>('')

  const ping = async () => {
    setMsg('')
    try {
      const r = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/health`)
      const j = await r.json()
      if (!r.ok) throw new Error(JSON.stringify(j))
      setMsg(JSON.stringify(j))
    } catch (e:any) {
      setMsg(e.message)
    }
  }

  return (
    <Container sx={{ mt: 6 }}>
      <Stack spacing={2}>
        <Typography variant="h4">FTSE100 Forecast</Typography>
        <Button variant="contained" onClick={ping}>Ping backend</Button>
        {msg && (msg.startsWith('{') ? <code>{msg}</code> : <Alert severity="error">{msg}</Alert>)}
      </Stack>
    </Container>
  )
}

"use client"

import { useEffect, useMemo, useState } from "react"
import { Container, Stack, Card, CardContent, Typography, Button, Alert, Chip, Divider, Box } from "@mui/material"
import Grid from "@mui/material/Grid" // ✅ MUI v6 Grid2
import { LineChart, Line, XAxis, YAxis, Tooltip, CartesianGrid, ResponsiveContainer, ReferenceLine } from "recharts"
import { getOHLC, getPredict } from "@/lib/api"
import type { OhlcRow, PredictOut } from "@/lib/types"

export default function Dashboard() {
  const [rows, setRows] = useState<OhlcRow[]>([])
  const [pred, setPred] = useState<PredictOut | null>(null)
  const [err, setErr] = useState<string>("")
  const [info, setInfo] = useState<string>("")
  const [loading, setLoading] = useState<boolean>(false)

  const loadOHLC = async () => {
    setErr("")
    setInfo("")
    try {
      const data = await getOHLC()
      setRows(data.slice(-60))
      if (!data.length) setInfo("No market data returned yet. Try Refresh.")
    } catch (e: any) {
      setErr("Failed to load OHLC: " + e.message)
    }
  }

  useEffect(() => { loadOHLC() }, [])

  const onPredict = async () => {
    setErr("")
    setInfo("")
    setLoading(true)
    try {
      const p = await getPredict()
      setPred(p)
      setInfo("Forecast generated and saved to history.")
    } catch (e: any) {
      setErr("Predict failed: " + e.message)
    } finally {
      setLoading(false)
    }
  }

  const lastClose = rows.length ? rows[rows.length - 1].close : undefined
  const directionChip = useMemo(() => {
    if (!pred) return null
    const color = pred.direction === "UP" ? "success" : "error"
    return <Chip label={pred.direction} color={color as any} size="small" />
  }, [pred])

  return (
    <Container maxWidth="lg" sx={{ mt: 4, mb: 6 }}>
      <Stack spacing={3}>
        <Typography variant="h4">Dashboard</Typography>

        {err && <Alert severity="error">{err}</Alert>}
        {info && <Alert severity="info">{info}</Alert>}

        <Card>
          <CardContent>
            <Grid container spacing={3} alignItems="center">
              <Grid size={{ xs: 12, md: 8 }}>
                <Typography variant="h6" sx={{ mb: 1 }}>
                  Market Snapshot (last 60 trading days)
                </Typography>
                <div style={{ width: "100%", height: 340 }}>
                  {rows.length ? (
                    <ResponsiveContainer>
                      <LineChart data={rows}>
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis dataKey="date" hide />
                        <YAxis domain={["dataMin", "dataMax"]} />
                        <Tooltip />
                        <Line type="monotone" dataKey="close" dot={false} />
                        {pred && (
                          <>
                            <ReferenceLine y={pred.last_close} stroke="#9e9e9e" strokeDasharray="4 4" />
                            <ReferenceLine y={pred.predicted_close} stroke="#2e7d32" strokeDasharray="4 4" />
                          </>
                        )}
                      </LineChart>
                    </ResponsiveContainer>
                  ) : (
                    <Box
                      sx={{
                        height: 340,
                        border: "1px dashed",
                        borderColor: "divider",
                        borderRadius: 2,
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        color: "text.secondary"
                      }}
                    >
                      No chart data yet — click “Refresh Data”.
                    </Box>
                  )}
                </div>
              </Grid>

              <Grid size={{ xs: 12, md: 4 }}>
                <Stack spacing={1.2}>
                  <Typography variant="h6">Forecast</Typography>
                  <Stack direction="row" spacing={1} alignItems="center">
                    <Typography>Direction:</Typography>{directionChip || <Typography color="text.secondary">—</Typography>}
                  </Stack>
                  <Typography>Last close: {lastClose ? lastClose.toFixed(2) : "—"}</Typography>
                  <Typography>Predicted close: {pred ? pred.predicted_close.toFixed(2) : "—"}</Typography>
                  <Typography>Signal: {pred ? pred.signal : "—"}</Typography>
                  <Typography>Band: {pred ? `[${pred.band_lower.toFixed(2)} – ${pred.band_upper.toFixed(2)}]` : "—"}</Typography>
                  <Divider sx={{ my: 1 }} />
                  <Stack direction="row" spacing={2}>
                    <Button variant="contained" onClick={onPredict} disabled={loading}>
                      {loading ? "Predicting..." : "Predict"}
                    </Button>
                    <Button variant="outlined" onClick={loadOHLC}>Refresh Data</Button>
                  </Stack>
                  <Typography variant="body2" color="text.secondary">
                    Model: {pred?.model_version || "—"} | Scaler: {pred?.scaler_version || "—"}
                  </Typography>
                </Stack>
              </Grid>
            </Grid>
          </CardContent>
        </Card>
      </Stack>
    </Container>
  )
}

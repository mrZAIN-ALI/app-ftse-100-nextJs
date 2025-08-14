"use client"

import { useEffect, useState } from "react"
import { Container, Stack, Typography, Button, Alert } from "@mui/material"
import { DataGrid, GridColDef, GridToolbar } from "@mui/x-data-grid"
import { listPredictions, reconcile } from "@/lib/api"

const columns: GridColDef[] = [
  { field: "generated_at", headerName: "Generated", flex: 1, valueGetter: v => new Date(v.value).toLocaleString() },
  { field: "prediction_for", headerName: "For Date", flex: 1 },
  { field: "last_close", headerName: "Last", flex: 0.8, valueFormatter: p => p.value?.toFixed(2) },
  { field: "predicted_close", headerName: "Pred", flex: 0.8, valueFormatter: p => p.value?.toFixed(2) },
  { field: "actual_close", headerName: "Actual", flex: 0.8, valueFormatter: p => p.value?.toFixed(2) },
  { field: "abs_error", headerName: "Abs Err", flex: 0.7, valueFormatter: p => p.value?.toFixed(4) },
  { field: "pct_error", headerName: "% Err", flex: 0.7, valueFormatter: p => p.value ? (p.value*100).toFixed(2)+"%" : "" },
  { field: "direction_pred", headerName: "Dir", flex: 0.6 },
  { field: "direction_hit", headerName: "Hit?", flex: 0.6 },
  { field: "signal", headerName: "Signal", flex: 0.8 },
]

export default function HistoryPage() {
  const [rows, setRows] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [err, setErr] = useState<string>("")
  const [info, setInfo] = useState<string>("")

  const load = async () => {
    setErr(""); setInfo("")
    try {
      const r = await listPredictions()
      setRows(r.map((x:any) => ({ id: x.id, ...x })))
    } catch (e:any) {
      setErr("Failed to load history: " + e.message)
    }
  }

  useEffect(() => { load() }, [])

  const onReconcile = async () => {
    setLoading(true); setErr(""); setInfo("")
    try {
      const res = await reconcile()
      setInfo(`Updated ${res.updated} rows`)
      await load()
    } catch (e:any) {
      setErr("Reconcile failed: " + e.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <Container maxWidth="lg" sx={{ mt: 4, mb: 6 }}>
      <Stack spacing={2}>
        <Typography variant="h4">History</Typography>
        {err && <Alert severity="error">{err}</Alert>}
        {info && <Alert severity="success">{info}</Alert>}
        <Stack direction="row" spacing={2}>
          <Button variant="contained" onClick={onReconcile} disabled={loading}>
            {loading ? "Reconciling..." : "Reconcile Actuals"}
          </Button>
          <Button variant="outlined" onClick={load}>Refresh</Button>
        </Stack>
        <div style={{ height: 620, width: "100%" }}>
          <DataGrid
            rows={rows}
            columns={columns}
            slots={{ toolbar: GridToolbar }}
            disableRowSelectionOnClick
          />
        </div>
      </Stack>
    </Container>
  )
}

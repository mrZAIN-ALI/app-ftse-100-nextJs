'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Alert,
  Box,
  Button,
  Chip,
  Container,
  Paper,
  Stack,
  TextField,
  Typography,
} from '@mui/material';
import {
  DataGrid,
  GridColDef,
  GridRenderCellParams,
  GridToolbar,
} from '@mui/x-data-grid';

type PredRow = {
  id: string;
  generated_at?: string | null;
  window_start?: string | null;
  window_end?: string | null;
  prediction_for?: string | null;
  last_close?: number | null;
  predicted_close?: number | null;
  actual_close?: number | null;
  direction_pred?: 'UP' | 'DOWN' | null;
  direction_hit?: boolean | null;
  abs_error?: number | null;
  pct_error?: number | null; // 0.0123 => 1.23%
  band_lower?: number | null;
  band_upper?: number | null;
  signal?: 'LONG' | 'SHORT' | 'NO_TRADE' | null;
  model_version?: string | null;
  scaler_version?: string | null;
};

type ApiResponse = {
  success: boolean;
  count: number;
  offset: number;
  limit: number;
  data: PredRow[];
};

const BACKEND = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';

function fmtNum(v: number | null | undefined, dps = 2) {
  if (v == null || Number.isNaN(Number(v))) return '—';
  return Number(v).toLocaleString(undefined, {
    minimumFractionDigits: dps,
    maximumFractionDigits: dps,
  });
}

const columns: GridColDef<PredRow>[] = [
  {
    field: 'generated_at',
    headerName: 'Generated',
    flex: 1,
    renderCell: (p: GridRenderCellParams<PredRow, string | null | undefined>) => (
      <span>{p.value ? new Date(p.value).toLocaleString() : ''}</span>
    ),
  },
  {
    field: 'prediction_for',
    headerName: 'For Date',
    flex: 0.9,
    renderCell: (p: GridRenderCellParams<PredRow, string | null | undefined>) => (
      <span>{p.value || ''}</span>
    ),
  },
  {
    field: 'last_close',
    headerName: 'Last',
    flex: 0.7,
    renderCell: (p: GridRenderCellParams<PredRow, number | null | undefined>) => (
      <span>{fmtNum(p.value as number, 2)}</span>
    ),
  },
  {
    field: 'predicted_close',
    headerName: 'Pred',
    flex: 0.7,
    renderCell: (p: GridRenderCellParams<PredRow, number | null | undefined>) => (
      <span>{fmtNum(p.value as number, 2)}</span>
    ),
  },
  {
    field: 'actual_close',
    headerName: 'Actual',
    flex: 0.7,
    renderCell: (p: GridRenderCellParams<PredRow, number | null | undefined>) => (
      <span>{fmtNum(p.value as number, 2)}</span>
    ),
  },
  {
    field: 'abs_error',
    headerName: 'Abs Err',
    flex: 0.7,
    renderCell: (p: GridRenderCellParams<PredRow, number | null | undefined>) => (
      <span>{fmtNum(p.value as number, 4)}</span>
    ),
  },
  {
    field: 'pct_error',
    headerName: '% Err',
    flex: 0.7,
    renderCell: (p: GridRenderCellParams<PredRow, number | null | undefined>) => {
      const v = p.value;
      return <span>{v == null ? '—' : `${(Number(v) * 100).toFixed(2)}%`}</span>;
    },
  },
  {
    field: 'direction_pred',
    headerName: 'Dir',
    flex: 0.6,
    renderCell: (p: GridRenderCellParams<PredRow, 'UP' | 'DOWN' | null | undefined>) => {
      const v = p.value;
      if (!v) return <span>—</span>;
      return (
        <Chip
          size="small"
          label={v}
          color={v === 'UP' ? 'success' : 'error'}
          variant="outlined"
        />
      );
    },
  },
  {
    field: 'direction_hit',
    headerName: 'Hit?',
    flex: 0.6,
    renderCell: (p: GridRenderCellParams<PredRow, boolean | null | undefined>) => {
      const v = p.value;
      if (v == null) return <span>—</span>;
      return (
        <Chip
          size="small"
          label={v ? 'YES' : 'NO'}
          color={v ? 'success' : 'error'}
          variant="filled"
        />
      );
    },
  },
  {
    field: 'signal',
    headerName: 'Signal',
    flex: 0.8,
    renderCell: (p: GridRenderCellParams<PredRow, 'LONG' | 'SHORT' | 'NO_TRADE' | null | undefined>) => {
      const v = p.value || 'NO_TRADE';
      const color: 'default' | 'success' | 'error' =
        v === 'LONG' ? 'success' : v === 'SHORT' ? 'error' : 'default';
      return <Chip size="small" label={v} color={color} variant="outlined" />;
    },
  },
];

export default function HistoryPage() {
  const [rows, setRows] = useState<PredRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string>('');
  const [info, setInfo] = useState<string>('');
  const [limit, setLimit] = useState<number>(100);
  const [offset, setOffset] = useState<number>(0);
  const [start, setStart] = useState<string>(''); // yyyy-mm-dd
  const [end, setEnd] = useState<string>(''); // yyyy-mm-dd

  const csvUrl = useMemo(() => {
    const u = new URL(`${BACKEND}/history`);
    u.searchParams.set('limit', String(limit));
    u.searchParams.set('offset', String(offset));
    if (start) u.searchParams.set('start', start);
    if (end) u.searchParams.set('end', end);
    u.searchParams.set('format', 'csv');
    return u.toString();
  }, [limit, offset, start, end]);

  const fetchRows = useCallback(async () => {
    setErr('');
    setLoading(true);
    try {
      const url = new URL(`${BACKEND}/history`);
      url.searchParams.set('limit', String(limit));
      url.searchParams.set('offset', String(offset));
      if (start) url.searchParams.set('start', start);
      if (end) url.searchParams.set('end', end);
      const res = await fetch(url.toString(), { cache: 'no-store' });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data: ApiResponse = await res.json();
      setRows((data?.data || []).map((x, i) => ({
        ...x,
        id: String(x.id ?? `row-${i}`), // ensure stable string id; no duplicates
      })));
    } catch (e: any) {
      setErr(`Failed to load history: ${e.message || e}`);
      setRows([]);
    } finally {
      setLoading(false);
    }
  }, [limit, offset, start, end]);

  const onReconcile = useCallback(async () => {
    setLoading(true);
    setErr('');
    setInfo('');
    try {
      // Prefer POST; fallback to GET if needed
      let res = await fetch(`${BACKEND}/reconcile`, { method: 'POST' });
      if (!res.ok) res = await fetch(`${BACKEND}/reconcile`);
      if (!res.ok) throw new Error(`Reconcile failed (HTTP ${res.status})`);
      const data = await res.json().catch(() => ({}));
      const updated = data?.updated ?? data?.count ?? 'OK';
      setInfo(`Reconciled: ${updated}`);
      await fetchRows();
    } catch (e: any) {
      setErr(`Reconcile failed: ${e.message || e}`);
    } finally {
      setLoading(false);
    }
  }, [fetchRows]);

  useEffect(() => {
    fetchRows();
  }, [fetchRows]);

  return (
    <Container maxWidth="lg" sx={{ mt: 4, mb: 6 }}>
      <Stack spacing={2}>
        <Typography variant="h4" sx={{ color: 'text.primary' }}>
          History
        </Typography>

        {err && <Alert severity="error">{err}</Alert>}
        {info && <Alert severity="success">{info}</Alert>}

        {/* Filters in a Paper to ensure contrast on dark backgrounds */}
        <Paper
          elevation={1}
          sx={{
            p: 2,
            bgcolor: 'background.paper',
            color: 'text.primary',
          }}
        >
          <Stack
            direction={{ xs: 'column', sm: 'row' }}
            spacing={2}
            alignItems="center"
          >
            <TextField
              label="Start"
              type="date"
              value={start}
              onChange={(e) => setStart(e.target.value)}
              InputLabelProps={{ shrink: true }}
              size="small"
              sx={{
                minWidth: { xs: '100%', sm: 160 },
                '& .MuiInputBase-input': { color: 'text.primary' },
                '& .MuiInputLabel-root': { color: 'text.secondary' },
                '& .MuiOutlinedInput-notchedOutline': { borderColor: 'divider' },
              }}
            />
            <TextField
              label="End"
              type="date"
              value={end}
              onChange={(e) => setEnd(e.target.value)}
              InputLabelProps={{ shrink: true }}
              size="small"
              sx={{
                minWidth: { xs: '100%', sm: 160 },
                '& .MuiInputBase-input': { color: 'text.primary' },
                '& .MuiInputLabel-root': { color: 'text.secondary' },
                '& .MuiOutlinedInput-notchedOutline': { borderColor: 'divider' },
              }}
            />
            <TextField
              label="Limit"
              type="number"
              value={limit}
              onChange={(e) =>
                setLimit(Math.max(1, Math.min(500, Number(e.target.value) || 1)))
              }
              InputProps={{ inputProps: { min: 1, max: 500 } }}
              size="small"
              sx={{
                width: 120,
                '& .MuiInputBase-input': { color: 'text.primary' },
                '& .MuiInputLabel-root': { color: 'text.secondary' },
                '& .MuiOutlinedInput-notchedOutline': { borderColor: 'divider' },
              }}
            />
            <TextField
              label="Offset"
              type="number"
              value={offset}
              onChange={(e) => setOffset(Math.max(0, Number(e.target.value) || 0))}
              InputProps={{ inputProps: { min: 0 } }}
              size="small"
              sx={{
                width: 120,
                '& .MuiInputBase-input': { color: 'text.primary' },
                '& .MuiInputLabel-root': { color: 'text.secondary' },
                '& .MuiOutlinedInput-notchedOutline': { borderColor: 'divider' },
              }}
            />

            <Button variant="contained" onClick={fetchRows} disabled={loading}>
              {loading ? 'Loading…' : 'Apply'}
            </Button>
            <Button variant="outlined" component="a" href={csvUrl}>
              Download CSV
            </Button>
            <Button variant="outlined" onClick={onReconcile} disabled={loading}>
              {loading ? 'Reconciling…' : 'Reconcile Actuals'}
            </Button>
          </Stack>
        </Paper>

        {/* Grid container with explicit height so DataGrid is never 0px */}
        <Box
          sx={{
            height: { xs: 520, md: 'calc(100vh - 260px)' },
            minHeight: 520,
            width: '100%',
          }}
        >
          <DataGrid
            rows={rows}
            columns={columns}
            loading={loading}
            disableRowSelectionOnClick
            slots={{ toolbar: GridToolbar }}
            slotProps={{
              toolbar: {
                showQuickFilter: true,
                quickFilterProps: { debounceMs: 300 },
              },
            }}
            initialState={{
              sorting: { sortModel: [{ field: 'generated_at', sort: 'desc' }] },
              pagination: { paginationModel: { pageSize: 25 } },
            }}
            pageSizeOptions={[10, 25, 50, 100]}
            sx={{
              height: '100%',                // make grid fill the Box
              bgcolor: 'background.paper',   // readable on dark backgrounds
              color: 'text.primary',
              '& .MuiDataGrid-columnHeaders': {
                bgcolor: 'background.default',
              },
              '& .MuiDataGrid-cell': {
                color: 'text.primary',
              },
              '& .MuiDataGrid-toolbarContainer .MuiButtonBase-root': {
                color: 'text.primary',
              },
              '& .MuiSvgIcon-root': {
                color: 'text.primary',
              },
              '& .MuiInputBase-input': {
                color: 'text.primary',
              },
            }}
          />
        </Box>
      </Stack>
    </Container>
  );
}

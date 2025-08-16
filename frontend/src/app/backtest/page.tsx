'use client';

import { useCallback, useMemo, useState } from 'react';
import {
  Alert, Box, Button, Container, Paper, Stack, TextField, Typography, Chip
} from '@mui/material';
import {
  LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid,
} from 'recharts';

type BacktestSeries = {
  dates: (string | null)[];
  cum_pl_points: (number | null)[];
  cum_return_pct: (number | null)[];
  rolling_directional_accuracy_pct: (number | null)[];
  rolling_rmse: (number | null)[];
};

type BacktestResponse = {
  success: boolean;
  summary: Record<string, number | string | null>;
  series: BacktestSeries;
  table: Array<Record<string, any>>;
};

type PointResponse = {
  success: boolean;
  target_date: string;
  lookback: number;
  last_close: number;
  predicted_close: number;
  actual_close: number;
  direction_pred: 'UP' | 'DOWN';
  direction_hit: boolean;
  abs_error: number;
  pct_error: number;        // %
  accuracy_pct: number;     // %
  trade_points: number;
  trade_return_pct: number; // %
};

const BACKEND = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';

function allNullOrZero(arr?: (number | null)[]) {
  if (!arr || arr.length === 0) return true;
  return arr.every((v) => v == null || Math.abs(Number(v)) < 1e-9);
}

function fmtNumber(n: number | string | null | undefined, decimals = 2) {
  if (n === null || n === undefined) return '—';
  const num = Number(n);
  if (Number.isNaN(num)) return String(n);
  return num.toFixed(decimals);
}

export default function BacktestPage() {
  const [mode, setMode] = useState<'single' | 'range'>('single');

  // single-day
  const [target, setTarget] = useState('');

  // range
  const [start, setStart] = useState('');
  const [end, setEnd] = useState('');
  const [window, setWindow] = useState(7);

  const [data, setData] = useState<BacktestResponse | null>(null);
  const [point, setPoint] = useState<PointResponse | null>(null);
  const [err, setErr] = useState('');
  const [loading, setLoading] = useState(false);

  const run = useCallback(async () => {
    setErr('');
    setLoading(true);
    try {
      if (mode === 'single') {
        if (!target) throw new Error('Pick a target date');
        const url = new URL(`${BACKEND}/backtest/point`);
        url.searchParams.set('target', target);
        url.searchParams.set('lookback', '60');
        const res = await fetch(url.toString(), { cache: 'no-store' });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const payload: PointResponse = await res.json();
        setPoint(payload);
        setData(null);
      } else {
        const url = new URL(`${BACKEND}/backtest`);
        if (start) url.searchParams.set('start', start);
        if (end) url.searchParams.set('end', end);
        url.searchParams.set('window', String(window));
        const res = await fetch(url.toString(), { cache: 'no-store' });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const payload: BacktestResponse = await res.json();
        setData(payload);
        setPoint(null);
      }
    } catch (e: any) {
      setErr(e.message || String(e));
      setData(null);
      setPoint(null);
    } finally {
      setLoading(false);
    }
  }, [mode, target, start, end, window]);

  const chartRows = useMemo(() => {
    if (!data?.series?.dates) return [];
    const s = data.series;
    return s.dates.map((d, i) => ({
      date: d ?? '',
      cum_pl_points: s.cum_pl_points?.[i] ?? null,
      cum_return_pct: s.cum_return_pct?.[i] ?? null,
      rolling_acc: s.rolling_directional_accuracy_pct?.[i] ?? null,
      rolling_rmse: s.rolling_rmse?.[i] ?? null,
    }));
  }, [data]);

  // single indicator values
  const singleAccuracy = point?.accuracy_pct ?? null;
  const rangeAccuracy =
    (data?.summary?.Avg_Accuracy_pct as number | undefined) ??
    (data?.summary?.avg_accuracy_pct as number | undefined) ?? null;

  // Only show selected summary keys
  const allowedSummaryKeys = new Set([
    'count', 'MAE', 'RMSE', 'MAPE_pct', 'Avg_Accuracy_pct', 'Directional_Accuracy_pct',
    'Naive_MAE', 'Naive_RMSE', 'Window'
  ]);
  const filteredSummary = Object.fromEntries(
    Object.entries(data?.summary || {}).filter(([k]) => allowedSummaryKeys.has(k))
  );
  const s = data?.series;

  return (
    <Container maxWidth="lg" sx={{ mt: 4, mb: 6 }}>
      <Stack spacing={2}>
        <Typography variant="h4">Backtest</Typography>
        {err && <Alert severity="error">{err}</Alert>}

        <Paper sx={{ p: 2 }}>
          <Stack direction={{ xs: 'column', lg: 'row' }} spacing={2} alignItems="center">
            <TextField
              select
              label="Mode"
              value={mode}
              onChange={(e) => setMode((e.target.value as 'single' | 'range') || 'single')}
              size="small"
              sx={{ width: 160 }}
              SelectProps={{ native: true }}
            >
              <option value="single">Single day</option>
              <option value="range">Range</option>
            </TextField>

            {mode === 'single' ? (
              <>
                <TextField
                  label="Target date"
                  type="date"
                  value={target}
                  onChange={(e) => setTarget(e.target.value)}
                  InputLabelProps={{ shrink: true }}
                  size="small"
                />
                <Chip
                  label={singleAccuracy == null ? 'Accuracy —' : `Accuracy ${fmtNumber(singleAccuracy)}%`}
                  color="primary"
                  variant="outlined"
                  sx={{ height: 32, fontWeight: 600 }}
                />
              </>
            ) : (
              <>
                <TextField
                  label="Start"
                  type="date"
                  value={start}
                  onChange={(e) => setStart(e.target.value)}
                  InputLabelProps={{ shrink: true }}
                  size="small"
                />
                <TextField
                  label="End"
                  type="date"
                  value={end}
                  onChange={(e) => setEnd(e.target.value)}
                  InputLabelProps={{ shrink: true }}
                  size="small"
                />
                <TextField
                  label="Rolling Window"
                  type="number"
                  value={window}
                  onChange={(e) => setWindow(Math.max(2, Math.min(60, Number(e.target.value) || 7)))}
                  size="small"
                  sx={{ width: 160 }}
                />
                <Chip
                  label={rangeAccuracy == null ? 'Accuracy —' : `Accuracy ${fmtNumber(rangeAccuracy)}%`}
                  color="primary"
                  variant="outlined"
                  sx={{ height: 32, fontWeight: 600 }}
                />
              </>
            )}

            <Button variant="contained" onClick={run} disabled={loading}>
              {loading ? 'Running…' : 'Run Backtest'}
            </Button>
          </Stack>
        </Paper>

        {/* Single-day result */}
        {point && (
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>Single-day result — {point.target_date}</Typography>
            <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr 1fr', md: 'repeat(4, 1fr)' }, gap: 2 }}>
              {[
                ['Last', fmtNumber(point.last_close, 4)],
                ['Predicted', fmtNumber(point.predicted_close, 4)],
                ['Actual', fmtNumber(point.actual_close, 4)],
                ['Dir', point.direction_pred],
                ['Hit?', point.direction_hit ? 'YES' : 'NO'],
                ['Abs Err', fmtNumber(point.abs_error, 4)],
                ['Pct Err', `${fmtNumber(point.pct_error)}%`],
                ['Accuracy %', `${fmtNumber(point.accuracy_pct)}%`],
                ['Trade Pts', fmtNumber(point.trade_points, 4)],
                ['Trade %', `${fmtNumber(point.trade_return_pct)}%`],
              ].map(([k, v]) => (
                <Box key={k as string} sx={{ p: 1, borderRadius: 1, bgcolor: 'background.default', border: '1px solid', borderColor: 'divider' }}>
                  <Typography variant="caption" color="text.secondary">{k}</Typography>
                  <Typography variant="body1" fontWeight={600}>{String(v)}</Typography>
                </Box>
              ))}
            </Box>
          </Paper>
        )}

        {/* Range results with charts */}
        {!!data && (
          <>
            <Paper sx={{ p: 2 }}>
              <Typography variant="h6" gutterBottom>Summary</Typography>
              <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr 1fr', md: 'repeat(4, 1fr)' }, gap: 2 }}>
                {Object.entries(filteredSummary).map(([k, v]) => (
                  <Box key={k} sx={{ p: 1, borderRadius: 1, bgcolor: 'background.default', border: '1px solid', borderColor: 'divider' }}>
                    <Typography variant="caption" color="text.secondary">{k}</Typography>
                    <Typography variant="body1" fontWeight={600}>
                      {v === null || v === undefined ? '—' : String(v)}
                    </Typography>
                  </Box>
                ))}
              </Box>
            </Paper>

            <Paper sx={{ p: 2 }}>
              <Typography variant="h6" mb={1}>Cumulative P/L (points)</Typography>
              <Box sx={{ height: 320, position: 'relative' }}>
                {allNullOrZero(s?.cum_pl_points) && (
                  <Box sx={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'text.secondary', zIndex: 1 }}>
                    No movement yet (try a wider date range)
                  </Box>
                )}
                <ResponsiveContainer>
                  <LineChart data={chartRows}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="date" />
                    <YAxis />
                    <Tooltip />
                    <Line type="monotone" dataKey="cum_pl_points" dot={false} connectNulls />
                  </LineChart>
                </ResponsiveContainer>
              </Box>
            </Paper>

            <Paper sx={{ p: 2 }}>
              <Typography variant="h6" mb={1}>Cumulative Return (%)</Typography>
              <Box sx={{ height: 320 }}>
                <ResponsiveContainer>
                  <LineChart data={chartRows}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="date" />
                    <YAxis />
                    <Tooltip />
                    <Line type="monotone" dataKey="cum_return_pct" dot={false} connectNulls />
                  </LineChart>
                </ResponsiveContainer>
              </Box>
            </Paper>

            <Paper sx={{ p: 2 }}>
              <Typography variant="h6" mb={1}>Rolling Directional Accuracy (%)</Typography>
              <Box sx={{ height: 320 }}>
                <ResponsiveContainer>
                  <LineChart data={chartRows}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="date" />
                    <YAxis domain={[0, 100]} />
                    <Tooltip />
                    <Line type="monotone" dataKey="rolling_acc" dot={false} connectNulls />
                  </LineChart>
                </ResponsiveContainer>
              </Box>
            </Paper>

            <Paper sx={{ p: 2 }}>
              <Typography variant="h6" mb={1}>Rolling RMSE</Typography>
              <Box sx={{ height: 320 }}>
                <ResponsiveContainer>
                  <LineChart data={chartRows}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="date" />
                    <YAxis />
                    <Tooltip />
                    <Line type="monotone" dataKey="rolling_rmse" dot={false} connectNulls />
                  </LineChart>
                </ResponsiveContainer>
              </Box>
            </Paper>
          </>
        )}
      </Stack>
    </Container>
  );
}

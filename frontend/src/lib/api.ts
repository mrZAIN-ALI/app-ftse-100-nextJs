import type { OhlcRow, PredictOut } from "@/lib/types"

const BASE = process.env.NEXT_PUBLIC_API_URL!

export async function getOHLC(): Promise<OhlcRow[]> {
  const r = await fetch(`${BASE}/ohlc`, { cache: "no-store" })
  if (!r.ok) throw new Error("ohlc_failed")
  const j = await r.json()
  return j.rows as OhlcRow[]
}

export async function getPredict(): Promise<PredictOut> {
  const r = await fetch(`${BASE}/predict`)
  const j = await r.json()
  if (!r.ok) throw new Error(j?.detail || "predict_failed")
  return j as PredictOut
}

export async function listPredictions() {
  const r = await fetch(`${BASE}/predictions`, { cache: "no-store" })
  const j = await r.json()
  if (!r.ok) throw new Error("history_failed")
  return j.rows as any[]
}

export async function reconcile() {
  const r = await fetch(`${BASE}/reconcile`, { method: "POST" })
  const j = await r.json()
  if (!r.ok) throw new Error("reconcile_failed")
  return j as { updated: number }
}

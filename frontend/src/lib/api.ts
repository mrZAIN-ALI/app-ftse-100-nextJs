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

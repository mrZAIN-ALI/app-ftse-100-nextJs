export type OhlcRow = {
  date: string
  open: number
  high: number
  low: number
  close: number
  volume: number
}

export type PredictOut = {
  last_close: number
  predicted_close: number
  direction: "UP" | "DOWN"
  band_lower: number
  band_upper: number
  signal: "LONG" | "SHORT" | "NO_TRADE"
  window_start: string
  window_end: string
  prediction_for: string
  model_version?: string
  scaler_version?: string
}

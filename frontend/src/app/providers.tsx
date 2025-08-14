"use client"
import * as React from "react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"

const qc = new QueryClient()
export default function Providers({ children }: { children: React.ReactNode }) {
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

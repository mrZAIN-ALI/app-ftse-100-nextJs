'use client'

import * as React from 'react'
import { useServerInsertedHTML } from 'next/navigation'
import { CacheProvider } from '@emotion/react'
import createCache from '@emotion/cache'
import { CssBaseline, ThemeProvider } from '@mui/material'
import theme from '@/lib/theme'

function createEmotionCache() {
  const cache = createCache({ key: 'mui', prepend: true })
  cache.compat = true
  return cache
}

export default function ThemeRegistry({ children }: { children: React.ReactNode }) {
  const [cache] = React.useState(() => {
    const c = createEmotionCache()
    const prevInsert = c.insert
    let inserted: string[] = []
    c.insert = (...args: any[]) => {
      const serialized = args[1]
      if (c.inserted[serialized.name] === undefined) {
        inserted.push(serialized.name)
      }
      // @ts-ignore
      return prevInsert(...args)
    }
    // @ts-ignore
    c.inserted = c.inserted || {}
    // Expose the list on the cache for server pass
    // @ts-ignore
    c.__inserted = inserted
    return c
  })

  useServerInsertedHTML(() => {
    // @ts-ignore
    const names: string[] = cache.__inserted || []
    // @ts-ignore
    cache.__inserted = []
    if (names.length === 0) return null
    return (
      <style
        data-emotion={`mui ${names.join(' ')}`}
        // @ts-ignore
        dangerouslySetInnerHTML={{ __html: Object.values(cache.inserted).join(' ') }}
      />
    )
  })

  return (
    <CacheProvider value={cache}>
      <ThemeProvider theme={theme}>
        <CssBaseline />
        {children}
      </ThemeProvider>
    </CacheProvider>
  )
}

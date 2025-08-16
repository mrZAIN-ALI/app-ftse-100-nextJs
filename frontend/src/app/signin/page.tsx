// frontend/src/app/signin/page.tsx
'use client'

import * as React from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import Container from '@mui/material/Container'
import Paper from '@mui/material/Paper'
import Typography from '@mui/material/Typography'
import Stack from '@mui/material/Stack'
import Alert from '@mui/material/Alert'
import Snackbar from '@mui/material/Snackbar'
import Divider from '@mui/material/Divider'
import Box from '@mui/material/Box'
import { LoadingButton } from '@mui/lab'
import GoogleIcon from '@mui/icons-material/Google'
import { createClientSupabase } from '@/lib/supabase/client'

export default function SignInPage() {
  const router = useRouter()
  const supabase = React.useMemo(() => createClientSupabase(), [])
  const searchParams = useSearchParams()
  const [loading, setLoading] = React.useState(false)
  const [snack, setSnack] = React.useState<{ open: boolean; msg: string }>({ open: false, msg: '' })

  // Nicety: if already signed in, bounce to dashboard
  React.useEffect(() => {
    ;(async () => {
      const { data: { session } } = await supabase.auth.getSession()
      if (session) router.replace('/dashboard')
    })()
  }, [router, supabase])

  React.useEffect(() => {
    const err = searchParams.get('err')
    if (err) setSnack({ open: true, msg: decodeURIComponent(err) })
  }, [searchParams])

  const handleGoogle = async () => {
    try {
      setLoading(true)
      const origin = window.location.origin
      const next = searchParams.get('next') || searchParams.get('redirectedFrom') || '/dashboard'

      const { error } = await supabase.auth.signInWithOAuth({
        provider: 'google',
        options: {
          redirectTo: `${origin}/auth/callback?next=${encodeURIComponent(next)}`,
          queryParams: {
            prompt: 'consent',
            access_type: 'offline',
          },
        },
      })

      if (error) {
        setSnack({ open: true, msg: error.message || 'Sign-in failed' })
        setLoading(false)
      }
      // on success, browser redirects to Google → back to /auth/callback
    } catch (e: any) {
      setSnack({ open: true, msg: e?.message ?? 'Unexpected error' })
      setLoading(false)
    }
  }

  return (
    <Container maxWidth="sm" sx={{ py: { xs: 6, md: 10 } }}>
      <Paper elevation={3} sx={{ p: { xs: 3, md: 4 }, borderRadius: 3 }}>
        <Stack spacing={2}>
          <Typography variant="h4" fontWeight={700}>ftse100 Forecast</Typography>
          <Typography variant="body1" color="text.secondary">
            Sign in to continue. We currently support Google sign-in.
          </Typography>
          <Divider sx={{ my: 1 }} />
          <LoadingButton
            onClick={handleGoogle}
            variant="contained"
            startIcon={<GoogleIcon />}
            loading={loading}
            disabled={loading}
            sx={{ py: 1.25, textTransform: 'none', fontSize: 16, fontWeight: 600 }}
            fullWidth
          >
            Continue with Google
          </LoadingButton>
          <Box sx={{ mt: 1 }}>
            <Alert severity="info" variant="outlined">
              By continuing, you create a secure session with your Google account.
            </Alert>
          </Box>
        </Stack>
      </Paper>

      <Snackbar
        open={snack.open}
        autoHideDuration={4000}
        onClose={() => setSnack((s) => ({ ...s, open: false }))}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        <Alert
          severity="error"
          onClose={() => setSnack((s) => ({ ...s, open: false }))}
          variant="filled"
          sx={{ width: '100%' }}
        >
          {snack.msg}
        </Alert>
      </Snackbar>
    </Container>
  )
}

"use client";
import Box from "@mui/material/Box";
import CircularProgress from "@mui/material/CircularProgress";

export default function SignInLoading() {
  return (
    <Box sx={{ minHeight: "60vh", display: "grid", placeItems: "center" }}>
      <CircularProgress />
    </Box>
  );
}

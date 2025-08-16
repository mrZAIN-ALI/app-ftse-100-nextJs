"use client";
import LinearProgress from "@mui/material/LinearProgress";

export default function ProtectedLoading() {
  return (
    <LinearProgress
      sx={{ position: "fixed", left: 0, right: 0, top: 0, zIndex: 2000, height: 3 }}
    />
  );
}

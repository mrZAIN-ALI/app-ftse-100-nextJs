"use client";

import * as React from "react";
import Link from "next/link";
import { useRouter, usePathname } from "next/navigation";
import {
  AppBar, Toolbar, IconButton, Typography, Box, Drawer, List, ListItemButton, ListItemIcon, ListItemText,
  Divider, Avatar, Tooltip, Stack, useMediaQuery, Theme, Button, Paper
} from "@mui/material";
import { LoadingButton } from "@mui/lab";
import MenuIcon from "@mui/icons-material/Menu";
import ChevronLeftIcon from "@mui/icons-material/ChevronLeft";
import ChevronRightIcon from "@mui/icons-material/ChevronRight";
import DashboardIcon from "@mui/icons-material/Dashboard";
import QueryStatsIcon from "@mui/icons-material/QueryStats";
import HistoryIcon from "@mui/icons-material/History";
import LogoutIcon from "@mui/icons-material/Logout";
import Brightness4Icon from "@mui/icons-material/Brightness4";
import Brightness7Icon from "@mui/icons-material/Brightness7";
import { useThemeMode } from "@/lib/theme/ThemeProvider";
import { createClientSupabase } from "@/lib/supabase/client";

const DRAWER_EXPANDED = 260;
const DRAWER_COLLAPSED = 80;

type SimpleUser = {
  email?: string | null;
  name?: string | null;
  imageUrl?: string | null;
} | null;

function initials(name?: string | null, email?: string | null) {
  const base = name || email || "";
  const parts = base.trim().split(/\s+/);
  const a = parts[0]?.[0] || "";
  const b = parts[1]?.[0] || "";
  return (a + b || a || "U").toUpperCase();
}

export default function AppShell({ user, children }: { user: SimpleUser; children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const { mode, toggle } = useThemeMode();
  const supabase = React.useMemo(() => createClientSupabase(), []);
  const isDesktop = useMediaQuery((t: Theme) => t.breakpoints.up("md"));

  const [mobileOpen, setMobileOpen] = React.useState(false);
  const [collapsed, setCollapsed] = React.useState<boolean>(false);
  const [signingOut, setSigningOut] = React.useState(false);

  // Persist collapse
  React.useEffect(() => {
    const v = typeof window !== "undefined" ? localStorage.getItem("ftse-nav-collapsed") : null;
    setCollapsed(v === "1");
  }, []);
  React.useEffect(() => {
    if (typeof window !== "undefined") localStorage.setItem("ftse-nav-collapsed", collapsed ? "1" : "0");
  }, [collapsed]);

  const drawerWidth = collapsed ? DRAWER_COLLAPSED : DRAWER_EXPANDED;

  const nav = [
    { href: "/dashboard", label: "Dashboard", icon: <DashboardIcon /> },
    { href: "/backtest", label: "Backtest", icon: <QueryStatsIcon /> },
    { href: "/history", label: "History", icon: <HistoryIcon /> },
  ];

  const handleSignOut = async () => {
    try {
      setSigningOut(true);
      await supabase.auth.signOut();
      router.replace("/signin");
    } finally {
      setSigningOut(false);
    }
  };

  const DrawerContent = (
    <Stack height="100%">
      {/* User header */}
      <Box sx={{ p: 2, display: "flex", alignItems: "center", gap: 1.5 }}>
        <Avatar src={user?.imageUrl ?? undefined} sx={{ width: 44, height: 44 }}>
          {initials(user?.name, user?.email)}
        </Avatar>
        {!collapsed && (
          <Box sx={{ minWidth: 0 }}>
            <Typography variant="subtitle2" noWrap>{user?.name || "User"}</Typography>
            <Typography variant="caption" color="text.secondary" noWrap>
              {user?.email || ""}
            </Typography>
          </Box>
        )}
      </Box>

      <Divider />

      {/* Nav */}
      <List sx={{ px: 1, flex: 1 }}>
        {nav.map((item) => {
          const active = pathname.startsWith(item.href);
          return (
            <Link key={item.href} href={item.href} style={{ textDecoration: "none", color: "inherit" }}>
              <ListItemButton
                selected={active}
                sx={{
                  borderRadius: 12,
                  mb: 0.5,
                  px: collapsed ? 1 : 2,
                }}
                onClick={() => setMobileOpen(false)}
              >
                <ListItemIcon sx={{ minWidth: 40 }}>{item.icon}</ListItemIcon>
                {!collapsed && <ListItemText primary={item.label} />}
              </ListItemButton>
            </Link>
          );
        })}
      </List>

      <Divider />

      {/* Bottom actions */}
      <Stack direction="row" alignItems="center" justifyContent="space-between" sx={{ p: 1.25 }}>
        {/* Expand/collapse control always visible */}


        {/* Sign out button (icon-only when collapsed) */}
        <LoadingButton
          onClick={handleSignOut}
          variant={collapsed ? "text" : "outlined"}
          color="inherit"
          startIcon={<LogoutIcon />}
          loading={signingOut}
          disabled={signingOut}
          sx={{
            minWidth: collapsed ? 0 : 120,
            borderRadius: 2,
          }}
        >
          {!collapsed && "Sign out"}
        </LoadingButton>
      </Stack>
    </Stack>
  );

  return (
    <Box sx={{ display: "flex" }}>
      {/* Top AppBar */}
      <AppBar
        position="fixed"
        color="default"
        elevation={1}
        sx={{
          zIndex: (t) => t.zIndex.drawer + 1,
          bgcolor: (t) => t.palette.background.paper,
          borderBottom: "1px solid",
          borderColor: "divider",
        }}
      >
        <Toolbar sx={{ gap: 1 }}>
          {/* Desktop: toggle collapse; Mobile: open drawer */}
          <Tooltip title={isDesktop ? (collapsed ? "Expand sidebar" : "Collapse sidebar") : "Open menu"}>
            <IconButton
              edge="start"
              onClick={() => (isDesktop ? setCollapsed((c) => !c) : setMobileOpen(true))}
              aria-label="Toggle navigation"
            >
              {isDesktop ? (collapsed ? <ChevronRightIcon /> : <ChevronLeftIcon />) : <MenuIcon />}
            </IconButton>
          </Tooltip>

          {/* Brand */}
          <Typography variant="h6" fontWeight={800} sx={{ mr: 2 }}>
            ftse100 Forecast
          </Typography>

          {/* Spacer */}
          <Box sx={{ flex: 1 }} />

          {/* Theme toggle */}
          <Tooltip title={`Switch to ${mode === "light" ? "dark" : "light"} mode`}>
            <IconButton onClick={toggle} aria-label="Toggle theme">
              {mode === "light" ? <Brightness4Icon /> : <Brightness7Icon />}
            </IconButton>
          </Tooltip>

          {/* Avatar */}
          <Tooltip title={user?.email || ""}>
            <Avatar src={user?.imageUrl ?? undefined} sx={{ width: 34, height: 34, ml: 1 }}>
              {initials(user?.name, user?.email)}
            </Avatar>
          </Tooltip>
        </Toolbar>
      </AppBar>

      {/* Left Drawer */}
      {isDesktop ? (
        <Drawer
          anchor="left"
          variant="permanent"
          open
          PaperProps={{
            sx: {
              width: drawerWidth,
              overflowX: "hidden",
              transition: (t) => t.transitions.create("width", { duration: t.transitions.duration.shorter }),
              boxSizing: "border-box",
              borderRight: "1px solid",
              borderColor: "divider",
            },
          }}
        >
          {DrawerContent}
        </Drawer>
      ) : (
        <Drawer
          anchor="left"
          variant="temporary"
          open={mobileOpen}
          onClose={() => setMobileOpen(false)}
          ModalProps={{ keepMounted: true }}
          PaperProps={{
            sx: {
              width: DRAWER_EXPANDED,
              boxSizing: "border-box",
              borderRight: "1px solid",
              borderColor: "divider",
            },
          }}
        >
          {DrawerContent}
        </Drawer>
      )}

      {/* Content */}
     {/* Content */}
<Box
  component="main"
  sx={{
    flexGrow: 1,
    p: { xs: 2, md: 3 },
    mt: 8, // offset AppBar
    minHeight: "calc(100vh - 64px)",
    bgcolor: "background.default", // light = white, dark = dark
  }}
>
  <Paper
    elevation={0}
    sx={{
      p: { xs: 2, md: 3 },
      borderRadius: 3,
      bgcolor: "background.paper", // keeps it white in light, dark in dark
    }}
  >
    {children}
  </Paper>
</Box>

    </Box>
  );
}

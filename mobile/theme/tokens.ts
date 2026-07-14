/**
 * Harbor LifeLine — Design Language: "Tactical Dark Mode"
 * Per blueprint section 5: Background #0B0F14, Primary Amber #FFB020,
 * Mono font (JetBrains Mono via expo-font).
 */

export const colors = {
  background: "#0B0F14",
  surface: "#12181F",
  surfaceRaised: "#1A222B",
  border: "#232C36",

  amber: "#FFB020",
  amberDim: "#8A5F16",

  textPrimary: "#F5F7FA",
  textSecondary: "#9AA5B1",
  textMuted: "#5C6670",

  // Chat bubbles per blueprint section 5
  bubbleAI: "#FFB020", // Amber bubbles (AI)
  bubbleAIText: "#0B0F14",
  bubbleUser: "#2A323C", // Gray bubbles (User)
  bubbleUserText: "#F5F7FA",

  danger: "#E5484D",
  success: "#3DD68C",
  warning: "#FFB020",

  connectionOnline: "#3DD68C",
  connectionOffline: "#E5484D",
  connectionSearching: "#FFB020",
} as const;

export const fonts = {
  mono: "JetBrainsMono-Regular",
  monoBold: "JetBrainsMono-Bold",
  monoMedium: "JetBrainsMono-Medium",
} as const;

export const spacing = {
  xs: 4,
  sm: 8,
  md: 16,
  lg: 24,
  xl: 32,
  xxl: 48,
} as const;

export const radii = {
  sm: 6,
  md: 12,
  lg: 20,
  pill: 999,
} as const;

export type ConnectionState = "ble" | "lan" | "offline" | "searching";

export const connectionLabel: Record<ConnectionState, string> = {
  ble: "BLE",
  lan: "LAN",
  offline: "OFFLINE",
  searching: "SCANNING",
};

export const connectionColor: Record<ConnectionState, string> = {
  ble: colors.connectionOnline,
  lan: colors.connectionOnline,
  offline: colors.connectionOffline,
  searching: colors.connectionSearching,
};

import React, { useEffect } from "react";
import { Stack } from "expo-router";
import * as Font from "expo-font";
import { colors } from "../theme/tokens";
import { initLocalLog } from "../lib/localLog";

export default function RootLayout() {
  const [fontsLoaded] = Font.useFonts({
    "JetBrainsMono-Regular": require("../assets/fonts/JetBrainsMono-Regular.ttf"),
    "JetBrainsMono-Medium": require("../assets/fonts/JetBrainsMono-Medium.ttf"),
    "JetBrainsMono-Bold": require("../assets/fonts/JetBrainsMono-Bold.ttf"),
  });

  useEffect(() => {
    initLocalLog().catch((err) =>
      console.warn("[harbor] local log init failed (non-fatal):", err)
    );
  }, []);

  if (!fontsLoaded) return null;

  return (
    <Stack
      screenOptions={{
        headerShown: false,
        contentStyle: { backgroundColor: colors.background },
        animation: "fade",
      }}
    >
      <Stack.Screen name="index" />
      <Stack.Screen name="chat" />
      <Stack.Screen name="peers" />
    </Stack>
  );
}

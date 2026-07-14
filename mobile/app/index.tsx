/**
 * Harbor LifeLine — index.tsx (SOS Home)
 * Per blueprint section 5: "Giant 'TAP TO ASK HARBOR' button. Connection
 * pills indicating BLE/LAN/Offline."
 */

import React, { useEffect } from "react";
import { View, Text, Pressable, StyleSheet, SafeAreaView } from "react-native";
import { router } from "expo-router";
import { colors, fonts, spacing, radii, connectionLabel, connectionColor } from "../theme/tokens";
import { useHarborStore } from "../store/useHarborStore";

export default function SosHome() {
  const connection = useHarborStore((s) => s.connection);
  const nearbyHubs = useHarborStore((s) => s.nearbyHubs);
  const activeHubId = useHarborStore((s) => s.activeHubId);

  const isConnected = connection === "ble" || connection === "lan";

  const handleAskHarbor = () => {
    if (isConnected) {
      router.push("/chat");
    } else {
      router.push("/peers");
    }
  };

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.wordmark}>HARBOR LIFELINE</Text>
        <Text style={styles.tagline}>When the grid dies, the Harbor stays lit.</Text>
      </View>

      <View style={styles.pillRow}>
        <ConnectionPill state={connection} />
        {activeHubId ? (
          <View style={styles.hubPill}>
            <Text style={styles.hubPillText}>
              {nearbyHubs.find((h) => h.id === activeHubId)?.name ?? activeHubId}
            </Text>
          </View>
        ) : null}
      </View>

      <View style={styles.center}>
        <Pressable
          onPress={handleAskHarbor}
          style={({ pressed }) => [
            styles.sosButton,
            pressed && styles.sosButtonPressed,
          ]}
        >
          <Text style={styles.sosButtonText}>TAP TO{"\n"}ASK HARBOR</Text>
        </Pressable>
        <Text style={styles.hint}>
          {isConnected
            ? "Connected — tap to describe your emergency"
            : "Not connected — tap to find a nearby Hub"}
        </Text>
      </View>

      <Pressable style={styles.peersLink} onPress={() => router.push("/peers")}>
        <Text style={styles.peersLinkText}>
          {nearbyHubs.length > 0
            ? `${nearbyHubs.length} Hub${nearbyHubs.length === 1 ? "" : "s"} nearby →`
            : "Scan for nearby Hubs →"}
        </Text>
      </Pressable>
    </SafeAreaView>
  );
}

function ConnectionPill({ state }: { state: ReturnType<typeof useHarborStore.getState>["connection"] }) {
  return (
    <View style={[styles.connectionPill, { borderColor: connectionColor[state] }]}>
      <View style={[styles.dot, { backgroundColor: connectionColor[state] }]} />
      <Text style={[styles.connectionPillText, { color: connectionColor[state] }]}>
        {connectionLabel[state]}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
    paddingHorizontal: spacing.lg,
  },
  header: {
    marginTop: spacing.lg,
    alignItems: "center",
  },
  wordmark: {
    color: colors.amber,
    fontFamily: fonts.monoBold,
    fontSize: 22,
    letterSpacing: 2,
  },
  tagline: {
    color: colors.textSecondary,
    fontFamily: fonts.mono,
    fontSize: 12,
    marginTop: spacing.xs,
    textAlign: "center",
  },
  pillRow: {
    flexDirection: "row",
    justifyContent: "center",
    gap: spacing.sm,
    marginTop: spacing.lg,
  },
  connectionPill: {
    flexDirection: "row",
    alignItems: "center",
    borderWidth: 1,
    borderRadius: radii.pill,
    paddingVertical: spacing.xs,
    paddingHorizontal: spacing.md,
  },
  dot: {
    width: 6,
    height: 6,
    borderRadius: 3,
    marginRight: spacing.xs,
  },
  connectionPillText: {
    fontFamily: fonts.monoMedium,
    fontSize: 11,
    letterSpacing: 1,
  },
  hubPill: {
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radii.pill,
    paddingVertical: spacing.xs,
    paddingHorizontal: spacing.md,
  },
  hubPillText: {
    color: colors.textSecondary,
    fontFamily: fonts.mono,
    fontSize: 11,
  },
  center: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
  },
  sosButton: {
    width: 220,
    height: 220,
    borderRadius: 110,
    backgroundColor: colors.amber,
    alignItems: "center",
    justifyContent: "center",
    shadowColor: colors.amber,
    shadowOpacity: 0.4,
    shadowRadius: 24,
    shadowOffset: { width: 0, height: 0 },
    elevation: 8,
  },
  sosButtonPressed: {
    backgroundColor: colors.amberDim,
    transform: [{ scale: 0.98 }],
  },
  sosButtonText: {
    color: colors.background,
    fontFamily: fonts.monoBold,
    fontSize: 22,
    textAlign: "center",
    lineHeight: 28,
  },
  hint: {
    color: colors.textMuted,
    fontFamily: fonts.mono,
    fontSize: 12,
    marginTop: spacing.lg,
    textAlign: "center",
  },
  peersLink: {
    alignItems: "center",
    paddingVertical: spacing.lg,
  },
  peersLinkText: {
    color: colors.amber,
    fontFamily: fonts.monoMedium,
    fontSize: 13,
  },
});

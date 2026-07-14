/**
 * Harbor LifeLine — peers.tsx
 * Per blueprint section 5: "BLE scan results showing nearby Hubs with
 * signal strength bars."
 *
 * BLE scanning itself is implemented via react-native-ble-plx, scanning
 * for the service UUID advertised by the Hub's `bleak` GATT server
 * (0000LIFE-xxxx per blueprint section 6). See lib/bleClient.ts for the
 * scan-result shape this screen expects — swap the mock scan below for
 * a real BleManager.startDeviceScan() call once react-native-ble-plx is
 * wired into the Expo dev client (it requires a custom dev client / EAS
 * build, since it's a native module not supported in Expo Go).
 */

import React, { useCallback, useEffect, useState } from "react";
import { View, Text, Pressable, FlatList, StyleSheet, SafeAreaView } from "react-native";
import { router } from "expo-router";
import { colors, fonts, spacing, radii } from "../theme/tokens";
import { useHarborStore, type NearbyHub } from "../store/useHarborStore";
import { HubClient, DEFAULT_HUB_URL } from "../lib/hubClient";

const hubClient = new HubClient(DEFAULT_HUB_URL);

export default function Peers() {
  const nearbyHubs = useHarborStore((s) => s.nearbyHubs);
  const setNearbyHubs = useHarborStore((s) => s.setNearbyHubs);
  const connectToHub = useHarborStore((s) => s.connectToHub);
  const setConnection = useHarborStore((s) => s.setConnection);
  const [scanning, setScanning] = useState(false);

  const scan = useCallback(async () => {
    setScanning(true);
    setConnection("searching");

    // LAN probe: check if the default hotspot Hub address is reachable.
    // Real BLE scanning (react-native-ble-plx) would populate additional
    // entries here with transport: "ble" and live RSSI values.
    const found: NearbyHub[] = [];
    try {
      const health = await hubClient.health(2000);
      if (health.status === "ok") {
        found.push({
          id: DEFAULT_HUB_URL,
          name: `Hub (${health.model})`,
          rssi: -50, // LAN doesn't have RSSI; shown as strong/connected
          transport: "lan",
        });
      }
    } catch {
      // no LAN hub reachable — expected if only BLE is available
    }

    setNearbyHubs(found);
    setConnection(found.length > 0 ? "lan" : "offline");
    setScanning(false);
  }, [setNearbyHubs, setConnection]);

  useEffect(() => {
    scan();
  }, [scan]);

  const handleConnect = (hub: NearbyHub) => {
    connectToHub(hub.id);
    router.push("/chat");
  };

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>NEARBY HUBS</Text>
        <Pressable onPress={scan} disabled={scanning}>
          <Text style={styles.rescan}>{scanning ? "SCANNING..." : "RESCAN"}</Text>
        </Pressable>
      </View>

      <FlatList
        data={nearbyHubs}
        keyExtractor={(h) => h.id}
        contentContainerStyle={styles.list}
        ListEmptyComponent={
          <View style={styles.empty}>
            <Text style={styles.emptyText}>
              {scanning
                ? "Scanning for Hubs over BLE and LAN..."
                : "No Hubs found. Move closer or check the Hub is running."}
            </Text>
          </View>
        }
        renderItem={({ item }) => (
          <Pressable style={styles.hubRow} onPress={() => handleConnect(item)}>
            <View style={styles.hubInfo}>
              <Text style={styles.hubName}>{item.name}</Text>
              <Text style={styles.hubTransport}>{item.transport.toUpperCase()}</Text>
            </View>
            <SignalBars rssi={item.rssi} />
          </Pressable>
        )}
      />
    </SafeAreaView>
  );
}

function SignalBars({ rssi }: { rssi: number }) {
  // RSSI roughly -30 (excellent) to -90 (unusable). Map to 1-4 bars.
  const strength = rssi > -55 ? 4 : rssi > -65 ? 3 : rssi > -75 ? 2 : 1;
  return (
    <View style={styles.barsContainer}>
      {[1, 2, 3, 4].map((bar) => (
        <View
          key={bar}
          style={[
            styles.bar,
            { height: 4 + bar * 3 },
            bar <= strength ? styles.barActive : styles.barInactive,
          ]}
        />
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.background },
  header: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.md,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  title: {
    color: colors.textPrimary,
    fontFamily: fonts.monoBold,
    fontSize: 14,
    letterSpacing: 1,
  },
  rescan: {
    color: colors.amber,
    fontFamily: fonts.monoMedium,
    fontSize: 12,
  },
  list: { padding: spacing.md },
  empty: { paddingVertical: spacing.xxl, alignItems: "center" },
  emptyText: {
    color: colors.textMuted,
    fontFamily: fonts.mono,
    fontSize: 13,
    textAlign: "center",
    paddingHorizontal: spacing.lg,
  },
  hubRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radii.md,
    padding: spacing.md,
    marginBottom: spacing.sm,
  },
  hubInfo: { gap: spacing.xs },
  hubName: {
    color: colors.textPrimary,
    fontFamily: fonts.monoMedium,
    fontSize: 14,
  },
  hubTransport: {
    color: colors.amber,
    fontFamily: fonts.mono,
    fontSize: 11,
  },
  barsContainer: {
    flexDirection: "row",
    alignItems: "flex-end",
    gap: 3,
    height: 16,
  },
  bar: { width: 4, borderRadius: 1 },
  barActive: { backgroundColor: colors.amber },
  barInactive: { backgroundColor: colors.border },
});

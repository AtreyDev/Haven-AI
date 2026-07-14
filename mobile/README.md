# Harbor LifeLine — Mobile (Expo React Native)

The "Distress Node" client. Per blueprint section 5.

## Screens

- **`app/index.tsx`** — SOS Home. Giant "TAP TO ASK HARBOR" button, connection pills (BLE/LAN/Offline).
- **`app/chat.tsx`** — Distress interface. Amber bubbles (AI), gray bubbles (user), Hub latency shown per response, `expo-speech` TTS reads answers aloud.
- **`app/peers.tsx`** — Nearby Hub scan results with signal-strength bars.

## Stack

- **State:** Zustand (`store/useHarborStore.ts`)
- **Persistence:** `expo-sqlite` mirrors every message locally (`lib/localLog.ts`) so instructions survive leaving Hub range
- **Design:** Tactical dark mode — `#0B0F14` background, `#FFB020` amber, JetBrains Mono (`theme/tokens.ts`)
- **LAN transport:** `lib/hubClient.ts` talks to `hub_server.py`'s `/api/chat`
- **BLE transport:** `react-native-ble-plx`, scanning for the Hub's advertised service UUID (`0000LIFE-xxxx`)

## Setup

```bash
npm install
```

You'll need to add JetBrains Mono font files (not included here — pull
from [the official releases](https://github.com/JetBrains/JetBrainsMono))
into `assets/fonts/`:

```
assets/fonts/JetBrainsMono-Regular.ttf
assets/fonts/JetBrainsMono-Medium.ttf
assets/fonts/JetBrainsMono-Bold.ttf
```

## Running

```bash
npx expo start
```

**Note on BLE:** `react-native-ble-plx` is a native module and will not
work in Expo Go. Use a custom dev client or EAS build:

```bash
npx expo install expo-dev-client
eas build --profile development --platform ios
```

Until then, `peers.tsx` will still work over the LAN transport (hotspot
fallback) — it probes `DEFAULT_HUB_URL` in `lib/hubClient.ts`. Update that
constant to match your Hub's actual hotspot gateway IP, or wire up
mDNS/QR-code discovery for a real deploy.

## Known scope for the 8-hour build

This scaffold implements the full LAN path end-to-end (index → peers scan
→ connect → chat → Hub → SQLite mirror → TTS). The BLE GATT path
(`react-native-ble-plx` wiring in `peers.tsx`'s `scan()`) is stubbed with
a comment showing exactly where to swap in `BleManager.startDeviceScan()`
— this is the piece that needs a real BLE-capable dev client to test, per
the blueprint's own timeline (hours 5:00–6:15).

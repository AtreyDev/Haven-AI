/**
 * Harbor LifeLine — Hub API Client (LAN / Wi-Fi Direct transport)
 * Talks to hub_server.py's FastAPI endpoint. This is the "Priority 3
 * transport" fallback per blueprint section 4.3 — used when the phone
 * joins the Hub's hotspot instead of connecting over BLE.
 *
 * BLE GATT (Priority 2, required for iOS since RFCOMM is blocked by
 * Apple) is handled separately via react-native-ble-plx; see
 * lib/bleClient.ts stub below for the interface it should implement.
 */

export type ChatApiResponse = {
  response: string;
  source: "kb" | "llm";
  matched_keyword: string | null;
  latency_ms: number;
};

export type HealthResponse = {
  status: string;
  ollama_reachable: boolean;
  model: string;
};

export class HubClient {
  constructor(private baseUrl: string) {}

  async health(timeoutMs = 3000): Promise<HealthResponse> {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);
    try {
      const res = await fetch(`${this.baseUrl}/api/health`, {
        signal: controller.signal,
      });
      if (!res.ok) throw new Error(`Health check failed: ${res.status}`);
      return res.json();
    } finally {
      clearTimeout(timer);
    }
  }

  async ask(
    message: string,
    peerId: string,
    alias?: string,
    timeoutMs = 35000
  ): Promise<ChatApiResponse> {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);
    try {
      const res = await fetch(`${this.baseUrl}/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message, peer_id: peerId, alias }),
        signal: controller.signal,
      });
      if (!res.ok) throw new Error(`Chat request failed: ${res.status}`);
      return res.json();
    } finally {
      clearTimeout(timer);
    }
  }
}

/**
 * Default hub address when the phone has joined the Hub's hotspot.
 * In a real deploy this should be discovered (e.g. via mDNS/Bonjour or
 * a QR code the Hub prints on startup) rather than hardcoded — hotspot
 * gateway IPs vary by device.
 */
export const DEFAULT_HUB_URL = "http://192.168.43.1:8001";

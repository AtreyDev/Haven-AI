/**
 * Harbor LifeLine — Global State (Zustand)
 * Per blueprint section 5: "State Management: Zustand for global state."
 */

import { create } from "zustand";
import type { ConnectionState } from "../theme/tokens";

export type ChatMessage = {
  id: string;
  role: "user" | "ai";
  text: string;
  timestamp: number;
  source?: "kb" | "llm";
  latencyMs?: number;
};

export type NearbyHub = {
  id: string; // BLE peripheral id or IP:port
  name: string;
  rssi: number; // signal strength, for the peers.tsx bar display
  transport: "ble" | "lan";
};

type HarborState = {
  connection: ConnectionState;
  activeHubId: string | null;
  nearbyHubs: NearbyHub[];
  messages: ChatMessage[];
  isSending: boolean;

  setConnection: (state: ConnectionState) => void;
  setNearbyHubs: (hubs: NearbyHub[]) => void;
  connectToHub: (hubId: string) => void;
  disconnectHub: () => void;
  addMessage: (message: ChatMessage) => void;
  setSending: (sending: boolean) => void;
  clearMessages: () => void;
};

export const useHarborStore = create<HarborState>((set) => ({
  connection: "offline",
  activeHubId: null,
  nearbyHubs: [],
  messages: [],
  isSending: false,

  setConnection: (state) => set({ connection: state }),

  setNearbyHubs: (hubs) => set({ nearbyHubs: hubs }),

  connectToHub: (hubId) =>
    set((s) => ({
      activeHubId: hubId,
      connection: s.nearbyHubs.find((h) => h.id === hubId)?.transport ?? "lan",
    })),

  disconnectHub: () => set({ activeHubId: null, connection: "offline" }),

  addMessage: (message) =>
    set((s) => ({ messages: [...s.messages, message] })),

  setSending: (sending) => set({ isSending: sending }),

  clearMessages: () => set({ messages: [] }),
}));

/**
 * Harbor LifeLine — Local Log Mirror (expo-sqlite)
 * Per blueprint section 5: "Persistence: expo-sqlite mirrors logs onto
 * the phone so the user retains AI instructions even if they leave Hub
 * range."
 */

import * as SQLite from "expo-sqlite";
import type { ChatMessage } from "../store/useHarborStore";

const DB_NAME = "harbor_local.db";

let dbPromise: Promise<SQLite.SQLiteDatabase> | null = null;

function getDb() {
  if (!dbPromise) {
    dbPromise = SQLite.openDatabaseAsync(DB_NAME);
  }
  return dbPromise;
}

export async function initLocalLog() {
  const db = await getDb();
  await db.execAsync(`
    PRAGMA journal_mode = WAL;
    CREATE TABLE IF NOT EXISTS mirrored_messages (
      id TEXT PRIMARY KEY,
      role TEXT NOT NULL,
      text TEXT NOT NULL,
      source TEXT,
      latency_ms INTEGER,
      timestamp INTEGER NOT NULL
    );
  `);
}

export async function mirrorMessage(message: ChatMessage) {
  const db = await getDb();
  await db.runAsync(
    `INSERT OR REPLACE INTO mirrored_messages
       (id, role, text, source, latency_ms, timestamp)
     VALUES (?, ?, ?, ?, ?, ?)`,
    message.id,
    message.role,
    message.text,
    message.source ?? null,
    message.latencyMs ?? null,
    message.timestamp
  );
}

export async function loadMirroredMessages(): Promise<ChatMessage[]> {
  const db = await getDb();
  const rows = await db.getAllAsync<{
    id: string;
    role: "user" | "ai";
    text: string;
    source: "kb" | "llm" | null;
    latency_ms: number | null;
    timestamp: number;
  }>(`SELECT * FROM mirrored_messages ORDER BY timestamp ASC`);

  return rows.map((r) => ({
    id: r.id,
    role: r.role,
    text: r.text,
    timestamp: r.timestamp,
    source: r.source ?? undefined,
    latencyMs: r.latency_ms ?? undefined,
  }));
}

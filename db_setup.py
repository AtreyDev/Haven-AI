"""
Harbor LifeLine - Database Setup
Creates survival_mesh.db in WAL mode and seeds the survival_kb table
with 20 canonical distress scenarios so common crises get instant
answers without waiting on LLM inference.

Run: python3 db_setup.py
"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "survival_mesh.db")

SCHEMA = """
PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS distress_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    peer_mac TEXT,              -- BT MAC or IP:port
    transport TEXT,             -- 'rfcomm' | 'ble' | 'lan'
    user_message TEXT NOT NULL,
    ai_response TEXT,
    latency_ms INTEGER,
    tokens_out INTEGER,
    source TEXT DEFAULT 'llm',  -- 'llm' | 'kb' (which path answered)
    timestamp DATETIME DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS peers (
    mac TEXT PRIMARY KEY,
    alias TEXT,
    first_seen DATETIME DEFAULT (datetime('now')),
    last_seen DATETIME
);

CREATE TABLE IF NOT EXISTS survival_kb (
    id INTEGER PRIMARY KEY,
    keyword TEXT UNIQUE,        -- e.g., 'snakebite', 'hypothermia'
    answer TEXT
);

CREATE INDEX IF NOT EXISTS idx_logs_time ON distress_logs(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_logs_peer ON distress_logs(peer_mac);
"""

# 20 canonical distress scenarios. Keyword = simple lowercase token(s)
# matched via substring search against incoming user_message before
# falling back to the LLM (see hub_server.py: kb_lookup()).
# Answers follow the same locked format as the LLM system prompt:
# short, imperative, bulleted-in-text, prioritized.
SEED_KB = [
    ("snakebite",
     "- Keep victim still, bite BELOW heart level.\n"
     "- Remove rings/tight clothing near bite.\n"
     "- Do NOT cut, suck, or apply tourniquet.\n"
     "- Mark swelling edge + time, monitor.\n"
     "- Seek antivenom urgently if available."),

    ("hypothermia",
     "- Move to dry shelter, remove wet clothing.\n"
     "- Insulate from ground first (biggest heat loss).\n"
     "- Warm core (chest/neck/groin) before limbs.\n"
     "- Give warm sweet liquids if conscious.\n"
     "- No alcohol. No rubbing limbs. Handle gently."),

    ("cardiac arrest",
     "- Call for help / send SOS immediately.\n"
     "- Start CPR: 30 chest compressions, 2 breaths.\n"
     "- Push hard/fast, ~2 inches deep, 100-120/min.\n"
     "- Use AED if available, follow voice prompts.\n"
     "- Continue until help arrives or person revives."),

    ("arterial bleed",
     "- Apply firm direct pressure with cloth NOW.\n"
     "- Elevate wound above heart if possible.\n"
     "- If pressure fails, apply tourniquet 2-3in above wound.\n"
     "- Note tourniquet time, do not loosen.\n"
     "- Treat for shock: lay flat, keep warm."),

    ("choking",
     "- Ask 'Are you choking?' If silent, act fast.\n"
     "- 5 back blows between shoulder blades.\n"
     "- 5 abdominal thrusts (Heimlich), repeat cycle.\n"
     "- If unconscious, start CPR, check mouth before breaths.\n"
     "- Infants: back blows + chest thrusts, no abdomen."),

    ("burns",
     "- Cool burn under running water 10-20 min.\n"
     "- Remove tight items before swelling starts.\n"
     "- Do NOT apply ice, butter, or ointments.\n"
     "- Cover loosely with clean, non-stick cloth.\n"
     "- Seek care if burn is large, deep, or on face/joints."),

    ("fracture",
     "- Do not move injured limb unnecessarily.\n"
     "- Immobilize joint above and below fracture.\n"
     "- Splint with rigid material + padding, secure snug.\n"
     "- Check circulation (color/warmth) after splinting.\n"
     "- Elevate if possible, treat pain, seek help."),

    ("dehydration",
     "- Move to shade/cool area immediately.\n"
     "- Sip water slowly, add salt/sugar if available (ORS).\n"
     "- Avoid gulping large amounts at once.\n"
     "- Rest, loosen clothing, monitor urine color.\n"
     "- Severe confusion/no urine = seek help urgently."),

    ("heatstroke",
     "- Move to shade/cool area NOW, this is an emergency.\n"
     "- Remove excess clothing, fan the person.\n"
     "- Cool with wet cloths on neck, armpits, groin.\n"
     "- Do not give fluids if not fully conscious.\n"
     "- Monitor closely, seek help immediately."),

    ("seizure",
     "- Clear area of hard/sharp objects around person.\n"
     "- Cushion head, do NOT restrain movements.\n"
     "- Do NOT put anything in their mouth.\n"
     "- Time the seizure, turn on side after it stops.\n"
     "- Seek help if seizure exceeds 5 minutes or repeats."),

    ("drowning",
     "- Remove from water without becoming victim yourself.\n"
     "- Check breathing; start CPR if not breathing.\n"
     "- Expect vomiting, turn head to side if breathing.\n"
     "- Treat for hypothermia, keep warm and dry.\n"
     "- Seek medical care even if person seems recovered."),

    ("no water source",
     "- Collect dew/rain with cloth or container.\n"
     "- Dig near green vegetation or dry riverbeds.\n"
     "- Solar still: plastic sheet over pit + container.\n"
     "- Never drink urine or seawater.\n"
     "- Ration sweat, not water; rest in shade."),

    ("no shelter storm",
     "- Find natural windbreak: rocks, dense trees, ditch.\n"
     "- Build lean-to with branches, insulate with leaves.\n"
     "- Avoid lone tall trees, ridgelines, flood paths.\n"
     "- Signal location before storm worsens visibility.\n"
     "- Stay dry, insulate from ground, conserve heat."),

    ("lost no signal",
     "- Stop moving, assess: Stop-Think-Observe-Plan.\n"
     "- Stay put if others may search for you.\n"
     "- Signal: mirror flash, whistle 3x, bright cloth.\n"
     "- Conserve phone/device battery, airplane mode.\n"
     "- Mark trail if you must move, follow water downhill."),

    ("smoke inhalation",
     "- Get to fresh air immediately, stay low if indoors.\n"
     "- Cover nose/mouth with damp cloth if smoke present.\n"
     "- Do not re-enter smoke-filled area.\n"
     "- Watch for coughing, confusion, breathing difficulty.\n"
     "- Seek oxygen/medical care as soon as possible."),

    ("insect sting allergic",
     "- Remove stinger by scraping, not pinching.\n"
     "- Watch for swelling of face/throat/breathing trouble.\n"
     "- Use epinephrine auto-injector (EpiPen) if available.\n"
     "- Keep person lying flat, legs elevated.\n"
     "- This can be life-threatening: seek help urgently."),

    ("food poisoning",
     "- Rest, sip clear fluids/ORS frequently.\n"
     "- Avoid solid food until vomiting subsides.\n"
     "- Do NOT take anti-diarrheal if fever/blood present.\n"
     "- Watch for severe dehydration signs.\n"
     "- Seek help if symptoms worsen or persist >48hrs."),

    ("earthquake trapped",
     "- Stay calm, tap on pipe/wall to signal location.\n"
     "- Cover mouth with cloth, avoid excess dust inhalation.\n"
     "- Do not shout unless necessary (conserve air/energy).\n"
     "- Stay still to avoid further debris collapse.\n"
     "- Conserve device battery for periodic signaling only."),

    ("flood rising water",
     "- Move to highest available ground immediately.\n"
     "- Avoid walking/driving through moving water.\n"
     "- 6 inches of moving water can knock you down.\n"
     "- Stay off electrical equipment if wet.\n"
     "- Signal for rescue from a visible high point."),

    ("panic attack",
     "- Sit down, feet flat on ground, steady support.\n"
     "- Breathe in 4 counts, hold 4, out 6, repeat.\n"
     "- Name 5 things you see, 4 you hear, 3 you feel.\n"
     "- This will pass, you are not in physical danger.\n"
     "- Seek a trusted person or calm space if possible."),
]


def main():
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(SCHEMA)

    cur = conn.cursor()
    cur.executemany(
        "INSERT OR IGNORE INTO survival_kb (keyword, answer) VALUES (?, ?)",
        SEED_KB,
    )
    conn.commit()

    kb_count = cur.execute("SELECT COUNT(*) FROM survival_kb").fetchone()[0]
    mode = cur.execute("PRAGMA journal_mode;").fetchone()[0]
    conn.close()

    print(f"[db_setup] DB ready at: {DB_PATH}")
    print(f"[db_setup] journal_mode = {mode}")
    print(f"[db_setup] survival_kb rows = {kb_count}")


if __name__ == "__main__":
    main()

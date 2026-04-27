# sync_supabase.py - Cloud Supabase mirror to local Postgres
# Plug-and-play: reads SUPABASE_URL, SUPABASE_KEY from env (set in .env)
# Author: Erki Unn + Eirik (Cowork agent)
# Sleep-loop, runs every SYNC_INTERVAL seconds (default 900 = 15 min)

import os
import time
import json
import requests
import psycopg2

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
LOCAL_DB = {
    "host": "postgres",
    "port": 5432,
    "user": os.environ.get("LOCAL_DB_USER", "forestsense"),
    "password": os.environ.get("LOCAL_DB_PASSWORD", "forestsense_dev_2026"),
    "database": os.environ.get("LOCAL_DB_NAME", "forestsense")
}
SYNC_INTERVAL = int(os.environ.get("SYNC_INTERVAL", "900"))

if not SUPABASE_URL or not SUPABASE_KEY:
    print("[supabase-sync] FATAL: SUPABASE_URL and SUPABASE_KEY required in .env", flush=True)
    exit(1)

def wait_for_postgres(max_wait=120):
    """Retry connection until Postgres ready (race condition fix after reboot)"""
    start = time.time()
    attempt = 0
    while time.time() - start < max_wait:
        attempt += 1
        try:
            conn = psycopg2.connect(connect_timeout=3, **LOCAL_DB)
            conn.close()
            print("[supabase-sync] Postgres ready after " + str(attempt) + " attempts", flush=True)
            return True
        except Exception as e:
            print("[supabase-sync] Waiting for Postgres (" + str(attempt) + "): " + str(e)[:80], flush=True)
            time.sleep(3)
    return False

def ensure_schema():
    """Create cloud_agent_messages and supabase_sync_log tables if missing"""
    conn = psycopg2.connect(**LOCAL_DB)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS cloud_agent_messages (
            cloud_id INT PRIMARY KEY,
            from_agent TEXT NOT NULL,
            to_agent TEXT,
            message_type TEXT NOT NULL,
            priority INT,
            payload JSONB,
            status TEXT,
            correlation_id TEXT,
            created_at TIMESTAMPTZ,
            client_id TEXT,
            expires_at TIMESTAMPTZ,
            synced_at TIMESTAMPTZ DEFAULT NOW()
        );
        CREATE INDEX IF NOT EXISTS idx_cloud_agent_to_status ON cloud_agent_messages(to_agent, status);
        CREATE INDEX IF NOT EXISTS idx_cloud_agent_created ON cloud_agent_messages(created_at DESC);
        CREATE TABLE IF NOT EXISTS supabase_sync_log (
            id SERIAL PRIMARY KEY,
            sync_started TIMESTAMPTZ DEFAULT NOW(),
            sync_completed TIMESTAMPTZ,
            new_messages INT,
            last_cloud_id INT,
            error TEXT
        );
    """)
    conn.commit()
    cur.close()
    conn.close()

def fetch_supabase_messages(since_id=0, limit=1000):
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": "Bearer " + SUPABASE_KEY,
        "Content-Type": "application/json"
    }
    url = SUPABASE_URL + "/rest/v1/agent_messages"
    params = {
        "select": "*",
        "id": "gt." + str(since_id),
        "order": "id.asc",
        "limit": str(limit)
    }
    r = requests.get(url, headers=headers, params=params, timeout=30)
    r.raise_for_status()
    return r.json()

def sync_to_local():
    conn = psycopg2.connect(**LOCAL_DB)
    cur = conn.cursor()
    cur.execute("INSERT INTO supabase_sync_log (sync_started) VALUES (NOW()) RETURNING id")
    log_id = cur.fetchone()[0]
    conn.commit()
    try:
        cur.execute("SELECT COALESCE(MAX(cloud_id), 0) FROM cloud_agent_messages")
        last_id = cur.fetchone()[0]
        messages = fetch_supabase_messages(since_id=last_id)
        for msg in messages:
            cur.execute("""
                INSERT INTO cloud_agent_messages
                    (cloud_id, from_agent, to_agent, message_type, priority, payload, status, correlation_id, created_at, client_id, expires_at)
                VALUES (%(id)s, %(from_agent)s, %(to_agent)s, %(message_type)s, %(priority)s, %(payload)s, %(status)s, %(correlation_id)s, %(created_at)s, %(client_id)s, %(expires_at)s)
                ON CONFLICT (cloud_id) DO UPDATE
                SET status = EXCLUDED.status, payload = EXCLUDED.payload, synced_at = NOW()
            """, {
                "id": msg["id"],
                "from_agent": msg["from_agent"],
                "to_agent": msg.get("to_agent"),
                "message_type": msg["message_type"],
                "priority": msg.get("priority", 5),
                "payload": json.dumps(msg["payload"]),
                "status": msg.get("status", "pending"),
                "correlation_id": msg.get("correlation_id"),
                "created_at": msg.get("created_at"),
                "client_id": msg.get("client_id", "vestman"),
                "expires_at": msg.get("expires_at")
            })
        new_count = len(messages)
        new_max_id = messages[-1]["id"] if messages else last_id
        cur.execute("UPDATE supabase_sync_log SET sync_completed = NOW(), new_messages = %s, last_cloud_id = %s WHERE id = %s", (new_count, new_max_id, log_id))
        conn.commit()
        return new_count
    except Exception as e:
        cur.execute("UPDATE supabase_sync_log SET sync_completed = NOW(), error = %s WHERE id = %s", (str(e), log_id))
        conn.commit()
        raise
    finally:
        cur.close()
        conn.close()

def main():
    print("[supabase-sync] Started, interval " + str(SYNC_INTERVAL) + "s", flush=True)
    if not wait_for_postgres():
        print("[supabase-sync] FATAL: Postgres not ready after 120s", flush=True)
        return
    ensure_schema()
    while True:
        try:
            count = sync_to_local()
            print("[supabase-sync] Synced " + str(count) + " new messages", flush=True)
        except Exception as e:
            print("[supabase-sync] ERROR: " + str(e), flush=True)
        time.sleep(SYNC_INTERVAL)

if __name__ == "__main__":
    main()

# sync_memory_files.py - Index local Eirik folder content into Postgres
# Plug-and-play: full-text search via GIN index over .md/.txt/.py/etc files
# Author: Erki Unn + Eirik (Cowork agent)
# Sleep-loop, runs every SYNC_INTERVAL seconds (default 3600 = 1h)

import os
import time
import hashlib
import psycopg2

LOCAL_DB = {
    "host": "postgres",
    "port": 5432,
    "user": os.environ.get("LOCAL_DB_USER", "forestsense"),
    "password": os.environ.get("LOCAL_DB_PASSWORD", "forestsense_dev_2026"),
    "database": os.environ.get("LOCAL_DB_NAME", "forestsense")
}
EIRIK_ROOT = os.environ.get("EIRIK_ROOT", "/eirik")
SYNC_INTERVAL = int(os.environ.get("SYNC_INTERVAL", "3600"))
MAX_FILE_SIZE = int(os.environ.get("MAX_FILE_SIZE", "1048576"))
TEXT_EXTENSIONS = {".md", ".txt", ".py", ".ps1", ".yml", ".yaml", ".json", ".csv", ".html", ".sql", ".sh", ".conf", ".env", ".toml", ".ini", ".log"}

def wait_for_postgres(max_wait=120):
    start = time.time()
    attempt = 0
    while time.time() - start < max_wait:
        attempt += 1
        try:
            conn = psycopg2.connect(connect_timeout=3, **LOCAL_DB)
            conn.close()
            print("[memory-files-sync] Postgres ready after " + str(attempt) + " attempts", flush=True)
            return True
        except Exception as e:
            print("[memory-files-sync] Waiting for Postgres (" + str(attempt) + "): " + str(e)[:80], flush=True)
            time.sleep(3)
    return False

def ensure_schema():
    conn = psycopg2.connect(**LOCAL_DB)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS memory_files (
            id SERIAL PRIMARY KEY,
            path TEXT UNIQUE NOT NULL,
            folder_prefix TEXT NOT NULL,
            filename TEXT NOT NULL,
            extension TEXT,
            size_bytes BIGINT,
            sha256 TEXT,
            content TEXT,
            file_modified TIMESTAMPTZ,
            last_synced TIMESTAMPTZ DEFAULT NOW()
        );
        CREATE INDEX IF NOT EXISTS idx_memory_files_folder ON memory_files(folder_prefix);
        CREATE INDEX IF NOT EXISTS idx_memory_files_ext ON memory_files(extension);
        CREATE INDEX IF NOT EXISTS idx_memory_files_modified ON memory_files(file_modified DESC);
        CREATE INDEX IF NOT EXISTS idx_memory_files_content_fts ON memory_files USING GIN (to_tsvector('simple', COALESCE(content, '')));
        CREATE TABLE IF NOT EXISTS memory_files_sync_log (
            id SERIAL PRIMARY KEY,
            sync_started TIMESTAMPTZ DEFAULT NOW(),
            sync_completed TIMESTAMPTZ,
            files_processed INT,
            files_added INT,
            files_updated INT,
            files_unchanged INT,
            bytes_total BIGINT,
            error TEXT
        );
    """)
    conn.commit()
    cur.close()
    conn.close()

def get_file_info(filepath):
    try:
        with open(filepath, 'rb') as f:
            data = f.read()
        size = len(data)
        if size > MAX_FILE_SIZE:
            return None
        sha256 = hashlib.sha256(data).hexdigest()
        try:
            content = data.decode('utf-8')
        except UnicodeDecodeError:
            try:
                content = data.decode('latin-1')
            except Exception:
                return None
        return {"size": size, "sha256": sha256, "content": content}
    except Exception:
        return None

def sync_files():
    conn = psycopg2.connect(**LOCAL_DB)
    cur = conn.cursor()
    cur.execute("INSERT INTO memory_files_sync_log (sync_started) VALUES (NOW()) RETURNING id")
    log_id = cur.fetchone()[0]
    conn.commit()

    files_processed = 0
    files_added = 0
    files_updated = 0
    files_unchanged = 0
    bytes_total = 0
    seen_paths = set()

    try:
        for root, dirs, files in os.walk(EIRIK_ROOT):
            for filename in files:
                ext = os.path.splitext(filename)[1].lower()
                if ext not in TEXT_EXTENSIONS:
                    continue
                filepath = os.path.join(root, filename)
                rel_path = os.path.relpath(filepath, EIRIK_ROOT).replace("\\", "/")
                info = get_file_info(filepath)
                if not info:
                    continue
                files_processed += 1
                bytes_total += info["size"]
                seen_paths.add(rel_path)
                parts = rel_path.split("/")
                folder_prefix = parts[0] if len(parts) > 1 else "ROOT"
                file_modified = time.strftime("%Y-%m-%d %H:%M:%S+00", time.gmtime(os.path.getmtime(filepath)))
                cur.execute("SELECT sha256 FROM memory_files WHERE path = %s", (rel_path,))
                row = cur.fetchone()
                if row is None:
                    cur.execute("""
                        INSERT INTO memory_files (path, folder_prefix, filename, extension, size_bytes, sha256, content, file_modified, last_synced)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
                    """, (rel_path, folder_prefix, filename, ext, info["size"], info["sha256"], info["content"], file_modified))
                    files_added += 1
                elif row[0] != info["sha256"]:
                    cur.execute("""
                        UPDATE memory_files SET size_bytes = %s, sha256 = %s, content = %s, file_modified = %s, last_synced = NOW()
                        WHERE path = %s
                    """, (info["size"], info["sha256"], info["content"], file_modified, rel_path))
                    files_updated += 1
                else:
                    cur.execute("UPDATE memory_files SET last_synced = NOW() WHERE path = %s", (rel_path,))
                    files_unchanged += 1

        if seen_paths:
            placeholders = ",".join(["%s"] * len(seen_paths))
            cur.execute("DELETE FROM memory_files WHERE path NOT IN (" + placeholders + ")", tuple(seen_paths))

        cur.execute("""
            UPDATE memory_files_sync_log SET sync_completed = NOW(), files_processed = %s, files_added = %s,
                files_updated = %s, files_unchanged = %s, bytes_total = %s WHERE id = %s
        """, (files_processed, files_added, files_updated, files_unchanged, bytes_total, log_id))
        conn.commit()
        return files_processed, files_added, files_updated, files_unchanged
    except Exception as e:
        cur.execute("UPDATE memory_files_sync_log SET sync_completed = NOW(), error = %s WHERE id = %s", (str(e), log_id))
        conn.commit()
        raise
    finally:
        cur.close()
        conn.close()

def main():
    print("[memory-files-sync] Started, interval " + str(SYNC_INTERVAL) + "s, root " + EIRIK_ROOT, flush=True)
    if not wait_for_postgres():
        print("[memory-files-sync] FATAL: Postgres not ready after 120s", flush=True)
        return
    ensure_schema()
    while True:
        try:
            processed, added, updated, unchanged = sync_files()
            print("[memory-files-sync] OK: processed=" + str(processed) + " added=" + str(added) + " updated=" + str(updated) + " unchanged=" + str(unchanged), flush=True)
        except Exception as e:
            print("[memory-files-sync] ERROR: " + str(e), flush=True)
        time.sleep(SYNC_INTERVAL)

if __name__ == "__main__":
    main()

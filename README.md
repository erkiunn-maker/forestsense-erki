# forestsense-erki

**Eirik agentic memory infrastructure** - skills and toolkit for building AI agent memory backbones in Claude Code/Cowork environments, focused on the forestry domain.

Author: [Erki Unn](https://forestsense.ai) (Vestman Group, Forestsense AI builder)
Co-built with: **Eirik** (Cowork agent, Erki's digital twin)

## Quick Start - Mini-NAS in 30 minutes

If you have **Docker Desktop** + **PowerShell** + a **Supabase project**, you can run the local mini-NAS in ~30 min:

```powershell
git clone https://github.com/erkiunn-maker/forestsense-erki.git
cd forestsense-erki/mini-nas
pwsh ./setup.ps1
```

`setup.ps1` will:
1. Check Docker Desktop is installed and running
2. Create `.env` from `.env.example` (opens Notepad for you to edit)
3. Validate your `EIRIK_PATH`, `SUPABASE_URL`, `SUPABASE_KEY`
4. Start 4 Docker containers (postgres, pgadmin, sync-supabase, sync-memory-files)
5. Register a Windows Task Scheduler job for ZIP backups every 6h

After setup:
- **pgAdmin GUI:** http://localhost:5050
- **Postgres port:** 5432
- **Status check:** `docker compose ps`
- **Logs:** `docker logs forestsense-sync-supabase --tail 20`

## What you get

A **local AI agent memory backbone** running on your laptop:

- **Postgres 16** in Docker (port 5432, persistent volume)
- **pgAdmin** GUI (port 5050)
- **Supabase mirror** - pulls cloud agent_messages every 15 min into local Postgres for <5ms reads
- **Memory file indexer** - full-text searches your /Eirik/ folder content via Postgres GIN index, every 1h
- **ZIP backup** - 6h cron, keeps last 30 archives
- **Tailscale-ready** - access pgAdmin from your phone or other devices (just install Tailscale and add this machine)
- **VS Code Claude Code MCP-ready** - query local Postgres directly from Claude Code

Total disk: ~5 GB Docker overhead + your data. RAM at idle: ~500 MB.

## Repo layout

```
forestsense-erki/
├── README.md                  ← this file
├── LICENSE.md                 ← Dual MIT + Commercial
├── mini-nas/
│   ├── docker-compose.yml     ← 4 containers, parameterised via .env
│   ├── .env.example           ← copy to .env, fill in values
│   ├── setup.ps1              ← one-command Windows installer
│   ├── SKILL.md               ← public summary (full version in Drive)
│   └── scripts/
│       ├── sync_eirik.ps1     ← ZIP backup PowerShell script
│       ├── sync_supabase.py   ← Cloud Supabase mirror Python script
│       └── sync_memory_files.py  ← Memory file content indexer Python script
└── (more skills coming)
```

## Why this exists

Most AI agent setups use cloud-only memory (Supabase, Pinecone, etc.). This is fine until:

1. Your sandbox gets reset → agent forgets everything
2. Internet drops → agent can't read its own memory
3. Cloud latency 50ms+ per query → multi-agent orchestration is painful
4. Cloud bills grow as your memory archive grows

**Local mini-NAS solves all four** - Postgres on your laptop with 1h sync to cloud Supabase. <5ms latency. Cost: zero (uses your existing laptop).

When the **real NAS** arrives (Synology DS1825+ in our case), the Docker setup migrates in ~2 hours, no rewrites - the same `docker-compose.yml` works on Synology Container Manager.

## Status (2026-04-27)

| Skill | Status | Notes |
|---|---|---|
| **mini-nas** | 🟢 v1.0 plug-and-play | Built 2026-04-26, running 24/7 in Vestman ops, setup.ps1 ready |
| **agent-messaging-bus** | 🟡 documented in Drive | GitHub coming next |
| **directo-mcp** | ⏳ planned | Custom Directo BI Direct API MCP server |
| **lvm-geo-mcp** | ⏳ planned | LVM Geo ArcGIS proxy MCP server |

## Software-engineering retro

This setup was built incrementally over a 5-hour session with **8 bug iterations**. The full 19 KB SKILL.md (in Drive) documents every bug + fix, so you don't repeat them. Highlights:

- **Race condition** after reboot: `sync-supabase` starts before Postgres is ready. Fix: `wait_for_postgres()` retry loop (already in `sync_supabase.py`).
- **Markdown auto-link in chat tools**: paste artefacts when chat apps detect `filename.zip` patterns. Fix: use base64 encoding for paste-heavy workflows.
- **pgAdmin Master Password**: prompts after every restart unless disabled. Fix: `PGADMIN_CONFIG_MASTER_PASSWORD_REQUIRED: "False"` (already in `docker-compose.yml`).
- **Windows Defender Firewall blocks Tailscale**: phone can't reach laptop on 5050/5432. Fix: `New-NetFirewallRule -Direction Inbound -LocalPort 5050,5432` (manual step, run as Admin).
- **Docker Desktop autostart**: enable in Settings → General → "Start Docker Desktop when you sign in".
- **VS Code Claude Code MCP**: install `@modelcontextprotocol/server-postgres` globally, not via `npx -y` (which breaks Claude Code's argument parser).

## Migration to real NAS (Synology DS1825+ etc.)

When your physical NAS arrives, migration is ~2-3 hours:

1. `docker compose down` on laptop
2. Copy 4 things to NAS via SMB or USB:
   - `docker-compose.yml`
   - `scripts/` folder
   - `data/postgres/` (the Postgres volume)
   - `backups/` folder
3. Adjust `EIRIK_PATH`, `DATA_PATH`, `SCRIPTS_PATH`, `BACKUP_PATH` in `.env` to NAS paths
4. `docker compose up -d` on NAS via Container Manager
5. Install Tailscale on NAS for remote access

The full migration playbook is in Drive (mini-nas SKILL.md §7).

## License

Dual MIT + Commercial - see [LICENSE.md](LICENSE.md). MIT for personal/educational/internal use; commercial license required for paid redistribution. Vestman Group internal tooling automatically MIT.

## Always-clickable-links rule

Per Persistent Rule #22 (Erki + Eirik 2026-04-27): every reference to a system, file, project, MCP server, or repository must include a clickable link. This applies to all skills derived from forestsense-erki.

## Contact

Erki Unn - Vestman Group forestry leader, Forestsense AI builder
Email: erki.unn@forestsense.ai
Web: https://forestsense.ai

---

*Last updated: 2026-04-27 by Eirik (Cowork agent)*
*Built in collaboration with Erki Unn over 5h on 2026-04-26.*

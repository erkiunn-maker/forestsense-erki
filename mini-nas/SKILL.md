---
name: local-mini-nas-deployment
description: >
  Local mini-NAS deployment guide — Docker + Postgres + Supabase mirror + Tailscale + VS Code MCP
  for AI agent memory backup on Windows/macOS/Linux laptop. Built 2026-04-26 by Erki Unn + Eirik.
triggers:
  et: >
    mini-NAS, lokaalne Postgres, agendi mälu kindlustus, Supabase peegeldus,
    laptopi mini-NAS, NAS migratsioon DS1825+
  en: >
    local mini-NAS, agent memory backup, Postgres mirror, Supabase sync,
    laptop NAS deployment, Synology DS1825 migration
---

# Mini-NAS Deployment — SKILL v1.0

This is the **public summary** version. Full 19 KB skill (with detailed software-engineering retro of 8 bug iterations, line-by-line setup, NAS DS1825+ migration playbook) lives in **Drive**:

- [Forestsense Drive — `_KATUS/Skills/Tehniline_platvorm/local-mini-nas-deployment/`](https://drive.google.com/drive/folders/1CS3zP5pTFsJDCZSYZns8LvuoJ-DpFawj)
- Full SKILL file: `local-mini-nas-deployment_SKILL_v1.0.md` (19 KB, 11 sections)

## What this skill builds

A **local mini-NAS** running on your laptop:
- **Postgres 16** in Docker (port 5432, persistent volume)
- **pgAdmin** GUI (port 5050)
- **Supabase mirror** — pulls cloud agent_messages every 15 min into local Postgres
- **Memory file indexer** — full-text searches your /Eirik/ folder content via Postgres GIN index, every 1h
- **ZIP backup** — 6h cron, keeps last 30 archives
- **Tailscale VPN** — access pgAdmin from your phone or other devices
- **VS Code Claude Code MCP** — query local Postgres directly from Claude Code

## Setup time

- Erki + Eirik 2026-04-26: **~5 hours** (with 8 bug iterations — first-time inkremental build)
- Future team members using GitHub repo + setup.ps1: **~30 minutes** (planned v1.1)

## 5-phase setup overview

| Phase | What | Time |
|---|---|---|
| **A** | Docker + Postgres + ZIP backup | 45 min |
| **B** | Cloud-Supabase mirror | 30 min |
| **C** | Memory file content indexing | 25 min |
| **D** | Tailscale VPN | 10 min |
| **G** | VS Code Claude Code MCP | 15 min |

## Critical bugs to avoid

1. **Race condition** — `sync-supabase` starts before Postgres ready after reboot. Fix: `wait_for_postgres()` retry loop.
2. **Markdown auto-link in chat** — `timestamp.zip` becomes `[timestamp.zip](http://timestamp.zip)`. Fix: use `${ts}.zip` syntax or string concatenation.
3. **pgAdmin Master Password** — set `PGADMIN_CONFIG_MASTER_PASSWORD_REQUIRED: "False"` from start.
4. **Windows Defender Firewall blocks Tailscale** — add inbound rules for ports 5050 + 5432.
5. **Docker Desktop autostart** — enable in Settings → General.

Full retro: see Drive skill file §4 ("Mis läks valesti — õppetunnid").

## NAS DS1825+ migration (when real NAS arrives)

`docker-compose down` on laptop → copy 4 things to NAS (compose.yml + scripts/ + data/postgres/ + backups/) → adjust volume paths to `/volume1/docker/forestsense-os/` → `docker-compose up -d` on NAS. **~2-3 hours total**.

Full migration playbook: Drive skill file §7.

## License

Dual MIT + Commercial — see [LICENSE.md](https://github.com/erkiunn-maker/forestsense-erki/blob/main/LICENSE.md).

## Always-clickable-links rule

Per Forestsense Eirik project Persistent Rule #22: every reference to a system, file, project, MCP server, or repository must include a clickable link. This applies to all skills derived from forestsense-erki.

---

*Built by Erki Unn + Eirik (Cowork agent). 2026-04-27.*
*Full version: Drive Forestsense ecosystem.*

# forestsense-erki
Erki Unn and ForestSense repository 
# forestsense-erki

**Eirik agentic memory infrastructure** - skills and toolkit for building AI agent memory backbones in Claude Code/Cowork environments, focused on the forestry domain.

Author: Erki Unn (Vestman Group, Forestsense AI builder)
Co-built with: Eirik (Cowork agent, Erki's digital twin)

## What is this

A growing collection of production-tested skills for Claude agents:

- Local mini-NAS deployment (Docker + Postgres + Tailscale)
- - Multi-agent messaging bus (Supabase agent_messages pattern)
  - - Directo ERP integration (Estonian/Latvian accounting)
    - - LVM Geo (Latvian forestry data) integration
      - - Forestry domain workflows
       
        - These skills emerged from real Vestman Group operations (forestry, Baltic states) and are battle-tested in production.
       
        - ## Repo layout
       
        - ```
          forestsense-erki/
            README.md           <- this file
            LICENSE.md          <- MIT for code, commercial clause for enterprise
            mini-nas/           <- local mini-NAS deployment (1st skill)
              SKILL.md          <- step-by-step guide + software engineering retro
            agent-messaging-bus/  <- coming soon
            (more skills coming)
          ```

          ## Quick start - mini-NAS

          ```
          git clone https://github.com/erkiunn-maker/forestsense-erki.git
          cd forestsense-erki/mini-nas
          # Read SKILL.md for full step-by-step
          ```

          Setup time: ~30 min once setup.ps1 is ready. For now follow SKILL.md (5-phase guide A/B/C/D + G).

          ## Status

          | Skill | Status | Notes |
          |---|---|---|
          | mini-nas | v1.0 production | Built 2026-04-26, running 24/7 in Vestman ops |
          | agent-messaging-bus | documented | GitHub coming |
          | directo-mcp | planned | Custom Directo BI Direct MCP server |
          | lvm-geo-mcp | planned | LVM Geo ArcGIS proxy MCP server |

          ## License

          MIT for open-source. Commercial license required for paid redistribution. Contact Erki via forestsense.ai.

          ---

          Built in collaboration with Eirik. Last updated: 2026-04-27

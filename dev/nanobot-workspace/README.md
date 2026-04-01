# NanoBot Workspace

This folder is bind-mounted into the NanoBot container at `/config/nanobot/`.

## Contents

| Path | Description |
|------|-------------|
| `config.json` | Generated NanoBot configuration (auto-created on startup) |
| `workspace/` | NanoBot's AI workspace — markdown files, notes, tasks the AI creates |

## Dev mode (Docker Compose)

This directory is mounted as:
```
./nanobot-workspace  →  /config/nanobot  (inside container)
```

Edit files here in VS Code and they are immediately visible to the running NanoBot container.

## Real Home Assistant

In a real HA installation, `/config/nanobot/` is accessible via:
- **File Editor** add-on (built-in)
- **Studio Code Server** add-on
- **Samba** / **SSH** add-ons

The `config` map entry in `nanobot/config.yaml` grants the add-on read/write access to `/config`.

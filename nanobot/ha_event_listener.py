#!/usr/bin/env python3
"""HA Event Listener — Phase 3: Home Assistant Event Streaming.

Connects to the HA WebSocket API and subscribes to configured event types.
When an event fires, writes a JSON file to the NanoBot workspace events/
directory so the NanoBot cron/proactive agent can react to it.

Supported connection modes (auto-detected):
  1. HA Supervisor mode: connects to ws://supervisor/core/websocket using the
     SUPERVISOR_TOKEN from the environment (no manual token required).
  2. Standalone/dev mode: connects to the URL in HA_WEBSOCKET_URL using the
     HA_ACCESS_TOKEN from the environment.

Usage:
    python3 ha_event_listener.py

Environment variables:
    HA_WEBSOCKET_URL   WebSocket URL (default: ws://supervisor/core/websocket)
    HA_ACCESS_TOKEN    Long-Lived Access Token (auto-set from SUPERVISOR_TOKEN)
    HA_EVENT_TYPES     Comma-separated event types (default: state_changed)
    NANOBOT_WORKSPACE  Workspace path (default: /config/nanobot/workspace)
"""

import asyncio
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path


# ---------------------------------------------------------------------------
# Config from environment
# ---------------------------------------------------------------------------
def _get_config() -> dict:
    supervisor_token = os.environ.get("SUPERVISOR_TOKEN", "")
    ha_access_token = os.environ.get("HA_ACCESS_TOKEN", supervisor_token)

    # Prefer explicit URL, fall back to supervisor endpoint
    default_url = "ws://supervisor/core/websocket"
    ws_url = os.environ.get("HA_WEBSOCKET_URL", default_url)

    event_types_raw = os.environ.get("HA_EVENT_TYPES", "state_changed")
    event_types = [t.strip() for t in event_types_raw.split(",") if t.strip()]

    workspace = Path(os.environ.get("NANOBOT_WORKSPACE", "/config/nanobot/workspace"))
    events_dir = workspace / "events"

    return {
        "ws_url": ws_url,
        "access_token": ha_access_token,
        "event_types": event_types,
        "events_dir": events_dir,
    }


# ---------------------------------------------------------------------------
# WebSocket event listener
# ---------------------------------------------------------------------------
async def listen(cfg: dict) -> None:
    """Connect to HA WebSocket API and stream events to the workspace."""
    try:
        import websockets  # type: ignore[import-untyped]
    except ImportError:
        print(
            "[ha_event_listener] ERROR: 'websockets' package not found. "
            "Install it with: pip install websockets",
            file=sys.stderr,
        )
        sys.exit(1)

    events_dir: Path = cfg["events_dir"]
    events_dir.mkdir(parents=True, exist_ok=True)

    ws_url: str = cfg["ws_url"]
    token: str = cfg["access_token"]
    event_types: list = cfg["event_types"]

    print(f"[ha_event_listener] Connecting to {ws_url}", flush=True)
    print(f"[ha_event_listener] Subscribing to events: {event_types}", flush=True)

    reconnect_delay = 5  # seconds

    while True:
        try:
            async with websockets.connect(ws_url) as ws:
                # HA WebSocket protocol: first message is auth_required
                msg = json.loads(await ws.recv())
                if msg.get("type") != "auth_required":
                    print(
                        f"[ha_event_listener] Unexpected first message: {msg}",
                        file=sys.stderr,
                    )
                    await asyncio.sleep(reconnect_delay)
                    continue

                # Send auth
                await ws.send(json.dumps({"type": "auth", "access_token": token}))
                auth_result = json.loads(await ws.recv())

                if auth_result.get("type") == "auth_invalid":
                    print(
                        "[ha_event_listener] ERROR: Authentication failed. "
                        "Check SUPERVISOR_TOKEN / HA_ACCESS_TOKEN.",
                        file=sys.stderr,
                    )
                    sys.exit(1)

                if auth_result.get("type") != "auth_ok":
                    print(
                        f"[ha_event_listener] Unexpected auth response: {auth_result}",
                        file=sys.stderr,
                    )
                    await asyncio.sleep(reconnect_delay)
                    continue

                print("[ha_event_listener] Authenticated successfully.", flush=True)

                # Subscribe to each event type
                for sub_id, event_type in enumerate(event_types, start=1):
                    subscribe_msg = {
                        "id": sub_id,
                        "type": "subscribe_events",
                        "event_type": event_type,
                    }
                    await ws.send(json.dumps(subscribe_msg))
                    result = json.loads(await ws.recv())
                    if result.get("success"):
                        print(
                            f"[ha_event_listener] Subscribed to '{event_type}' (id={sub_id})",
                            flush=True,
                        )
                    else:
                        print(
                            f"[ha_event_listener] WARNING: Failed to subscribe to '{event_type}': {result}",
                            file=sys.stderr,
                        )

                reconnect_delay = 5  # reset on successful connect

                # Main receive loop
                async for raw in ws:
                    try:
                        msg = json.loads(raw)
                    except json.JSONDecodeError:
                        continue

                    if msg.get("type") != "event":
                        continue

                    event = msg.get("event", {})
                    event_type = event.get("event_type", "unknown")
                    event_data = event.get("data", {})

                    _write_event_file(events_dir, event_type, event_data)

        except (ConnectionRefusedError, OSError) as exc:
            print(
                f"[ha_event_listener] Connection failed: {exc}. "
                f"Retrying in {reconnect_delay}s...",
                file=sys.stderr,
                flush=True,
            )
            await asyncio.sleep(reconnect_delay)
            reconnect_delay = min(reconnect_delay * 2, 60)

        except Exception as exc:  # noqa: BLE001
            print(
                f"[ha_event_listener] Unexpected error: {exc}. "
                f"Retrying in {reconnect_delay}s...",
                file=sys.stderr,
                flush=True,
            )
            await asyncio.sleep(reconnect_delay)
            reconnect_delay = min(reconnect_delay * 2, 60)


def _write_event_file(events_dir: Path, event_type: str, data: dict) -> None:
    """Write a JSON event file to the workspace events/ directory.

    File naming: <timestamp>-<event_type>.json
    e.g.: 2025-04-01T22-05-33Z-state_changed.json

    NanoBot's cron agent polls this directory and processes new files.
    """
    now = datetime.now(timezone.utc)
    ts = now.strftime("%Y-%m-%dT%H-%M-%SZ")
    safe_type = event_type.replace("/", "_")
    filename = f"{ts}-{safe_type}.json"
    filepath = events_dir / filename

    payload = {
        "timestamp": now.isoformat(),
        "event_type": event_type,
        "data": data,
    }

    # For state_changed events: add a human-readable summary at top level
    if event_type == "state_changed":
        entity_id = data.get("entity_id", "")
        new_state = data.get("new_state") or {}
        old_state = data.get("old_state") or {}
        new_s = new_state.get("state", "unknown")
        old_s = old_state.get("state", "unknown")
        payload["summary"] = f"{entity_id}: {old_s} → {new_s}"

    try:
        filepath.write_text(json.dumps(payload, indent=2, ensure_ascii=False))
        # Print compact log (not full payload to avoid log spam)
        summary = payload.get("summary", event_type)
        print(f"[ha_event_listener] Event: {summary}", flush=True)
    except OSError as exc:
        print(f"[ha_event_listener] Failed to write {filepath}: {exc}", file=sys.stderr)


# ---------------------------------------------------------------------------
# Cleanup: delete processed event files older than N hours
# ---------------------------------------------------------------------------
def _cleanup_old_events(events_dir: Path, max_age_hours: int = 24) -> None:
    """Remove event files older than max_age_hours to prevent accumulation."""
    import time

    cutoff = time.time() - (max_age_hours * 3600)
    removed = 0
    for f in events_dir.glob("*.json"):
        try:
            if f.stat().st_mtime < cutoff:
                f.unlink()
                removed += 1
        except OSError:
            pass
    if removed:
        print(f"[ha_event_listener] Cleaned up {removed} old event files.", flush=True)


async def _cleanup_loop(events_dir: Path) -> None:
    """Periodically clean up old event files."""
    while True:
        await asyncio.sleep(3600)  # every hour
        _cleanup_old_events(events_dir)


async def main() -> None:
    cfg = _get_config()

    if not cfg["access_token"]:
        print(
            "[ha_event_listener] ERROR: No access token. "
            "Set SUPERVISOR_TOKEN or HA_ACCESS_TOKEN.",
            file=sys.stderr,
        )
        sys.exit(1)

    # Run both loops concurrently
    await asyncio.gather(
        listen(cfg),
        _cleanup_loop(cfg["events_dir"]),
    )


if __name__ == "__main__":
    asyncio.run(main())

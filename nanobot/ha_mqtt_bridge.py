#!/usr/bin/env python3
"""HA MQTT Bridge — Phase 4: Bidirectional MQTT Integration.

Provides two-way MQTT communication between Home Assistant automations and NanoBot:

  INCOMING (HA → NanoBot):
    Subscribe to "nanobot/inbox" topic.
    Messages are POSTed to NanoBot's OpenAI-compatible API at localhost:8900
    via POST /v1/chat/completions (requires api_enabled=true in the add-on config).
    Message format: plain text (the task), or JSON {"task": "...", "session": "..."}

  OUTGOING (NanoBot → HA):
    NanoBot's cron/proactive agent publishes results to "nanobot/outbox" by
    writing a JSON file to /config/nanobot/workspace/mqtt_publish/<topic>.json
    This bridge watches that directory and publishes the messages.

  STATUS:
    Publishes NanoBot availability to "nanobot/status" (online/offline).

Environment variables (auto-set by run.sh from bashio::services mqtt):
    MQTT_HOST          Broker hostname/IP (required)
    MQTT_PORT          Broker port (default: 1883)
    MQTT_USER          Username (optional)
    MQTT_PASS          Password (optional)
    NANOBOT_API_URL    NanoBot API server URL (default: http://localhost:8900)
    NANOBOT_WORKSPACE  Workspace path (default: /config/nanobot/workspace)

HA Automation example (send task to NanoBot):
    service: mqtt.publish
    data:
      topic: nanobot/inbox
      payload: "What lights are on in the living room?"

HA Automation example (react to NanoBot response):
    trigger:
      - platform: mqtt
        topic: nanobot/outbox
    action:
      - service: notify.mobile_app
        data:
          message: "{{ trigger.payload }}"
"""

import json
import os
import sys
import time
import urllib.error as urllib_error
import urllib.request as urllib_request
from pathlib import Path

try:
    import paho.mqtt.client as mqtt_client  # type: ignore[import-untyped]
except ImportError:
    print(
        "[ha_mqtt_bridge] ERROR: 'paho-mqtt' package not found. "
        "Install it with: pip install paho-mqtt",
        file=sys.stderr,
    )
    sys.exit(1)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
MQTT_HOST = os.environ.get("MQTT_HOST", "")
MQTT_PORT = int(os.environ.get("MQTT_PORT", "1883"))
MQTT_USER = os.environ.get("MQTT_USER", "")
MQTT_PASS = os.environ.get("MQTT_PASS", "")
API_URL = os.environ.get("NANOBOT_API_URL", "http://localhost:8900")
WORKSPACE = Path(os.environ.get("NANOBOT_WORKSPACE", "/config/nanobot/workspace"))

INBOX_TOPIC = "nanobot/inbox"
OUTBOX_TOPIC = "nanobot/outbox"
STATUS_TOPIC = "nanobot/status"
PUBLISH_DIR = WORKSPACE / "mqtt_publish"

CLIENT_ID = "nanobot-ha-bridge"
RECONNECT_DELAY_SEC = 5


# ---------------------------------------------------------------------------
# Post task to NanoBot API (OpenAI-compatible endpoint)
# ---------------------------------------------------------------------------
def post_to_nanobot(task: str) -> str | None:
    """POST a task to NanoBot's /v1/chat/completions endpoint.

    Returns the assistant response text, or None on failure.
    """
    payload = json.dumps(
        {
            "messages": [{"role": "user", "content": task}],
            "stream": False,
        }
    ).encode()
    req = urllib_request.Request(
        f"{API_URL}/v1/chat/completions",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib_request.urlopen(req, timeout=120) as resp:
            body = json.loads(resp.read().decode())
            # Extract assistant message from OpenAI-format response
            choices = body.get("choices", [])
            if choices:
                content = choices[0].get("message", {}).get("content", "")
                print(f"[ha_mqtt_bridge] Response: {content[:120]}", flush=True)
                return content
            print(f"[ha_mqtt_bridge] Empty response from API", flush=True)
            return None
    except urllib_error.HTTPError as exc:
        error_body = ""
        try:
            error_body = exc.read().decode()[:200]
        except Exception:
            pass
        print(
            f"[ha_mqtt_bridge] WARNING: API error {exc.code}: {error_body}",
            file=sys.stderr,
        )
        return None
    except urllib_error.URLError as exc:
        print(
            f"[ha_mqtt_bridge] WARNING: Failed to reach NanoBot API at {API_URL}: {exc}",
            file=sys.stderr,
        )
        return None


# ---------------------------------------------------------------------------
# MQTT callbacks
# ---------------------------------------------------------------------------
def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        print(
            f"[ha_mqtt_bridge] Connected to MQTT broker {MQTT_HOST}:{MQTT_PORT}",
            flush=True,
        )
        client.subscribe(INBOX_TOPIC)
        client.publish(STATUS_TOPIC, "online", retain=True)
        print(f"[ha_mqtt_bridge] Subscribed to '{INBOX_TOPIC}'", flush=True)
    else:
        print(f"[ha_mqtt_bridge] Connection failed (rc={rc})", file=sys.stderr)


def on_disconnect(client, userdata, rc, properties=None, reason_code=None):
    if rc != 0:
        print(
            f"[ha_mqtt_bridge] Unexpected disconnect (rc={rc}). "
            f"Reconnecting in {RECONNECT_DELAY_SEC}s...",
            file=sys.stderr,
            flush=True,
        )


def on_message(client, userdata, msg):
    """Handle incoming MQTT messages from HA → NanoBot."""
    try:
        raw = msg.payload.decode("utf-8").strip()
    except UnicodeDecodeError:
        print(
            "[ha_mqtt_bridge] WARNING: Received non-UTF-8 message, ignoring.",
            file=sys.stderr,
        )
        return

    if not raw:
        return

    # Support both plain text and JSON payloads
    task = raw
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            task = data.get("task", data.get("message", raw))
    except json.JSONDecodeError:
        pass  # treat as plain text

    print(f"[ha_mqtt_bridge] Inbox: {task[:100]}", flush=True)

    # Post to NanoBot API and optionally publish response to outbox
    response = post_to_nanobot(task)
    if response:
        client.publish(OUTBOX_TOPIC, response)
        print(f"[ha_mqtt_bridge] Published response to '{OUTBOX_TOPIC}'", flush=True)


# ---------------------------------------------------------------------------
# Outgoing publish watcher
# ---------------------------------------------------------------------------
def poll_publish_queue(client: mqtt_client.Client) -> None:
    """Check PUBLISH_DIR for files to publish, send, then delete."""
    if not PUBLISH_DIR.exists():
        return

    for filepath in sorted(PUBLISH_DIR.glob("*.json")):
        try:
            data = json.loads(filepath.read_text())
            topic = data.get("topic", OUTBOX_TOPIC)
            payload = data.get("payload", "")
            retain = data.get("retain", False)

            if not isinstance(payload, str):
                payload = json.dumps(payload)

            client.publish(topic, payload, retain=retain)
            print(
                f"[ha_mqtt_bridge] Published to '{topic}': {str(payload)[:80]}",
                flush=True,
            )
        except (json.JSONDecodeError, OSError) as exc:
            print(
                f"[ha_mqtt_bridge] WARNING: Failed to publish {filepath}: {exc}",
                file=sys.stderr,
            )
        finally:
            try:
                filepath.unlink()
            except OSError:
                pass


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    if not MQTT_HOST:
        print("[ha_mqtt_bridge] ERROR: MQTT_HOST not set.", file=sys.stderr)
        sys.exit(1)

    PUBLISH_DIR.mkdir(parents=True, exist_ok=True)

    # Build MQTT client (supports both paho-mqtt v1 and v2 APIs)
    try:
        # paho-mqtt >= 2.0
        CallbackAPIVersion = getattr(mqtt_client, "CallbackAPIVersion", None)
        if CallbackAPIVersion is not None:
            client = mqtt_client.Client(
                client_id=CLIENT_ID,
                callback_api_version=CallbackAPIVersion.VERSION2,  # type: ignore[attr-defined]
            )
        else:
            client = mqtt_client.Client(client_id=CLIENT_ID)
    except Exception:
        client = mqtt_client.Client(client_id=CLIENT_ID)

    client.will_set(STATUS_TOPIC, "offline", retain=True)

    if MQTT_USER:
        client.username_pw_set(MQTT_USER, MQTT_PASS)

    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_message = on_message

    while True:
        try:
            client.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
            break
        except (ConnectionRefusedError, OSError) as exc:
            print(
                f"[ha_mqtt_bridge] Cannot connect to {MQTT_HOST}:{MQTT_PORT}: {exc}. "
                f"Retrying in {RECONNECT_DELAY_SEC}s...",
                file=sys.stderr,
                flush=True,
            )
            time.sleep(RECONNECT_DELAY_SEC)

    client.loop_start()

    print(
        "[ha_mqtt_bridge] Bridge running. Polling for outgoing messages...", flush=True
    )

    try:
        while True:
            poll_publish_queue(client)
            time.sleep(2)
    except KeyboardInterrupt:
        pass
    finally:
        client.publish(STATUS_TOPIC, "offline", retain=True)
        client.loop_stop()
        client.disconnect()
        print("[ha_mqtt_bridge] Stopped.", flush=True)


if __name__ == "__main__":
    main()

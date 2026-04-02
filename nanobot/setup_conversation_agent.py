#!/usr/bin/env python3
"""Auto-register NanoBot as a Home Assistant Conversation Agent.

Uses the HA WebSocket API to:
1. Check if an openai_conversation config entry already exists for NanoBot
2. If not, create one via the config flow
3. Optionally set it as the default conversation agent in the assist pipeline

Requires:
  - SUPERVISOR_TOKEN env var (auto-set inside HA add-ons)
  - NanoBot API server already running on port 8900
  - The openai_conversation integration available in HA Core

Usage:
    python3 /app/setup_conversation_agent.py
"""

import asyncio
import json
import os
import sys

SUPERVISOR_TOKEN = os.environ.get("SUPERVISOR_TOKEN", "")
WS_URL = "ws://supervisor/core/websocket"
NANOBOT_API_BASE = "http://localhost:8900/v1"
# The API key can be anything non-empty — NanoBot API doesn't validate it.
NANOBOT_API_KEY = "nanobot-local"
INTEGRATION_DOMAIN = "openai_conversation"

LOG_PREFIX = "[setup_conversation_agent]"


async def ws_send_and_receive(ws, msg: dict) -> dict:
    """Send a WS message and wait for the matching response by id."""
    await ws.send(json.dumps(msg))
    while True:
        raw = await ws.recv()
        resp = json.loads(raw)
        if resp.get("id") == msg.get("id"):
            return resp


async def main() -> None:
    try:
        import websockets  # type: ignore[import-untyped]
    except ImportError:
        print(f"{LOG_PREFIX} ERROR: websockets package not found.", file=sys.stderr)
        sys.exit(1)

    if not SUPERVISOR_TOKEN:
        print(
            f"{LOG_PREFIX} ERROR: SUPERVISOR_TOKEN not set. "
            "This script only works inside an HA add-on.",
            file=sys.stderr,
        )
        sys.exit(1)

    print(f"{LOG_PREFIX} Connecting to {WS_URL}...", flush=True)

    try:
        async with websockets.connect(WS_URL) as ws:
            # --- Authenticate ---
            msg = json.loads(await ws.recv())
            if msg.get("type") != "auth_required":
                print(f"{LOG_PREFIX} Unexpected: {msg}", file=sys.stderr)
                return

            await ws.send(
                json.dumps(
                    {
                        "type": "auth",
                        "access_token": SUPERVISOR_TOKEN,
                    }
                )
            )
            auth_result = json.loads(await ws.recv())
            if auth_result.get("type") != "auth_ok":
                print(f"{LOG_PREFIX} Auth failed: {auth_result}", file=sys.stderr)
                return

            print(f"{LOG_PREFIX} Authenticated.", flush=True)

            # --- Check existing config entries ---
            msg_id = 1
            result = await ws_send_and_receive(
                ws,
                {
                    "id": msg_id,
                    "type": "config_entries/get",
                    "domain": INTEGRATION_DOMAIN,
                },
            )

            entries = result.get("result", [])
            for entry in entries:
                data = entry.get("data", {})
                base_url = data.get("base_url", "")
                # Check if this entry already points at our NanoBot API
                if "localhost:8900" in base_url or "127.0.0.1:8900" in base_url:
                    entry_id = entry.get("entry_id", "")
                    print(
                        f"{LOG_PREFIX} NanoBot conversation agent already configured "
                        f"(entry_id={entry_id}). Skipping creation.",
                        flush=True,
                    )
                    # Still try to set as default pipeline agent
                    await _set_default_agent(ws, entry_id, msg_id + 1)
                    return

            print(
                f"{LOG_PREFIX} No existing NanoBot entry found. "
                "Creating via config flow...",
                flush=True,
            )

            # --- Init config flow ---
            msg_id += 1
            result = await ws_send_and_receive(
                ws,
                {
                    "id": msg_id,
                    "type": "config_entries/flow",
                    "handler": INTEGRATION_DOMAIN,
                    "context": {"source": "user"},
                },
            )

            if not result.get("success", True):
                error = result.get("error", {})
                print(
                    f"{LOG_PREFIX} Failed to init config flow: {error}", file=sys.stderr
                )
                return

            flow_id = result.get("result", {}).get("flow_id")
            step_id = result.get("result", {}).get("step_id")
            flow_type = result.get("result", {}).get("type")

            if not flow_id:
                print(f"{LOG_PREFIX} No flow_id in response: {result}", file=sys.stderr)
                return

            print(
                f"{LOG_PREFIX} Config flow started: flow_id={flow_id}, "
                f"step_id={step_id}, type={flow_type}",
                flush=True,
            )

            # --- Submit the user step ---
            # The openai_conversation config flow expects:
            #   step "user": {"api_key": str, "base_url": str (optional)}
            msg_id += 1
            result = await ws_send_and_receive(
                ws,
                {
                    "id": msg_id,
                    "type": "config_entries/flow",
                    "flow_id": flow_id,
                    "data": {
                        "api_key": NANOBOT_API_KEY,
                        "base_url": NANOBOT_API_BASE,
                    },
                },
            )

            result_data = result.get("result", {})
            result_type = result_data.get("type")

            if result_type == "create_entry":
                entry_id = result_data.get("result", {}).get("entry_id", "")
                title = result_data.get("title", "")
                print(
                    f"{LOG_PREFIX} SUCCESS: Config entry created! "
                    f"title='{title}', entry_id={entry_id}",
                    flush=True,
                )

                # Set as default conversation agent
                await _set_default_agent(ws, entry_id, msg_id + 1)

            elif result_type == "form":
                # Flow wants another step — maybe model selection
                next_step = result_data.get("step_id", "")
                print(
                    f"{LOG_PREFIX} Flow requires another step: {next_step}", flush=True
                )

                # For newer HA versions, the flow may have a second step
                # for model selection. Try to submit with defaults.
                if next_step:
                    msg_id += 1
                    result2 = await ws_send_and_receive(
                        ws,
                        {
                            "id": msg_id,
                            "type": "config_entries/flow",
                            "flow_id": flow_id,
                            "data": {},  # accept defaults
                        },
                    )
                    r2 = result2.get("result", {})
                    if r2.get("type") == "create_entry":
                        entry_id = r2.get("result", {}).get("entry_id", "")
                        print(
                            f"{LOG_PREFIX} SUCCESS: Entry created after "
                            f"step '{next_step}', entry_id={entry_id}",
                            flush=True,
                        )
                        await _set_default_agent(ws, entry_id, msg_id + 1)
                    else:
                        print(
                            f"{LOG_PREFIX} WARNING: Unexpected result after "
                            f"step '{next_step}': {r2}",
                            file=sys.stderr,
                        )

            elif result_type == "abort":
                reason = result_data.get("reason", "unknown")
                print(f"{LOG_PREFIX} Flow aborted: {reason}", flush=True)
                if reason == "already_configured":
                    print(f"{LOG_PREFIX} Integration already exists.", flush=True)

            else:
                print(f"{LOG_PREFIX} Unexpected flow result: {result}", file=sys.stderr)

    except (ConnectionRefusedError, OSError) as exc:
        print(f"{LOG_PREFIX} Cannot connect to HA WebSocket: {exc}", file=sys.stderr)
    except Exception as exc:  # noqa: BLE001
        print(f"{LOG_PREFIX} Error: {exc}", file=sys.stderr)


async def _set_default_agent(ws, entry_id: str, start_msg_id: int) -> None:
    """Set the NanoBot conversation agent as the default in the assist pipeline.

    HA stores assist pipelines in config/.storage/core.assist_pipeline.
    We use the WS API to list pipelines and update the preferred one.
    """
    if not entry_id:
        return

    # The conversation agent entity_id format for openai_conversation:
    # conversation.<slug> where slug comes from the entry title
    # However, for setting the pipeline we need the actual agent ID.
    # The format is: "conversation.openai_conversation_<entry_id_first_part>"
    # But it's simpler to just list entities and find the matching one.

    msg_id = start_msg_id

    try:
        # List assist pipelines
        result = await ws_send_and_receive(
            ws,
            {
                "id": msg_id,
                "type": "assist_pipeline/pipeline/list",
            },
        )

        if not result.get("success"):
            print(
                f"{LOG_PREFIX} Could not list assist pipelines: {result}",
                file=sys.stderr,
            )
            return

        pipelines = result.get("result", {}).get("pipelines", [])
        preferred_id = result.get("result", {}).get("preferred_pipeline")

        if not pipelines:
            print(
                f"{LOG_PREFIX} No assist pipelines found. "
                "User can set the agent manually.",
                flush=True,
            )
            return

        # Find the conversation entity for our config entry.
        # Try to get it from the entity registry.
        msg_id += 1
        result = await ws_send_and_receive(
            ws,
            {
                "id": msg_id,
                "type": "config/entity_registry/list",
            },
        )

        agent_entity_id = None
        if result.get("success"):
            for entity in result.get("result", []):
                if entity.get("config_entry_id") == entry_id and entity.get(
                    "entity_id", ""
                ).startswith("conversation."):
                    agent_entity_id = entity["entity_id"]
                    break

        if not agent_entity_id:
            # Fallback: try common pattern
            print(
                f"{LOG_PREFIX} Could not find conversation entity for "
                f"entry_id={entry_id}. Skipping pipeline update.",
                flush=True,
            )
            return

        print(f"{LOG_PREFIX} Found conversation entity: {agent_entity_id}", flush=True)

        # Update the preferred pipeline to use our agent
        if preferred_id:
            # Find the preferred pipeline
            preferred = None
            for p in pipelines:
                if p.get("id") == preferred_id:
                    preferred = p
                    break

            if preferred and preferred.get("conversation_engine") != agent_entity_id:
                msg_id += 1
                result = await ws_send_and_receive(
                    ws,
                    {
                        "id": msg_id,
                        "type": "assist_pipeline/pipeline/update",
                        "pipeline_id": preferred_id,
                        "conversation_engine": agent_entity_id,
                        "conversation_language": preferred.get(
                            "conversation_language", "en"
                        ),
                        "language": preferred.get("language", "en"),
                        "name": preferred.get("name", "Home Assistant"),
                        "stt_engine": preferred.get("stt_engine"),
                        "stt_language": preferred.get("stt_language"),
                        "tts_engine": preferred.get("tts_engine"),
                        "tts_language": preferred.get("tts_language"),
                        "tts_voice": preferred.get("tts_voice"),
                        "wake_word_entity": preferred.get("wake_word_entity"),
                        "wake_word_id": preferred.get("wake_word_id"),
                    },
                )

                if result.get("success"):
                    print(
                        f"{LOG_PREFIX} Set '{agent_entity_id}' as the "
                        f"conversation agent in pipeline '{preferred.get('name')}'.",
                        flush=True,
                    )
                else:
                    print(
                        f"{LOG_PREFIX} WARNING: Failed to update pipeline: {result}",
                        file=sys.stderr,
                    )
            else:
                print(f"{LOG_PREFIX} Pipeline already uses NanoBot agent.", flush=True)

    except Exception as exc:  # noqa: BLE001
        print(f"{LOG_PREFIX} Pipeline setup error (non-fatal): {exc}", file=sys.stderr)


if __name__ == "__main__":
    asyncio.run(main())

#!/usr/bin/env bash
# ==============================================================================
# NanoBot AI Assistant - Home Assistant Add-on Entrypoint
# ==============================================================================
# Called via: /usr/bin/with-contenv /run.sh
# with-contenv ensures s6-overlay exports NANOBOT_* env vars into this script.
set -euo pipefail

# Detect if running under HA Supervisor (real token vs dev dummy)
# In dev mode, SUPERVISOR_TOKEN is set to "dev-token" or not set at all
IS_HA_SUPERVISOR=false
if [ -n "${SUPERVISOR_TOKEN:-}" ] && [ "${SUPERVISOR_TOKEN}" != "dev-token" ]; then
    # Try to source bashio
    if [ -f /usr/lib/bashio/bashio.sh ]; then
        # shellcheck source=/dev/null
        source /usr/lib/bashio/bashio.sh
        IS_HA_SUPERVISOR=true
    fi
fi

if [ "${IS_HA_SUPERVISOR}" = "true" ]; then
    # HA Supervisor environment — use bashio
    LOG_LEVEL=$(bashio::config 'log_level' 'info')
    API_ENABLED=$(bashio::config 'api_enabled' 'false')
    AUTO_CONVERSATION_AGENT=$(bashio::config 'auto_conversation_agent' 'false')
    HA_MCP_ENABLED=$(bashio::config 'ha_mcp_enabled' 'false')
    HA_EVENTS_ENABLED=$(bashio::config 'ha_events_enabled' 'false')
    HA_EVENT_TYPES=$(bashio::config 'ha_event_types' 'state_changed')
    MQTT_ENABLED=$(bashio::config 'mqtt_enabled' 'false')
    WEBUI_ENABLED=$(bashio::config 'webui_enabled' 'true')
    bashio::log.info "Starting NanoBot AI Assistant..."
    bashio::log.info "Log level: ${LOG_LEVEL}"
    bashio::log.info "Generating NanoBot configuration..."
else
    # Standalone Docker environment (dev mode)
    # Read from options.json, but allow NANOBOT_* env vars to override.
    # (s6-overlay may strip docker env vars, so options.json is the primary source)
    LOG_LEVEL=$(python3 -c "import os,json; d=json.load(open('/data/options.json')); print(os.environ.get('NANOBOT_LOG_LEVEL','').strip() or d.get('log_level','info'))" 2>/dev/null || echo "info")
    API_ENABLED=$(python3 -c "import os,json; d=json.load(open('/data/options.json')); v=os.environ.get('NANOBOT_API_ENABLED','').strip().lower(); print(v if v in ('true','false') else str(d.get('api_enabled',False)).lower())" 2>/dev/null || echo "false")
    AUTO_CONVERSATION_AGENT=$(python3 -c "import os,json; d=json.load(open('/data/options.json')); v=os.environ.get('NANOBOT_AUTO_CONVERSATION_AGENT','').strip().lower(); print(v if v in ('true','false') else str(d.get('auto_conversation_agent',False)).lower())" 2>/dev/null || echo "false")
    HA_MCP_ENABLED=$(python3 -c "import os,json; d=json.load(open('/data/options.json')); v=os.environ.get('NANOBOT_HA_MCP_ENABLED','').strip().lower(); print(v if v in ('true','false') else str(d.get('ha_mcp_enabled',False)).lower())" 2>/dev/null || echo "false")
    HA_EVENTS_ENABLED=$(python3 -c "import os,json; d=json.load(open('/data/options.json')); v=os.environ.get('NANOBOT_HA_EVENTS_ENABLED','').strip().lower(); print(v if v in ('true','false') else str(d.get('ha_events_enabled',False)).lower())" 2>/dev/null || echo "false")
    HA_EVENT_TYPES=$(python3 -c "import os,json; d=json.load(open('/data/options.json')); print(os.environ.get('NANOBOT_HA_EVENT_TYPES','').strip() or d.get('ha_event_types','state_changed'))" 2>/dev/null || echo "state_changed")
    MQTT_ENABLED=$(python3 -c "import os,json; d=json.load(open('/data/options.json')); v=os.environ.get('NANOBOT_MQTT_ENABLED','').strip().lower(); print(v if v in ('true','false') else str(d.get('mqtt_enabled',False)).lower())" 2>/dev/null || echo "false")
    WEBUI_ENABLED=$(python3 -c "import os,json; d=json.load(open('/data/options.json')); v=os.environ.get('NANOBOT_WEBUI_ENABLED','').strip().lower(); print(v if v in ('true','false') else str(d.get('webui_enabled',True)).lower())" 2>/dev/null || echo "true")
    echo "[INFO] Starting NanoBot AI Assistant (standalone/dev mode)..."
    echo "[INFO] Log level: ${LOG_LEVEL}"
    echo "[INFO] Generating NanoBot configuration..."
fi

# Generate nanobot config.json from HA options
# (set -e exits on failure automatically)
python3 /app/generate_config.py

echo "[INFO] Configuration generated successfully."

# Set NANOBOT log level via environment (needed early for nanobot serve)
case "${LOG_LEVEL}" in
    trace)   export LOGURU_LEVEL="TRACE" ;;
    debug)   export LOGURU_LEVEL="DEBUG" ;;
    info)    export LOGURU_LEVEL="INFO" ;;
    warning) export LOGURU_LEVEL="WARNING" ;;
    error)   export LOGURU_LEVEL="ERROR" ;;
    *)       export LOGURU_LEVEL="INFO" ;;
esac

# ==============================================================================
# Phase 2 — OpenAI-compatible API Server (nanobot_api_server.py)
# `nanobot gateway` does NOT include an HTTP API — it only runs channels.
# Our standalone API server provides POST /v1/chat/completions on port 8900.
# This is required for: HA Conversation integration, MQTT bridge inbox.
# ==============================================================================
if [ "${API_ENABLED}" = "true" ]; then
    echo "[INFO] Starting NanoBot API server on port 8900..."
    python3 /app/nanobot_api_server.py &
    API_SERVER_PID=$!
    echo "[INFO] API server started (PID: ${API_SERVER_PID})"

    # Wait briefly for the API server to bind before starting dependents
    sleep 2
else
    echo "[INFO] OpenAI-compatible API: disabled"
fi

# ==============================================================================
# Phase 2b — Auto-register as HA Conversation Agent
# Requires API server to be running (api_enabled=true).
# Uses HA WebSocket API to create an openai_conversation config entry
# pointing at NanoBot's API, then sets it as the default assist agent.
# Only works under real HA Supervisor (SUPERVISOR_TOKEN must be valid).
# ==============================================================================
if [ "${AUTO_CONVERSATION_AGENT}" = "true" ]; then
    if [ "${API_ENABLED}" != "true" ]; then
        echo "[WARNING] auto_conversation_agent=true but api_enabled=false."
        echo "[WARNING] The API server must be running for conversation agent registration."
        echo "[WARNING] Enabling api_enabled would fix this."
    elif [ "${IS_HA_SUPERVISOR}" = "true" ] || [ -n "${SUPERVISOR_TOKEN:-}" ]; then
        echo "[INFO] Auto-registering NanoBot as HA conversation agent..."
        # Run in background — non-blocking, best-effort.
        # If it fails, the add-on still starts normally.
        python3 /app/setup_conversation_agent.py &
        SETUP_AGENT_PID=$!
        echo "[INFO] Conversation agent setup started (PID: ${SETUP_AGENT_PID})"
    else
        echo "[INFO] auto_conversation_agent: skipped (not running under HA Supervisor)"
    fi
else
    echo "[INFO] Auto conversation agent registration: disabled"
fi

# ==============================================================================
# Phase 3 — HA Event Listener
# Start the WebSocket event listener as a background process if enabled.
# ==============================================================================
if [ "${HA_EVENTS_ENABLED}" = "true" ]; then
    echo "[INFO] Starting HA event listener (event types: ${HA_EVENT_TYPES})..."

    # Pass event types and workspace to the listener via env vars
    export HA_EVENT_TYPES="${HA_EVENT_TYPES}"
    export NANOBOT_WORKSPACE="/config/nanobot/workspace"

    python3 /app/ha_event_listener.py &
    EVENT_LISTENER_PID=$!
    echo "[INFO] HA event listener started (PID: ${EVENT_LISTENER_PID})"
else
    echo "[INFO] HA event listener: disabled"
fi

# ==============================================================================
# Phase 4 — MQTT Bridge
# Auto-detect Mosquitto and start MQTT bridge if enabled.
# NOTE: MQTT inbox requires the API server (api_enabled=true) to forward
# messages via POST /v1/chat/completions.
# ==============================================================================
if [ "${MQTT_ENABLED}" = "true" ]; then
    if [ "${API_ENABLED}" != "true" ]; then
        echo "[WARNING] mqtt_enabled=true but api_enabled=false."
        echo "[WARNING] MQTT inbox messages cannot be forwarded without the API server."
        echo "[WARNING] Set api_enabled=true to enable MQTT → NanoBot message routing."
    fi

    echo "[INFO] MQTT integration enabled — detecting broker..."

    MQTT_HOST=""
    MQTT_PORT="1883"
    MQTT_USER=""
    MQTT_PASS=""

    if [ "${IS_HA_SUPERVISOR}" = "true" ]; then
        # Auto-detect Mosquitto broker from HA Supervisor service discovery
        if bashio::services.available "mqtt"; then
            MQTT_HOST=$(bashio::services "mqtt" "host")
            MQTT_PORT=$(bashio::services "mqtt" "port")
            MQTT_USER=$(bashio::services "mqtt" "username")
            MQTT_PASS=$(bashio::services "mqtt" "password")
            bashio::log.info "Mosquitto broker detected at ${MQTT_HOST}:${MQTT_PORT}"
        else
            bashio::log.warning "mqtt_enabled=true but no MQTT broker found via service discovery."
            bashio::log.warning "Install the Mosquitto broker add-on, or set MQTT_HOST manually."
        fi
    else
        # Dev mode: read from env vars or options.json (s6-overlay may strip docker env vars)
        MQTT_HOST=$(python3 -c "import os,json; d=json.load(open('/data/options.json')); print(os.environ.get('MQTT_HOST','').strip() or os.environ.get('NANOBOT_MQTT_HOST','').strip() or d.get('mqtt_host',''))" 2>/dev/null || echo "")
        MQTT_PORT=$(python3 -c "import os,json; d=json.load(open('/data/options.json')); print(os.environ.get('MQTT_PORT','').strip() or os.environ.get('NANOBOT_MQTT_PORT','').strip() or str(d.get('mqtt_port',1883)))" 2>/dev/null || echo "1883")
        MQTT_USER=$(python3 -c "import os,json; d=json.load(open('/data/options.json')); print(os.environ.get('MQTT_USER','').strip() or os.environ.get('NANOBOT_MQTT_USER','').strip() or d.get('mqtt_user',''))" 2>/dev/null || echo "")
        MQTT_PASS=$(python3 -c "import os,json; d=json.load(open('/data/options.json')); print(os.environ.get('MQTT_PASS','').strip() or os.environ.get('NANOBOT_MQTT_PASS','').strip() or d.get('mqtt_pass',''))" 2>/dev/null || echo "")
    fi

    if [ -n "${MQTT_HOST}" ]; then
        export MQTT_HOST MQTT_PORT MQTT_USER MQTT_PASS
        export NANOBOT_WORKSPACE="/config/nanobot/workspace"
        # MQTT bridge posts to the API server on port 8900
        export NANOBOT_API_URL="http://localhost:8900"

        echo "[INFO] Starting MQTT bridge (${MQTT_HOST}:${MQTT_PORT})..."

        python3 /app/ha_mqtt_bridge.py &
        MQTT_BRIDGE_PID=$!
        echo "[INFO] MQTT bridge started (PID: ${MQTT_BRIDGE_PID})"
    else
        echo "[WARNING] MQTT enabled but no broker host found — skipping MQTT bridge."
    fi
else
    echo "[INFO] MQTT integration: disabled"
fi

# ==============================================================================
# Phase 5 — Workspace templates
# Copy example instruction files to workspace on first run.
# ==============================================================================
WORKSPACE_DIR="/config/nanobot/workspace"
TEMPLATES_DIR="/app/workspace-templates"
INSTRUCTIONS_DIR="${WORKSPACE_DIR}/instructions"

if [ -d "${TEMPLATES_DIR}" ]; then
    mkdir -p "${INSTRUCTIONS_DIR}"
    for template in "${TEMPLATES_DIR}"/*.md; do
        if [ -f "${template}" ]; then
            basename=$(basename "${template}")
            dest="${INSTRUCTIONS_DIR}/${basename}"
            if [ ! -f "${dest}" ]; then
                cp "${template}" "${dest}"
                echo "[INFO] Installed workspace template: ${basename}"
            fi
        fi
    done
fi

# ==============================================================================
# Phase 6 — WebUI with Nginx for HA Ingress
# Nginx serves static files (with rewritten URLs) on 8099, proxies API to backend on 18781
# ==============================================================================
if [ "${WEBUI_ENABLED}" = "true" ]; then
    echo "[INFO] NanoBot WebUI enabled..."
    
    # Extract static files from webui package at runtime
    echo "[INFO] Extracting WebUI static files..."
    mkdir -p /usr/share/nginx/html
    
    # Simple extraction — find dist/ relative to webui package root
    python3 -c "
import os, shutil, webui
pkg_dir = os.path.dirname(webui.__file__)
src = os.path.join(pkg_dir, 'web', 'dist')
dst = '/usr/share/nginx/html'
if os.path.isdir(src):
    for f in os.listdir(src):
        s = os.path.join(src, f)
        d = os.path.join(dst, f)
        if os.path.isdir(s):
            shutil.copytree(s, d, dirs_exist_ok=True)
        else:
            shutil.copy2(s, d)
    print('Done')
else:
    print(f'Missing: {src}')
"
    
    # Verify files exist
    ls -la /usr/share/nginx/html/ 2>&1 || echo "[ERROR] html directory empty"
    
    if [ ! -f "/usr/share/nginx/html/index.html" ]; then
        echo "[ERROR] index.html not found!"
    fi
    
    # Start WebUI backend on port 18781 (nginx proxies 8099 -> 18781)
    export WEBUI_PORT=18781
    export WEBUI_HOST="127.0.0.1"
    export WEBUI_ONLY=true
    export WEBUI_LOG_LEVEL="${LOG_LEVEL}"
    nanobot webui start --port 18781 --host 127.0.0.1 &
    WEBUI_PID=$!
    echo "[INFO] WebUI backend started (PID: ${WEBUI_PID}, port: 18781)"
    
    # Start nginx on port 8099 (HA ingress)
    echo "[INFO] Starting nginx on port 8099..."
    nginx -t -c /etc/nginx/http.d/nanobot.conf 2>&1 || echo "[WARNING] Nginx config test failed"
    nginx -c /etc/nginx/http.d/nanobot.conf &
    NGINX_PID=$!
    sleep 1
    if ps -p $NGINX_PID > /dev/null 2>&1; then
        echo "[INFO] Nginx started (PID: ${NGINX_PID})"
    else
        echo "[ERROR] Nginx failed to start, falling back to direct mode..."
        # Fallback: run WebUI directly on port 8099
        export WEBUI_PORT=8099
        export WEBUI_HOST="0.0.0.0"
        export WEBUI_ONLY=true
        export WEBUI_LOG_LEVEL="${LOG_LEVEL}"
        nanobot webui start --port 8099 --host 0.0.0.0 &
        WEBUI_PID=$!
        echo "[INFO] WebUI fallback started (PID: ${WEBUI_PID}, port: 8099)"
    fi
    
    sleep 3
else
    echo "[INFO] NanoBot WebUI: disabled"
fi

echo "[INFO] Starting NanoBot gateway on port 18790..."

# Start nanobot gateway (foreground — this is the main process)
exec nanobot gateway

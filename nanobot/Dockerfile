ARG BUILD_FROM
FROM ${BUILD_FROM}

# Install system dependencies
RUN apk add --no-cache \
    python3-dev \
    py3-pip \
    nodejs \
    npm \
    git \
    curl \
    ca-certificates \
    gcc \
    g++ \
    musl-dev \
    libffi-dev \
    openssl-dev \
    cargo \
    jq \
    bash \
    nginx

# Install nanobot-ai from PyPI with Discord + API server support
RUN pip3 install --no-cache-dir --break-system-packages "nanobot-ai[discord]" aiohttp

# Phase 3: websockets for HA event streaming
# Phase 4: paho-mqtt for MQTT bidirectional channel
RUN pip3 install --no-cache-dir --break-system-packages websockets paho-mqtt

# Phase 5: nanobot-webui for web management panel
# Use PyPI package - includes pre-built React frontend
RUN pip3 install --no-cache-dir --break-system-packages nanobot-webui

# Extract web UI static files to nginx directory
RUN mkdir -p /usr/share/nginx/html && \
    python3 -c "import webui.web; import os, shutil; src = os.path.join(os.path.dirname(webui.web.__file__), 'dist'); dst = '/usr/share/nginx/html'; [shutil.copytree(os.path.join(src, f), os.path.join(dst, f)) for f in os.listdir(src) if os.path.isdir(os.path.join(src, f))] if os.path.isdir(src) else None" || true

# Copy nginx config for ingress
COPY nginx.conf /etc/nginx/http.d/nanobot.conf

# Create nginx run directory
RUN mkdir -p /run/nginx

# Create app directory
WORKDIR /app

# Copy config generator and run script
COPY generate_config.py /app/generate_config.py
COPY nanobot_api_server.py /app/nanobot_api_server.py
COPY setup_conversation_agent.py /app/setup_conversation_agent.py
COPY run.sh /
COPY ha_event_listener.py /app/ha_event_listener.py
COPY ha_mqtt_bridge.py /app/ha_mqtt_bridge.py
COPY workspace-templates/ /app/workspace-templates/

RUN chmod a+x /run.sh

# Create nanobot config directory
RUN mkdir -p /root/.nanobot

# Labels
ARG BUILD_ARCH
ARG BUILD_VERSION
LABEL \
    io.hass.version="${BUILD_VERSION}" \
    io.hass.type="addon" \
    io.hass.arch="${BUILD_ARCH}"

CMD [ "/usr/bin/with-contenv", "/run.sh" ]

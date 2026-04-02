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
    bash

# Install nanobot-ai from PyPI with Discord + API server support
RUN pip3 install --no-cache-dir --break-system-packages "nanobot-ai[discord]" aiohttp

# Phase 3: websockets for HA event streaming
# Phase 4: paho-mqtt for MQTT bidirectional channel
RUN pip3 install --no-cache-dir --break-system-packages websockets paho-mqtt

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

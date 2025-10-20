FROM python:3.11-slim

# Prevent Python from buffering stdout/stderr so logs appear in docker logs immediately
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install CA certs for HTTPS and keep image small
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy project into the image
COPY . /app

# Install Python dependencies required by the project
# Adjust or pin versions as needed. These are the packages used by the repo.
RUN pip install --no-cache-dir paho-mqtt aiohttp xmltodict pycryptodome

# Ensure the runner script is executable
RUN chmod +x /app/scripts/mqtt_remote_service.py

# Optional: expose ports if the service needs to be reachable (MQTT broker not provided here)
# EXPOSE 1883

# Default environment variables can be overridden at runtime or via compose/env file
ENV MQTT_BROKER=localhost \
    MQTT_PORT=1883 \
    MQTT_TOPIC=panasonic/remote \
    TV_HOST=127.0.0.1 \
    TV_PORT=55000

# Run the runner script in foreground so systemd is not required inside the container
ENTRYPOINT ["/usr/local/bin/python", "/app/scripts/mqtt_remote_service.py"]

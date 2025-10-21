FROM python:3.11-slim

# Prevent Python from buffering stdout/stderr so logs appear in docker logs immediately
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY panasonic_viera /app/panasonic_viera
ADD mqtt_remote_service.py /app/mqtt_remote_service.py

USER root

RUN pip install --no-cache-dir paho-mqtt aiohttp xmltodict pycryptodome

RUN chmod +x /app/mqtt_remote_service.py

ENV MQTT_BROKER=localhost \
    MQTT_PORT=1883 \
    MQTT_TOPIC=panasonic/remote \
    TV_HOST=127.0.0.1 \
    TV_PORT=55000

ENTRYPOINT ["/usr/local/bin/python", "/app/mqtt_remote_service.py"]

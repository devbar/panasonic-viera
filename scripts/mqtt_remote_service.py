#!/usr/bin/env python3
"""Runner script to start MqttRemoteSubscriber as a long-running service."""
import os
import signal
import time
import logging

from panasonic_viera.remote_control import RemoteControl
from panasonic_viera.mqtt_remote import MqttRemoteSubscriber

_LOGGER = logging.getLogger("panasonic_viera.mqtt_service")


def _env_int(name, default):
    val = os.environ.get(name)
    return int(val) if val is not None and val != "" else default


def main():
    logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))

    broker = os.environ.get("MQTT_BROKER", "localhost")
    broker_port = _env_int("MQTT_PORT", 1883)
    topic = os.environ.get("MQTT_TOPIC", "panasonic/remote")
    qos = _env_int("MQTT_QOS", 0)
    client_id = os.environ.get("MQTT_CLIENT_ID", None)
    username = os.environ.get("MQTT_USERNAME", None)
    password = os.environ.get("MQTT_PASSWORD", None)

    tv_host = os.environ.get("TV_HOST", "127.0.0.1")
    tv_port = _env_int("TV_PORT", 55000)
    app_id = os.environ.get("TV_APP_ID", None)
    enc_key = os.environ.get("TV_ENC_KEY", None)
    listen_host = os.environ.get("LISTEN_HOST", None)
    listen_port = _env_int("LISTEN_PORT", 55000)

    _LOGGER.info("Starting MQTT -> Panasonic Viera bridge (broker=%s:%d topic=%s)", broker, broker_port, topic)

    # Create RemoteControl and MQTT subscriber
    remote = RemoteControl(
        host=tv_host,
        port=tv_port,
        app_id=app_id,
        encryption_key=enc_key,
        listen_host=listen_host,
        listen_port=listen_port,
    )

    subscriber = MqttRemoteSubscriber(
        remote=remote,
        broker=broker,
        port=broker_port,
        topic=topic,
        client_id=client_id,
        username=username,
        password=password,
        qos=qos,
    )

    # Start subscriber
    subscriber.start()

    # Graceful shutdown on signals
    def _shutdown(signum, frame):
        _LOGGER.info("Received signal %s, stopping...", signum)
        try:
            subscriber.stop()
        except Exception as exc:
            _LOGGER.exception("Error while stopping subscriber: %s", exc)
        raise SystemExit(0)

    signal.signal(signal.SIGTERM, _shutdown)
    signal.signal(signal.SIGINT, _shutdown)

    # Keep running until stopped
    try:
        while True:
            time.sleep(1)
    except SystemExit:
        _LOGGER.info("Service exiting")
    except Exception:
        _LOGGER.exception("Unhandled exception in service loop")
    finally:
        try:
            subscriber.stop()
        except Exception:
            pass


if __name__ == "__main__":
    main()
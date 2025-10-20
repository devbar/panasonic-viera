"""MQTT subscriber that calls RemoteControl.send_key on received messages."""
import json
import logging
from typing import Optional

import paho.mqtt.client as mqtt

from .remote_control import RemoteControl
from .keys import Keys

_LOGGER = logging.getLogger(__name__)


class MqttRemoteSubscriber:
    """Subscribe to an MQTT topic and forward received key commands to a RemoteControl.

    Payload handling:
    - If payload is JSON and contains "key" (or "action"), that value is used.
    - Otherwise the raw payload string is used.
    - If the extracted value matches a Keys enum (by name or value) the enum is used,
      otherwise the raw string is passed to RemoteControl.send_key.
    """

    def __init__(
        self,
        remote: RemoteControl,
        broker: str = "localhost",
        port: int = 1883,
        topic: str = "panasonic/remote",
        client_id: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        qos: int = 0,
    ):
        self.remote = remote
        self.broker = broker
        self.port = port
        self.topic = topic
        self.qos = qos

        self._client = mqtt.Client(client_id=client_id) if client_id else mqtt.Client()
        if username is not None:
            self._client.username_pw_set(username, password)

        # Bind callbacks
        self._client.on_connect = self._on_connect
        self._client.on_message = self._on_message
        self._client.on_disconnect = self._on_disconnect

    def start(self, keepalive: int = 60):
        """Connect to broker and start network loop."""
        _LOGGER.debug(
            "Connecting to MQTT broker %s:%d and subscribing to %s",
            self.broker,
            self.port,
            self.topic,
        )
        self._client.connect(self.broker, self.port, keepalive)
        # Use the background thread loop so callbacks run in separate thread
        self._client.loop_start()

    def stop(self):
        """Stop the MQTT client and disconnect."""
        _LOGGER.debug("Stopping MQTT subscriber")
        try:
            self._client.unsubscribe(self.topic)
        except Exception:
            # ignore unsubscribe errors
            pass
        self._client.loop_stop()
        try:
            self._client.disconnect()
        except Exception:
            # ignore disconnect errors
            pass

    # Callback methods
    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            _LOGGER.info(
                "Connected to MQTT broker %s:%d (rc=%s)", self.broker, self.port, rc
            )
            try:
                client.subscribe(self.topic, qos=self.qos)
                _LOGGER.debug(
                    "Subscribed to topic %s (qos=%d)", self.topic, self.qos
                )
            except Exception as exc:
                _LOGGER.error("Failed to subscribe to %s: %s", self.topic, exc)
        else:
            _LOGGER.error("MQTT connection failed with rc=%s", rc)

    def _on_disconnect(self, client, userdata, rc):
        _LOGGER.info("Disconnected from MQTT broker (rc=%s)", rc)

    def _on_message(self, client, userdata, msg):
        payload = None
        try:
            payload_text = msg.payload.decode("utf-8").strip()
        except Exception:
            _LOGGER.exception("Failed to decode MQTT payload")
            return

        # Try JSON first
        try:
            data = json.loads(payload_text)
            if isinstance(data, dict):
                payload = data.get("key") or data.get("action") or payload_text
            else:
                # If JSON is just a value (e.g. "POWER")
                payload = data
        except Exception:
            # Not JSON, use raw text
            payload = payload_text

        if payload is None:
            _LOGGER.debug("Empty payload received on topic %s", msg.topic)
            return

        # Try to map to Keys enum by name or value
        key_to_send = None
        try:
            # If payload matches enum name (case-insensitive)
            if isinstance(payload, str):
                try:
                    key_to_send = Keys[payload.upper()]
                except KeyError:
                    # Try by value
                    try:
                        key_to_send = Keys(payload)
                    except Exception:
                        key_to_send = None
            elif isinstance(payload, (int,)):
                # numeric value -> send as-is (fallback)
                key_to_send = payload
        except Exception:
            _LOGGER.debug("Could not map payload to Keys enum: %s", payload)

        # Dispatch
        try:
            if key_to_send is not None:
                _LOGGER.debug("Sending key via enum: %s", key_to_send)
                self.remote.send_key(key_to_send)
            else:
                _LOGGER.debug("Sending raw key via payload: %s", payload)
                # send_key accepts either Keys or raw string code
                self.remote.send_key(str(payload))
        except Exception:
            _LOGGER.exception("Failed to send key from MQTT payload: %s", payload)
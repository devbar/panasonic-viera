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

    def _get_payload(self, msg):
        try:
            payload_text = msg.payload.decode("utf-8").strip()
        except Exception:
            _LOGGER.exception("Failed to decode MQTT payload")
            return None
        
        try:
            data = json.loads(payload_text)
            if isinstance(data, dict):
                return data.get("key") or data.get("action") or payload_text
            else:                
                return data
        except Exception:            
            return payload_text
        
    def _get_key_to_send(self,payload):
        try:            
            if isinstance(payload, str):
                try:
                    return Keys[payload.upper()]
                except KeyError:
                    try:
                        return Keys(payload)
                    except Exception:
                        return None
            elif isinstance(payload, (int,)):
                return payload
        except Exception:
            _LOGGER.debug("Could not map payload to Keys enum: %s", payload)
            return None

    def _on_message(self, client, userdata, msg):
        payload = self._get_payload(msg)

        if payload is None:
            _LOGGER.debug("Empty payload received on topic %s", msg.topic)
            return
        
        if payload == "APPS":
            apps = self.remote.get_apps()
            client.publish(msg.topic + "/apps", json.dumps(apps))
            _LOGGER.info("Available apps: %s", apps)
            return
        
        if payload == "DEVICE_INFO":
            info = self.remote.get_device_info()
            client.publish(msg.topic + "/device_info", json.dumps(info))
            _LOGGER.info("TV Info: %s", info)
            return
        
        if payload == "VECTOR_INFO":
            info = self.remote.get_vector_info()
            client.publish(msg.topic + "/vector_info", json.dumps(info))
            _LOGGER.info("Vector Info: %s", info)
            return
                
        key_to_send = self._get_key_to_send(payload)
        
        try:
            if key_to_send is None:
                _LOGGER.debug("Sending raw key via payload: %s", payload)
                self.remote.send_key(str(payload))
            else:
                _LOGGER.debug("Sending key via enum: %s", key_to_send)
                self.remote.send_key(key_to_send)
        except Exception:
            _LOGGER.exception("Failed to send key from MQTT payload: %s", payload)
            self.remote.renew_session()
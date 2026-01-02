import paho.mqtt.client as mqtt
import logging
import json

from .remote_control import RemoteControl
from .keys import Keys

_LOGGER = logging.getLogger(__name__)

class MessageHandler:
    
    def __init__(self, client: mqtt.Client, remote: RemoteControl):
        self.client = client
        self.remote = remote

    def _get_payload(self, msg):
        try:
            payload = msg.payload.decode("utf-8").strip()
        except Exception as exp:
            _LOGGER.exception("Failed to decode MQTT payload", exp)
            return None
        
        try:
            data = json.loads(payload)
            if isinstance(data, dict):
                return (
                    data.get("key") or 
                    data.get("action") or 
                    payload
                )
            else:
                return data
        except Exception:
            _LOGGER.warning("Failed to parse MQTT payload as JSON, using raw payload")
            return payload
        
    def _get_apps(self, msg: any, payload: any):
        try:
            apps = self.remote.get_apps()
            self.client.publish(msg.topic + "/apps", json.dumps(apps))
        except Exception as exp:
            _LOGGER.exception(f"Failed to send key from MQTT payload: {payload}", exp)
            self.remote.renew_session()
            return
        _LOGGER.info(f"Available apps: {apps}")
        
    def _get_device_info(self, msg: any, payload: any):
        try:
            info = self.remote.get_device_info()
            self.client.publish(msg.topic + "/device_info", json.dumps(info))
        except Exception as exp:
            _LOGGER.exception(f"Failed to send key from MQTT payload: {payload}", exp)
            self.remote.renew_session()
            return
        _LOGGER.info(f"TV Info: {info}")        
    
    def _get_vector_info(self, msg: any, payload: any):
        try:
            info = self.remote.get_vector_info()
            self.client.publish(msg.topic + "/vector_info", json.dumps(info))
        except Exception as exp:
            _LOGGER.exception(f"Failed to send key from MQTT payload: {payload}", exp)
            self.remote.renew_session()
            return
        _LOGGER.info(f"Vector Info: {info}")
    
    def _turn_on(self):
        try:
            info = self.remote.get_apps()
            if len(info) == 0:
              self.remote.turn_on() 
        except Exception as exp:
            _LOGGER.exception(f"Failed to turn on TV from MQTT payload", exp)
            self.remote.renew_session()
    
    def _turn_off(self):
        try:
            info = self.remote.get_apps()
            if len(info) != 0:
                self.remote.turn_off() 
        except Exception as exp:
            _LOGGER.exception(f"Failed to turn off TV from MQTT payload", exp)
            self.remote.renew_session()
            
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
    
    def handle(self, msg):
        payload = self._get_payload(msg)

        if payload is None or len(payload) == 0:
            _LOGGER.debug("Empty payload received on topic %s", msg.topic)
            return
        
        if payload == "APPS":
            self._get_apps(msg, payload)
            return
        
        if payload == "DEVICE_INFO":
            self._get_device_info(msg, payload)
            return
        
        if payload == "VECTOR_INFO":
            self._get_vector_info(msg, payload)
            return
        
        if payload == "ON":
            self._turn_on()
            return
        
        if payload == "OFF":
            self._turn_off()
            return            
                
        key_to_send = self._get_key_to_send(payload)
        
        try:
            if key_to_send is None:
                _LOGGER.debug("Sending raw key via payload: %s", payload)
                self.remote.send_key(str(payload))
            else:
                _LOGGER.debug("Sending key via enum: %s", key_to_send)
                self.remote.send_key(key_to_send)
        except Exception as exp:
            _LOGGER.exception(f"Failed to send key from MQTT payload: {payload}", exp)
            self.remote.renew_session()
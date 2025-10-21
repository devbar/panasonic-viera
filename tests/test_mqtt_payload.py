import unittest
from unittest.mock import MagicMock
import json
from panasonic_viera.mqtt_remote import MqttRemoteSubscriber
from panasonic_viera.remote_control import RemoteControl

class TestMqttPayloadHandling(unittest.TestCase):
    def setUp(self):
        """Create a subscriber with mocked remote control"""
        self.remote = MagicMock(spec=RemoteControl)
        self.subscriber = MqttRemoteSubscriber(self.remote)

    def _create_msg(self, payload: bytes):
        """Helper to create mock MQTT message with payload"""
        msg = MagicMock()
        msg.payload = payload
        return msg

    def test_valid_json_with_key(self):
        msg = self._create_msg(b'{"key": "VOL_UP"}')
        result = self.subscriber._get_payload(msg)
        self.assertEqual(result, "VOL_UP")

    def test_valid_json_with_action(self):
        msg = self._create_msg(b'{"action": "POWER_OFF"}')
        result = self.subscriber._get_payload(msg)
        self.assertEqual(result, "POWER_OFF")

    def test_valid_json_without_key_or_action(self):
        msg = self._create_msg(b'{"other": "value"}')
        result = self.subscriber._get_payload(msg)
        self.assertEqual(result, json.dumps({"other": "value"}))

    def test_non_json_payload(self):
        msg = self._create_msg(b"RAW_KEY_CODE")
        result = self.subscriber._get_payload(msg)
        self.assertEqual(result, "RAW_KEY_CODE")

    def test_invalid_json_payload(self):
        msg = self._create_msg(b"{invalid: json}")
        result = self.subscriber._get_payload(msg)
        self.assertEqual(result, "{invalid: json}")

    def test_empty_payload(self):
        msg = self._create_msg(b"")
        result = self.subscriber._get_payload(msg)
        self.assertEqual(result, "")

    def test_non_dict_json(self):
        msg = self._create_msg(b'["array", "payload"]')
        result = self.subscriber._get_payload(msg)
        self.assertEqual(result, ["array", "payload"])

    def test_binary_payload_decoding_error(self):
        msg = self._create_msg(b"\x80abc")  # Invalid UTF-8
        result = self.subscriber._get_payload(msg)
        self.assertIsNone(result)

if __name__ == "__main__":
    unittest.main()
"""Unit tests for MessageHandler class."""
import unittest
from unittest.mock import MagicMock, patch, call
import json

from panasonic_viera.message_handler import MessageHandler
from panasonic_viera.keys import Keys


class TestMessageHandler(unittest.TestCase):
    """Test cases for MessageHandler."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_client = MagicMock()
        self.mock_remote = MagicMock()
        self.handler = MessageHandler(self.mock_client, self.mock_remote)

    def test_init(self):
        """Test MessageHandler initialization."""
        self.assertEqual(self.handler.client, self.mock_client)
        self.assertEqual(self.handler.remote, self.mock_remote)

    def test_get_payload_simple_string(self):
        """Test _get_payload with simple string payload."""
        mock_msg = MagicMock()
        mock_msg.payload.decode.return_value = "NRC_POWER-ONOFF"
        
        result = self.handler._get_payload(mock_msg)
        
        self.assertEqual(result, "NRC_POWER-ONOFF")

    def test_get_payload_json_with_key(self):
        """Test _get_payload with JSON containing 'key' field."""
        mock_msg = MagicMock()
        mock_msg.payload.decode.return_value = '{"key": "NRC_POWER-ONOFF"}'
        
        result = self.handler._get_payload(mock_msg)
        
        self.assertEqual(result, "NRC_POWER-ONOFF")

    def test_get_payload_json_with_action(self):
        """Test _get_payload with JSON containing 'action' field."""
        mock_msg = MagicMock()
        mock_msg.payload.decode.return_value = '{"action": "NRC_MUTE"}'
        
        result = self.handler._get_payload(mock_msg)
        
        self.assertEqual(result, "NRC_MUTE")

    def test_get_payload_json_with_both_key_and_action(self):
        """Test _get_payload with JSON containing both 'key' and 'action' - key takes precedence."""
        mock_msg = MagicMock()
        mock_msg.payload.decode.return_value = '{"key": "NRC_POWER-ONOFF", "action": "NRC_MUTE"}'
        
        result = self.handler._get_payload(mock_msg)
        
        self.assertEqual(result, "NRC_POWER-ONOFF")

    def test_get_payload_json_without_key_or_action(self):
        """Test _get_payload with JSON dict without 'key' or 'action' returns raw payload."""
        mock_msg = MagicMock()
        mock_msg.payload.decode.return_value = '{"other": "value"}'
        
        result = self.handler._get_payload(mock_msg)
        
        self.assertEqual(result, '{"other": "value"}')

    def test_get_payload_json_non_dict(self):
        """Test _get_payload with JSON non-dict (e.g., array or string)."""
        mock_msg = MagicMock()
        mock_msg.payload.decode.return_value = '["item1", "item2"]'
        
        result = self.handler._get_payload(mock_msg)
        
        self.assertEqual(result, ["item1", "item2"])

    def test_get_payload_invalid_json(self):
        """Test _get_payload with invalid JSON falls back to raw payload."""
        mock_msg = MagicMock()
        mock_msg.payload.decode.return_value = "not-valid-json"
        
        result = self.handler._get_payload(mock_msg)
        
        self.assertEqual(result, "not-valid-json")

    def test_get_payload_decode_error(self):
        """Test _get_payload with decode error returns None."""
        mock_msg = MagicMock()
        mock_msg.payload.decode.side_effect = UnicodeDecodeError('utf-8', b'', 0, 1, 'invalid')
        
        result = self.handler._get_payload(mock_msg)
        
        self.assertIsNone(result)

    def test_get_payload_empty_string(self):
        """Test _get_payload with empty string after strip."""
        mock_msg = MagicMock()
        mock_msg.payload.decode.return_value = "   "
        
        result = self.handler._get_payload(mock_msg)
        
        self.assertEqual(result, "")

    def test_get_apps_success(self):
        """Test _get_apps successfully retrieves and publishes apps."""
        mock_msg = MagicMock()
        mock_msg.topic = "panasonic/remote"
        apps = {"Netflix": "0010000200000001", "YouTube": "0070000200180001"}
        self.mock_remote.get_apps.return_value = apps
        
        self.handler._get_apps(mock_msg, "APPS")
        
        self.mock_remote.get_apps.assert_called_once()
        self.mock_client.publish.assert_called_once_with(
            "panasonic/remote/apps",
            json.dumps(apps)
        )

    def test_get_apps_exception_renews_session(self):
        """Test _get_apps renews session on exception."""
        mock_msg = MagicMock()
        mock_msg.topic = "panasonic/remote"
        self.mock_remote.get_apps.side_effect = Exception("Connection error")
        
        self.handler._get_apps(mock_msg, "APPS")
        
        self.mock_remote.renew_session.assert_called_once()

    def test_get_device_info_success(self):
        """Test _get_device_info successfully retrieves and publishes device info."""
        mock_msg = MagicMock()
        mock_msg.topic = "panasonic/remote"
        device_info = {"modelName": "TX-55HZ980", "friendlyName": "Living Room TV"}
        self.mock_remote.get_device_info.return_value = device_info
        
        self.handler._get_device_info(mock_msg, "DEVICE_INFO")
        
        self.mock_remote.get_device_info.assert_called_once()
        self.mock_client.publish.assert_called_once_with(
            "panasonic/remote/device_info",
            json.dumps(device_info)
        )

    def test_get_device_info_exception_renews_session(self):
        """Test _get_device_info renews session on exception."""
        mock_msg = MagicMock()
        mock_msg.topic = "panasonic/remote"
        self.mock_remote.get_device_info.side_effect = Exception("Connection error")
        
        self.handler._get_device_info(mock_msg, "DEVICE_INFO")
        
        self.mock_remote.renew_session.assert_called_once()

    def test_get_vector_info_success(self):
        """Test _get_vector_info successfully retrieves and publishes vector info."""
        mock_msg = MagicMock()
        mock_msg.topic = "panasonic/remote"
        vector_info = "<VectorInfo>data</VectorInfo>"
        self.mock_remote.get_vector_info.return_value = vector_info
        
        self.handler._get_vector_info(mock_msg, "VECTOR_INFO")
        
        self.mock_remote.get_vector_info.assert_called_once()
        self.mock_client.publish.assert_called_once_with(
            "panasonic/remote/vector_info",
            json.dumps(vector_info)
        )

    def test_get_vector_info_exception_renews_session(self):
        """Test _get_vector_info renews session on exception."""
        mock_msg = MagicMock()
        mock_msg.topic = "panasonic/remote"
        self.mock_remote.get_vector_info.side_effect = Exception("Connection error")
        
        self.handler._get_vector_info(mock_msg, "VECTOR_INFO")
        
        self.mock_remote.renew_session.assert_called_once()

    def test_turn_on_when_tv_is_off(self):
        """Test _turn_on turns on TV when it's off (no apps available)."""
        self.mock_remote.get_apps.return_value = {}
        
        self.handler._turn_on()
        
        self.mock_remote.get_apps.assert_called_once()
        self.mock_remote.turn_on.assert_called_once()

    def test_turn_on_when_tv_is_on(self):
        """Test _turn_on does not turn on TV when it's already on (apps available)."""
        self.mock_remote.get_apps.return_value = {"Netflix": "0010000200000001"}
        
        self.handler._turn_on()
        
        self.mock_remote.get_apps.assert_called_once()
        self.mock_remote.turn_on.assert_not_called()

    def test_turn_on_exception_renews_session(self):
        """Test _turn_on renews session on exception."""
        self.mock_remote.get_apps.side_effect = Exception("Connection error")
        
        self.handler._turn_on()
        
        self.mock_remote.renew_session.assert_called_once()

    def test_turn_off_when_tv_is_off(self):
        """Test _turn_off does not turn off TV when it's already off."""
        self.mock_remote.get_apps.return_value = {}
        
        self.handler._turn_off()
        
        self.mock_remote.get_apps.assert_called_once()
        self.mock_remote.turn_off.assert_not_called()

    def test_turn_off_when_tv_is_on(self):
        """Test _turn_off turns off TV when it's on (apps available)."""
        self.mock_remote.get_apps.return_value = {"Netflix": "0010000200000001"}
        
        self.handler._turn_off()
        
        self.mock_remote.get_apps.assert_called_once()
        self.mock_remote.turn_off.assert_called_once()

    def test_turn_off_exception_renews_session(self):
        """Test _turn_off renews session on exception."""
        self.mock_remote.get_apps.side_effect = Exception("Connection error")
        
        self.handler._turn_off()
        
        self.mock_remote.renew_session.assert_called_once()

    def test_handle_empty_payload(self):
        """Test handle with empty payload does nothing."""
        mock_msg = MagicMock()
        mock_msg.topic = "panasonic/remote"
        mock_msg.payload.decode.return_value = ""
        
        self.handler.handle(mock_msg)
        
        self.mock_remote.send_key.assert_not_called()

    def test_handle_none_payload(self):
        """Test handle with None payload does nothing."""
        mock_msg = MagicMock()
        mock_msg.topic = "panasonic/remote"
        mock_msg.payload.decode.side_effect = Exception("Decode error")
        
        self.handler.handle(mock_msg)
        
        self.mock_remote.send_key.assert_not_called()

    def test_handle_apps_command(self):
        """Test handle with APPS command."""
        mock_msg = MagicMock()
        mock_msg.topic = "panasonic/remote"
        mock_msg.payload.decode.return_value = "APPS"
        self.mock_remote.get_apps.return_value = {}
        
        self.handler.handle(mock_msg)
        
        self.mock_remote.get_apps.assert_called_once()
        self.mock_remote.send_key.assert_not_called()

    def test_handle_device_info_command(self):
        """Test handle with DEVICE_INFO command."""
        mock_msg = MagicMock()
        mock_msg.topic = "panasonic/remote"
        mock_msg.payload.decode.return_value = "DEVICE_INFO"
        self.mock_remote.get_device_info.return_value = {}
        
        self.handler.handle(mock_msg)
        
        self.mock_remote.get_device_info.assert_called_once()
        self.mock_remote.send_key.assert_not_called()

    def test_handle_vector_info_command(self):
        """Test handle with VECTOR_INFO command."""
        mock_msg = MagicMock()
        mock_msg.topic = "panasonic/remote"
        mock_msg.payload.decode.return_value = "VECTOR_INFO"
        self.mock_remote.get_vector_info.return_value = ""
        
        self.handler.handle(mock_msg)
        
        self.mock_remote.get_vector_info.assert_called_once()
        self.mock_remote.send_key.assert_not_called()

    def test_handle_on_command(self):
        """Test handle with ON command."""
        mock_msg = MagicMock()
        mock_msg.topic = "panasonic/remote"
        mock_msg.payload.decode.return_value = "ON"
        self.mock_remote.get_apps.return_value = {}
        
        self.handler.handle(mock_msg)
        
        self.mock_remote.turn_on.assert_called_once()
        self.mock_remote.send_key.assert_not_called()

    def test_handle_off_command(self):
        """Test handle with OFF command."""
        mock_msg = MagicMock()
        mock_msg.topic = "panasonic/remote"
        mock_msg.payload.decode.return_value = "OFF"
        self.mock_remote.get_apps.return_value = {"Netflix": "0010000200000001"}
        
        self.handler.handle(mock_msg)
        
        self.mock_remote.turn_off.assert_called_once()
        self.mock_remote.send_key.assert_not_called()

    @patch.object(MessageHandler, '_get_key_to_send')
    def test_handle_key_via_enum(self, mock_get_key):
        """Test handle sends key via enum when _get_key_to_send returns a key."""
        mock_msg = MagicMock()
        mock_msg.topic = "panasonic/remote"
        mock_msg.payload.decode.return_value = "NRC_POWER-ONOFF"
        mock_get_key.return_value = Keys.POWER
        
        self.handler.handle(mock_msg)
        
        mock_get_key.assert_called_once_with("NRC_POWER-ONOFF")
        self.mock_remote.send_key.assert_called_once_with(Keys.POWER)

    @patch.object(MessageHandler, '_get_key_to_send')
    def test_handle_raw_key_when_enum_not_found(self, mock_get_key):
        """Test handle sends raw key when _get_key_to_send returns None."""
        mock_msg = MagicMock()
        mock_msg.topic = "panasonic/remote"
        mock_msg.payload.decode.return_value = "CUSTOM_KEY"
        mock_get_key.return_value = None
        
        self.handler.handle(mock_msg)
        
        mock_get_key.assert_called_once_with("CUSTOM_KEY")
        self.mock_remote.send_key.assert_called_once_with("CUSTOM_KEY")

    @patch.object(MessageHandler, '_get_key_to_send')
    def test_handle_send_key_exception_renews_session(self, mock_get_key):
        """Test handle renews session when send_key raises exception."""
        mock_msg = MagicMock()
        mock_msg.topic = "panasonic/remote"
        mock_msg.payload.decode.return_value = "NRC_POWER-ONOFF"
        mock_get_key.return_value = Keys.POWER
        self.mock_remote.send_key.side_effect = Exception("Connection error")
        
        self.handler.handle(mock_msg)
        
        self.mock_remote.send_key.assert_called_once_with(Keys.POWER)
        self.mock_remote.renew_session.assert_called_once()

    def test_handle_json_payload_with_key(self):
        """Test handle with JSON payload containing key field."""
        mock_msg = MagicMock()
        mock_msg.topic = "panasonic/remote"
        mock_msg.payload.decode.return_value = '{"key": "NRC_MUTE"}'
        
        with patch.object(self.handler, '_get_key_to_send', return_value=None):
            self.handler.handle(mock_msg)
        
        self.mock_remote.send_key.assert_called_once_with("NRC_MUTE")

    def test_handle_json_payload_with_action(self):
        """Test handle with JSON payload containing action field."""
        mock_msg = MagicMock()
        mock_msg.topic = "panasonic/remote"
        mock_msg.payload.decode.return_value = '{"action": "NRC_VOLUP"}'
        
        with patch.object(self.handler, '_get_key_to_send', return_value=None):
            self.handler.handle(mock_msg)
        
        self.mock_remote.send_key.assert_called_once_with("NRC_VOLUP")

    def test_multiple_commands_in_sequence(self):
        """Test handling multiple commands in sequence."""
        mock_msg1 = MagicMock()
        mock_msg1.topic = "panasonic/remote"
        mock_msg1.payload.decode.return_value = "ON"
        
        mock_msg2 = MagicMock()
        mock_msg2.topic = "panasonic/remote"
        mock_msg2.payload.decode.return_value = "APPS"
        
        mock_msg3 = MagicMock()
        mock_msg3.topic = "panasonic/remote"
        mock_msg3.payload.decode.return_value = "OFF"
        
        self.mock_remote.get_apps.side_effect = [{}, {"Netflix": "001"}, {"Netflix": "001"}]
        
        self.handler.handle(mock_msg1)
        self.handler.handle(mock_msg2)
        self.handler.handle(mock_msg3)
        
        self.mock_remote.turn_on.assert_called_once()
        self.assertEqual(self.mock_remote.get_apps.call_count, 3)
        self.mock_remote.turn_off.assert_called_once()


if __name__ == '__main__':
    unittest.main()

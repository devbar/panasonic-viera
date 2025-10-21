import unittest
from unittest.mock import MagicMock

from panasonic_viera.mqtt_remote import MqttRemoteSubscriber
from panasonic_viera.keys import Keys
from panasonic_viera.remote_control import RemoteControl


class DummyRemote(RemoteControl):
    def __init__(self):
        # Do not call super to avoid network calls
        pass


class TestGetKeyToSend(unittest.TestCase):
    def setUp(self):
        self.remote = MagicMock(spec=DummyRemote)
        self.subscriber = MqttRemoteSubscriber(self.remote)

    def test_enum_by_name(self):
        # e.g., 'volume_up' -> Keys.VOLUME_UP
        key = self.subscriber._get_key_to_send('volume_up')
        self.assertEqual(key, Keys.VOLUME_UP)

    def test_enum_by_name_case_insensitive(self):
        key = self.subscriber._get_key_to_send('VoLuMe_Up')
        self.assertEqual(key, Keys.VOLUME_UP)

    def test_enum_by_value(self):
        # Use the value of an enum member
        val = Keys.VOLUME_DOWN.value
        key = self.subscriber._get_key_to_send(val)
        self.assertEqual(key, Keys.VOLUME_DOWN)

    def test_int_passthrough(self):
        key = self.subscriber._get_key_to_send(123)
        self.assertEqual(key, 123)

    def test_unknown_string_returns_none(self):
        key = self.subscriber._get_key_to_send('NON_EXISTENT_KEY')
        self.assertIsNone(key)

    def test_exception_path_returns_none(self):
        # Force an exception path by passing an object that raises on isinstance check
        class Bad:
            def __instancecheck__(self, other):
                raise RuntimeError("bad")

        # _get_key_to_send wraps in try/except and should return None
        key = self.subscriber._get_key_to_send(Bad())
        self.assertIsNone(key)


if __name__ == '__main__':
    unittest.main()

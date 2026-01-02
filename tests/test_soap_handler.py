"""Unit tests for SoapHandler class."""
import unittest
from unittest.mock import MagicMock, patch, Mock
import base64
from xml.etree import ElementTree

from panasonic_viera.soap_handler import SoapHandler
from panasonic_viera.exceptions import SOAPError
from panasonic_viera.constants import URN_REMOTE_CONTROL, URN_RENDERING_CONTROL


class TestSoapHandler(unittest.TestCase):
    """Test cases for SoapHandler."""

    def setUp(self):
        """Set up test fixtures."""
        self.host = "192.168.1.100"
        self.port = 55000
        self.handler = SoapHandler(self.host, self.port)
        self.handler_with_proxy = SoapHandler(self.host, self.port, proxy="http://proxy:8080")

    def test_init_without_proxy(self):
        """Test initialization without proxy."""
        handler = SoapHandler(self.host, self.port)
        self.assertEqual(handler._host, self.host)
        self.assertEqual(handler._port, self.port)
        self.assertIsNone(handler._proxy)

    def test_init_with_proxy(self):
        """Test initialization with proxy."""
        proxy = "http://proxy:8080"
        handler = SoapHandler(self.host, self.port, proxy=proxy)
        self.assertEqual(handler._host, self.host)
        self.assertEqual(handler._port, self.port)
        self.assertEqual(handler._proxy, proxy)

    @patch('panasonic_viera.soap_handler.build_opener')
    def test_get_opener_without_proxy(self, mock_build_opener):
        """Test _get_opener without proxy."""
        mock_opener = MagicMock()
        mock_build_opener.return_value = mock_opener
        
        opener = self.handler._get_opener()
        
        mock_build_opener.assert_called_once()
        self.assertEqual(opener, mock_opener)

    @patch('panasonic_viera.soap_handler.build_opener')
    def test_get_opener_with_proxy(self, mock_build_opener):
        """Test _get_opener with proxy."""
        mock_opener = MagicMock()
        mock_build_opener.return_value = mock_opener
        
        opener = self.handler_with_proxy._get_opener()
        
        mock_build_opener.assert_called_once()
        self.assertEqual(opener, mock_opener)

    @patch('panasonic_viera.soap_handler.SoapHandler._get_opener')
    def test_urlopen(self, mock_get_opener):
        """Test _urlopen method."""
        mock_opener = MagicMock()
        mock_response = MagicMock()
        mock_opener.open.return_value = mock_response
        mock_get_opener.return_value = mock_opener
        
        mock_request = MagicMock()
        result = self.handler._urlopen(mock_request, timeout=10)
        
        mock_opener.open.assert_called_once_with(mock_request, timeout=10)
        self.assertEqual(result, mock_response)

    def test_is_encrypted_request_true(self):
        """Test _is_encrypted_request returns True for encrypted requests."""
        encryption_context = {
            'app_id': 'test_app',
            'session_id': 'test_session',
            'session_seq_num': 1,
        }
        
        result = self.handler._is_encrypted_request(
            encryption_context,
            URN_REMOTE_CONTROL,
            "X_SendKey"
        )
        
        self.assertTrue(result)

    def test_is_encrypted_request_false_no_context(self):
        """Test _is_encrypted_request returns False when no encryption context."""
        result = self.handler._is_encrypted_request(
            None,
            URN_REMOTE_CONTROL,
            "X_SendKey"
        )
        
        self.assertFalse(result)

    def test_is_encrypted_request_false_excluded_action(self):
        """Test _is_encrypted_request returns False for excluded actions."""
        encryption_context = {'app_id': 'test_app'}
        
        for action in ["X_GetEncryptSessionId", "X_DisplayPinCode", "X_RequestAuth"]:
            result = self.handler._is_encrypted_request(
                encryption_context,
                URN_REMOTE_CONTROL,
                action
            )
            self.assertFalse(result, f"Action {action} should not be encrypted")

    def test_is_encrypted_request_false_different_urn(self):
        """Test _is_encrypted_request returns False for non-remote-control URN."""
        encryption_context = {'app_id': 'test_app'}
        
        result = self.handler._is_encrypted_request(
            encryption_context,
            URN_RENDERING_CONTROL,
            "GetVolume"
        )
        
        self.assertFalse(result)

    @patch('panasonic_viera.soap_handler.SoapHandler.encrypt_payload')
    def test_encrypt_request(self, mock_encrypt):
        """Test _encrypt_request method."""
        mock_encrypt.return_value = "encrypted_data"
        
        encryption_context = {
            'app_id': 'test_app_id',
            'session_id': 'test_session_id',
            'session_seq_num': 5,
            'session_key': bytearray(b'test_key'),
            'session_iv': bytearray(b'test_iv'),
            'session_hmac_key': bytearray(b'test_hmac'),
        }
        
        result = self.handler._encrypt_request(
            encryption_context,
            URN_REMOTE_CONTROL,
            "X_SendKey",
            "<X_KeyEvent>NRC_POWER-ONOFF</X_KeyEvent>"
        )
        
        self.assertEqual(result['action'], "X_EncryptedCommand")
        self.assertIn("test_app_id", result['params'])
        self.assertIn("encrypted_data", result['params'])
        self.assertEqual(result['body_elem'], "u")
        mock_encrypt.assert_called_once()

    @patch('panasonic_viera.soap_handler.Request')
    @patch('panasonic_viera.soap_handler.SoapHandler._urlopen')
    def test_send_request_unencrypted(self, mock_urlopen, mock_request_class):
        """Test send_request for unencrypted request."""
        mock_response = MagicMock()
        mock_response.read.return_value = b'<response>test</response>'
        mock_urlopen.return_value = mock_response
        
        mock_request = MagicMock()
        mock_request_class.return_value = mock_request
        
        result = self.handler.send_request(
            "nrc/control_0",
            URN_RENDERING_CONTROL,
            "GetVolume",
            "<InstanceID>0</InstanceID>",
            body_elem="m"
        )
        
        self.assertEqual(result, b'<response>test</response>')
        mock_request_class.assert_called_once()
        mock_urlopen.assert_called_once_with(mock_request, timeout=5)

    @patch('panasonic_viera.soap_handler.Request')
    @patch('panasonic_viera.soap_handler.SoapHandler._urlopen')
    @patch('panasonic_viera.soap_handler.SoapHandler.encrypt_payload')
    @patch('panasonic_viera.soap_handler.SoapHandler.decrypt_payload')
    def test_send_request_encrypted(self, mock_decrypt, mock_encrypt, mock_urlopen, mock_request_class):
        """Test send_request for encrypted request."""
        mock_encrypt.return_value = "encrypted_command"
        mock_decrypt.return_value = "<decrypted>response</decrypted>"
        
        mock_response = MagicMock()
        mock_response.read.return_value = b'<s:Envelope><X_EncResult>encrypted_result</X_EncResult></s:Envelope>'
        mock_urlopen.return_value = mock_response
        
        mock_request = MagicMock()
        mock_request_class.return_value = mock_request
        
        encryption_context = {
            'app_id': 'test_app',
            'session_id': 'session123',
            'session_seq_num': 1,
            'session_key': bytearray(b'0123456789abcdef'),
            'session_iv': bytearray(b'fedcba9876543210'),
            'session_hmac_key': bytearray(b'hmac_key_32_bytes_long_value'),
        }
        
        result = self.handler.send_request(
            "nrc/control_0",
            URN_REMOTE_CONTROL,
            "X_SendKey",
            "<X_KeyEvent>NRC_POWER-ONOFF</X_KeyEvent>",
            body_elem="u",
            encryption_context=encryption_context
        )
        
        self.assertEqual(result, "<decrypted>response</decrypted>")
        self.assertEqual(encryption_context['session_seq_num'], 2)
        mock_encrypt.assert_called_once()
        mock_decrypt.assert_called_once()

    @patch('panasonic_viera.soap_handler.Request')
    @patch('panasonic_viera.soap_handler.SoapHandler._urlopen')
    def test_send_request_http_error_rollback(self, mock_urlopen, mock_request_class):
        """Test send_request rolls back sequence number on HTTP error."""
        from urllib.request import HTTPError
        
        mock_urlopen.side_effect = HTTPError(None, 500, "Server Error", {}, None)
        
        encryption_context = {
            'app_id': 'test_app',
            'session_id': 'session123',
            'session_seq_num': 5,
            'session_key': bytearray(b'0123456789abcdef'),
            'session_iv': bytearray(b'fedcba9876543210'),
            'session_hmac_key': bytearray(b'hmac_key_32_bytes_long_value'),
        }
        
        with self.assertRaises(HTTPError):
            self.handler.send_request(
                "nrc/control_0",
                URN_REMOTE_CONTROL,
                "X_SendKey",
                "<X_KeyEvent>NRC_POWER-ONOFF</X_KeyEvent>",
                encryption_context=encryption_context
            )
        
        # Sequence number should be rolled back to original value
        self.assertEqual(encryption_context['session_seq_num'], 5)

    def test_encrypt_payload(self):
        """Test encrypt_payload static method."""
        data = "<X_ApplicationId>test_app</X_ApplicationId>"
        key = bytearray(b'0123456789abcdef')
        init_vector = bytearray(b'fedcba9876543210')
        hmac_key = bytearray(b'hmac_key_32_bytes_long_value')
        
        result = SoapHandler.encrypt_payload(data, key, init_vector, hmac_key)
        
        # Result should be base64 encoded
        self.assertIsInstance(result, str)
        # Should be valid base64
        decoded = base64.b64decode(result)
        self.assertIsInstance(decoded, bytes)
        # Should be longer than original due to padding and HMAC
        self.assertGreater(len(decoded), len(data))

    def test_decrypt_payload(self):
        """Test decrypt_payload static method."""
        # First encrypt some data
        data = "<X_SessionId>test_session</X_SessionId>"
        key = bytearray(b'0123456789abcdef')
        init_vector = bytearray(b'fedcba9876543210')
        hmac_key = bytearray(b'hmac_key_32_bytes_long_value')
        
        encrypted = SoapHandler.encrypt_payload(data, key, init_vector, hmac_key)
        
        # Now decrypt it
        decrypted = SoapHandler.decrypt_payload(encrypted, key, init_vector, hmac_key)
        
        self.assertEqual(decrypted, data)

    def test_handle_soap_error_with_error_description(self):
        """Test handle_soap_error with error description."""
        from urllib.request import HTTPError
        
        error_xml = b'<?xml version="1.0"?><s:Envelope><s:Body><s:Fault><detail><UPnPError><errorCode>401</errorCode><errorDescription>Invalid Action</errorDescription></UPnPError></detail></s:Fault></s:Body></s:Envelope>'
        
        mock_fp = MagicMock()
        mock_fp.read.return_value = error_xml
        
        http_error = HTTPError(None, 500, "Server Error", {}, mock_fp)
        
        with self.assertRaises(SOAPError) as context:
            SoapHandler.handle_soap_error(http_error)
        
        self.assertEqual(str(context.exception), "Invalid Action")

    def test_handle_soap_error_with_invalid_pin(self):
        """Test handle_soap_error with invalid PIN code."""
        from urllib.request import HTTPError
        
        error_xml = b'<?xml version="1.0"?><s:Envelope><s:Body><s:Fault><detail><UPnPError><errorCode>600</errorCode></UPnPError></detail></s:Fault></s:Body></s:Envelope>'
        
        mock_fp = MagicMock()
        mock_fp.read.return_value = error_xml
        
        http_error = HTTPError(None, 500, "Server Error", {}, mock_fp)
        
        with self.assertRaises(SOAPError) as context:
            SoapHandler.handle_soap_error(http_error)
        
        self.assertEqual(str(context.exception), "Invalid PIN Code!")

    def test_handle_soap_error_non_500_error(self):
        """Test handle_soap_error re-raises non-500 errors."""
        from urllib.request import HTTPError
        
        http_error = HTTPError(None, 404, "Not Found", {}, None)
        
        with self.assertRaises(HTTPError) as context:
            SoapHandler.handle_soap_error(http_error)
        
        self.assertEqual(context.exception.code, 404)

    def test_encrypt_decrypt_roundtrip(self):
        """Test that encrypt and decrypt are inverse operations."""
        original_data = "<X_KeyEvent>NRC_POWER-ONOFF</X_KeyEvent>"
        key = bytearray(b'0123456789abcdef')
        init_vector = bytearray(b'fedcba9876543210')
        hmac_key = bytearray(b'hmac_key_32_bytes_long_value')
        
        encrypted = SoapHandler.encrypt_payload(original_data, key, init_vector, hmac_key)
        decrypted = SoapHandler.decrypt_payload(encrypted, key, init_vector, hmac_key)
        
        self.assertEqual(decrypted, original_data)

    @patch('panasonic_viera.soap_handler.Request')
    @patch('panasonic_viera.soap_handler.SoapHandler._urlopen')
    def test_send_request_constructs_correct_soap_envelope(self, mock_urlopen, mock_request_class):
        """Test that send_request constructs correct SOAP envelope."""
        mock_response = MagicMock()
        mock_response.read.return_value = b'<response>test</response>'
        mock_urlopen.return_value = mock_response
        
        mock_request = MagicMock()
        mock_request_class.return_value = mock_request
        
        self.handler.send_request(
            "dmr/control_0",
            URN_RENDERING_CONTROL,
            "GetVolume",
            "<InstanceID>0</InstanceID><Channel>Master</Channel>",
            body_elem="m"
        )
        
        # Get the call arguments
        call_args = mock_request_class.call_args
        soap_body = call_args[0][1]
        
        # Verify SOAP structure
        self.assertIn(b'<?xml version="1.0" encoding="utf-8"?>', soap_body)
        self.assertIn(b'<s:Envelope', soap_body)
        self.assertIn(b'<s:Body>', soap_body)
        self.assertIn(b'<m:GetVolume', soap_body)
        self.assertIn(b'<InstanceID>0</InstanceID>', soap_body)
        self.assertIn(b'</s:Body>', soap_body)
        self.assertIn(b'</s:Envelope>', soap_body)


if __name__ == '__main__':
    unittest.main()

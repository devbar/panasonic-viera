"""SOAP handler for Panasonic Viera TV communication."""
import logging
import random
import base64
import struct
import hmac
import hashlib
from xml.etree import ElementTree
from urllib.request import Request, HTTPError, build_opener, HTTPHandler
from Crypto.Cipher import AES

from .constants import (
    URN_REMOTE_CONTROL,
    URL_TEMPLATE,
    pad,
)
from .exceptions import SOAPError

_LOGGER = logging.getLogger(__name__)


class SoapHandler:
    """Handles SOAP request creation, encryption, and communication."""

    def __init__(self, host, port, proxy=None):
        """Initialize the SOAP handler."""
        self._host = host
        self._port = port
        self._proxy = proxy

    def _get_opener(self):
        """Return an opener with proxy if set."""
        if self._proxy:
            try:
                from urllib.request import ProxyHandler
            except ImportError:
                from urllib2 import ProxyHandler
            proxy_handler = ProxyHandler({'http': self._proxy, 'https': self._proxy})
            return build_opener(proxy_handler, HTTPHandler)
        return build_opener(HTTPHandler)

    def _urlopen(self, req, timeout=5):
        """Open a URL with proxy support."""
        opener = self._get_opener()
        return opener.open(req, timeout=timeout)

    def send_request(self, url, urn, action, params, body_elem="m", encryption_context=None):
        """Send a SOAP request to the TV.
        
        Args:
            url: The URL path for the request
            urn: The URN for the SOAP action
            action: The SOAP action name
            params: The parameters for the SOAP action
            body_elem: The body element prefix (default "m")
            encryption_context: Optional dict with encryption details
                {
                    'app_id': str,
                    'session_id': str,
                    'session_seq_num': int,
                    'session_key': bytearray,
                    'session_iv': bytearray,
                    'session_hmac_key': bytearray
                }
        
        Returns:
            The response body as a string
        """
        is_encrypted = False
        original_seq_num = None

        # Encapsulate URN_REMOTE_CONTROL command in an X_EncryptedCommand if we're using encryption
        if encryption_context and urn == URN_REMOTE_CONTROL and action not in [
            "X_GetEncryptSessionId",
            "X_DisplayPinCode",
            "X_RequestAuth",
        ]:
            is_encrypted = True
            original_seq_num = encryption_context['session_seq_num']
            encryption_context['session_seq_num'] += 1
            
            encrypted_command = (
                f"<X_SessionId>{encryption_context['session_id']}</X_SessionId>"
                f"<X_SequenceNumber>{encryption_context['session_seq_num']:08d}</X_SequenceNumber>"
                "<X_OriginalCommand>"
                f'<u:{action} xmlns:u="urn:{urn}">'
                f"{params}"
                f"</u:{action}>"
                "</X_OriginalCommand>"
            )

            encrypted_command = self.encrypt_payload(
                encrypted_command,
                encryption_context['session_key'],
                encryption_context['session_iv'],
                encryption_context['session_hmac_key'],
            )

            action = "X_EncryptedCommand"
            params = (
                f"<X_ApplicationId>{encryption_context['app_id']}</X_ApplicationId>"
                f"<X_EncInfo>{encrypted_command}</X_EncInfo>"
            )
            body_elem = "u"

        # Construct SOAP request
        soap_body = (
            '<?xml version="1.0" encoding="utf-8"?>'
            '<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/"'
            ' s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">'
            "<s:Body>"
            f'<{body_elem}:{action} xmlns:{body_elem}="urn:{urn}">'
            f"{params}"
            f"</{body_elem}:{action}>"
            "</s:Body>"
            "</s:Envelope>"
        ).encode("utf-8")

        headers = {
            "Host": f"{self._host}:{self._port}",
            "Content-Length": len(soap_body),
            "Content-Type": "text/xml; charset=utf-8",
            "SOAPAction": f'"urn:{urn}#{action}"',
        }

        url = URL_TEMPLATE.format(self._host, self._port, url)

        _LOGGER.debug("Sending to %s:\n%s\n%s", url, headers, soap_body)
        req = Request(url, soap_body, headers)
        
        try:
            res = self._urlopen(req, timeout=5).read()
        except HTTPError as ex:
            # Rollback sequence number on error
            if encryption_context and original_seq_num is not None:
                encryption_context['session_seq_num'] = original_seq_num
            raise ex
        
        _LOGGER.debug("Response: %s", res)

        if is_encrypted:
            root = ElementTree.fromstring(res)
            enc_result = root.find(".//X_EncResult").text
            res = self.decrypt_payload(
                enc_result,
                encryption_context['session_key'],
                encryption_context['session_iv'],
                encryption_context['session_hmac_key']
            )

        return res

    @staticmethod
    def encrypt_payload(data, key, init_vector, hmac_key):
        """Encrypt SOAP payload.
        
        Args:
            data: The data to encrypt
            key: The encryption key
            init_vector: The initialization vector
            hmac_key: The HMAC key
            
        Returns:
            Base64-encoded encrypted payload with HMAC signature
        """
        # The encrypted payload must begin with a 16-byte header (12 random bytes, and 4 bytes for
        # the payload length in big endian)
        payload = bytearray(random.randint(0, 255) for _ in range(12))
        payload += struct.pack(">I", len(data))
        payload += data.encode("latin-1")

        # For compatibility with both Python 2.x and 3.x, flattening types to 'str' or 'bytes'
        init_vector = init_vector.decode("latin-1").encode("latin-1")
        key = key.decode("latin-1").encode("latin-1")
        payload = pad(payload.decode("latin-1")).encode("latin-1")
        hmac_key = hmac_key.decode("latin-1").encode("latin-1")

        # Initialize AES-CBC with key and IV
        aes = AES.new(key, AES.MODE_CBC, init_vector)
        # Encrypt with zero-padding
        ciphertext = aes.encrypt(payload)
        # Compute HMAC-SHA-256
        sig = hmac.new(hmac_key, ciphertext, hashlib.sha256).digest()
        # Concat HMAC with AES-encrypted payload
        return base64.b64encode(ciphertext + sig).decode("latin-1")

    @staticmethod
    def decrypt_payload(data, key, init_vector, hmac_key):
        """Decrypt SOAP payload.
        
        Args:
            data: The base64-encoded encrypted data
            key: The decryption key
            init_vector: The initialization vector
            hmac_key: The HMAC key (unused but kept for consistency)
            
        Returns:
            Decrypted payload as a string
        """
        # For compatibility with both Python 2.x and 3.x, flattening types to 'str' or 'bytes'
        key = key.decode("latin-1").encode("latin-1")
        init_vector = init_vector.decode("latin-1").encode("latin-1")

        # Initialize AES-CBC with key and IV
        aes = AES.new(key, AES.MODE_CBC, init_vector)
        # Decrypt
        decrypted = aes.decrypt(base64.b64decode(data)).decode("latin-1")
        # Unpad and return
        return decrypted[16:].split("\0")[0]

    @staticmethod
    def handle_soap_error(ex):
        """Handle SOAP HTTP errors.
        
        Args:
            ex: The HTTPError exception
            
        Raises:
            SOAPError: If a SOAP error is detected
            HTTPError: Re-raises the original exception if not a SOAP error
        """
        if ex.code == 500:
            xml = ElementTree.fromstring(ex.fp.read())
            for child in xml.iter():
                if child.tag.endswith("errorDescription"):
                    raise SOAPError(child.text)
                if child.tag.endswith("errorCode") and child.text == "600":
                    raise SOAPError("Invalid PIN Code!")
        raise ex

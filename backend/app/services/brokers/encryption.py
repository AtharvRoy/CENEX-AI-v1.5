"""
Token encryption service using Fernet (symmetric encryption).
Used to securely store broker access tokens in the database.
"""

from cryptography.fernet import Fernet
from typing import Optional
import base64
import logging

from app.core.config import settings


logger = logging.getLogger(__name__)


class TokenEncryption:
    """
    Encrypt/decrypt sensitive broker tokens using Fernet.
    
    Uses SECRET_KEY from config as encryption key (must be 32 url-safe base64 chars).
    """
    
    def __init__(self):
        """Initialize Fernet cipher with key derived from SECRET_KEY."""
        # Derive a 32-byte key from SECRET_KEY
        key = self._derive_key(settings.SECRET_KEY)
        self.cipher = Fernet(key)
        logger.debug("Token encryption initialized")
    
    @staticmethod
    def _derive_key(secret: str) -> bytes:
        """
        Derive a Fernet-compatible key from SECRET_KEY.
        
        Args:
            secret: Application secret key
        
        Returns:
            32-byte url-safe base64-encoded key
        """
        # Hash the secret and take first 32 bytes, then base64 encode
        import hashlib
        hashed = hashlib.sha256(secret.encode()).digest()
        return base64.urlsafe_b64encode(hashed)
    
    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt a plaintext string.
        
        Args:
            plaintext: String to encrypt (e.g., access token)
        
        Returns:
            Encrypted string (base64-encoded)
        """
        if not plaintext:
            return ""
        
        try:
            encrypted_bytes = self.cipher.encrypt(plaintext.encode())
            encrypted_str = encrypted_bytes.decode()
            logger.debug(f"Encrypted token (length: {len(plaintext)})")
            return encrypted_str
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise
    
    def decrypt(self, ciphertext: str) -> str:
        """
        Decrypt an encrypted string.
        
        Args:
            ciphertext: Encrypted string (base64-encoded)
        
        Returns:
            Decrypted plaintext string
        """
        if not ciphertext:
            return ""
        
        try:
            decrypted_bytes = self.cipher.decrypt(ciphertext.encode())
            plaintext = decrypted_bytes.decode()
            logger.debug(f"Decrypted token (length: {len(plaintext)})")
            return plaintext
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise
    
    def encrypt_optional(self, plaintext: Optional[str]) -> Optional[str]:
        """Encrypt with None handling."""
        return self.encrypt(plaintext) if plaintext else None
    
    def decrypt_optional(self, ciphertext: Optional[str]) -> Optional[str]:
        """Decrypt with None handling."""
        return self.decrypt(ciphertext) if ciphertext else None


# Global encryption instance
token_encryption = TokenEncryption()

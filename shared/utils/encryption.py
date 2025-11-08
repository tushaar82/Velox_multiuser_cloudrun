"""Encryption utilities for sensitive data."""

import os
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
from typing import Optional


class CredentialEncryption:
    """AES-256 encryption for broker credentials."""
    
    def __init__(self, encryption_key: Optional[str] = None):
        """
        Initialize encryption with a key.
        
        Args:
            encryption_key: Base64-encoded encryption key. If None, uses environment variable.
        """
        if encryption_key is None:
            encryption_key = os.getenv('ENCRYPTION_KEY')
            if not encryption_key:
                raise ValueError("ENCRYPTION_KEY environment variable not set")
        
        self.fernet = Fernet(encryption_key.encode() if isinstance(encryption_key, str) else encryption_key)
    
    @staticmethod
    def generate_key() -> str:
        """
        Generate a new encryption key.
        
        Returns:
            Base64-encoded encryption key
        """
        return Fernet.generate_key().decode()
    
    @staticmethod
    def derive_key_from_password(password: str, salt: Optional[bytes] = None) -> tuple[str, bytes]:
        """
        Derive an encryption key from a password using PBKDF2.
        
        Args:
            password: Password to derive key from
            salt: Salt for key derivation. If None, generates new salt.
            
        Returns:
            Tuple of (base64-encoded key, salt)
        """
        if salt is None:
            salt = os.urandom(16)
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=default_backend()
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return key.decode(), salt
    
    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt plaintext string.
        
        Args:
            plaintext: String to encrypt
            
        Returns:
            Base64-encoded encrypted string
        """
        encrypted = self.fernet.encrypt(plaintext.encode())
        return base64.urlsafe_b64encode(encrypted).decode()
    
    def decrypt(self, ciphertext: str) -> str:
        """
        Decrypt ciphertext string.
        
        Args:
            ciphertext: Base64-encoded encrypted string
            
        Returns:
            Decrypted plaintext string
            
        Raises:
            ValueError: If decryption fails
        """
        try:
            decoded = base64.urlsafe_b64decode(ciphertext.encode())
            decrypted = self.fernet.decrypt(decoded)
            return decrypted.decode()
        except Exception as e:
            raise ValueError(f"Decryption failed: {str(e)}")
    
    def encrypt_dict(self, data: dict) -> str:
        """
        Encrypt a dictionary as JSON.
        
        Args:
            data: Dictionary to encrypt
            
        Returns:
            Base64-encoded encrypted JSON string
        """
        import json
        json_str = json.dumps(data)
        return self.encrypt(json_str)
    
    def decrypt_dict(self, ciphertext: str) -> dict:
        """
        Decrypt a JSON string to dictionary.
        
        Args:
            ciphertext: Base64-encoded encrypted JSON string
            
        Returns:
            Decrypted dictionary
            
        Raises:
            ValueError: If decryption or JSON parsing fails
        """
        import json
        plaintext = self.decrypt(ciphertext)
        try:
            return json.loads(plaintext)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON after decryption: {str(e)}")

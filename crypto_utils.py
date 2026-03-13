from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2
import base64

class CryptoManager:
    def __init__(self, password):
        """Initialize encryption with a password"""
        if not password:
            raise ValueError("Encryption password is required")

        # Derive a key from the password using PBKDF2
        # Using a fixed salt since we need the same key across restarts
        salt = b'image_share_server_salt_v1'
        kdf = PBKDF2(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        self.cipher = Fernet(key)

    def encrypt_file(self, file_data):
        """Encrypt file data"""
        return self.cipher.encrypt(file_data)

    def decrypt_file(self, encrypted_data):
        """Decrypt file data"""
        return self.cipher.decrypt(encrypted_data)

# Global crypto manager instance
crypto_manager = None

def init_crypto(password):
    """Initialize the global crypto manager"""
    global crypto_manager
    crypto_manager = CryptoManager(password)

def get_crypto():
    """Get the global crypto manager"""
    if crypto_manager is None:
        raise RuntimeError("Crypto manager not initialized. Start server with --password argument.")
    return crypto_manager

import logging
import secrets
import ipaddress
import bcrypt
import hashlib

logger = logging.getLogger(__name__)

def verify_password(plain_password, hashed_password):
    try:
        if not plain_password or not hashed_password:
            return False
        # Pre-hash using SHA256 to avoid bcrypt 72-byte truncation
        pwd_hex = hashlib.sha256(plain_password.encode('utf-8')).hexdigest()
        pwd_bytes = pwd_hex.encode('utf-8')

        hash_bytes = hashed_password.encode('utf-8')
        return bcrypt.checkpw(pwd_bytes, hash_bytes)
    except Exception as e:
        logger.error(f"Password verification error: {e}")
        return False

def get_password_hash(password):
    if not password:
        return ""
    # Pre-hash using SHA256 to avoid bcrypt 72-byte truncation
    pwd_hex = hashlib.sha256(password.encode('utf-8')).hexdigest()
    pwd_bytes = pwd_hex.encode('utf-8')

    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_bytes, salt).decode('utf-8')

def is_local_ip(ip_str):
    """
    Checks if an IP address is local/private.
    """
    try:
        ip = ipaddress.ip_address(ip_str)
        return ip.is_loopback or ip.is_private
    except ValueError:
        return False

def verify_api_key(key, expected_key):
    """
    Verifies if the provided API key matches the expected key using constant-time comparison.
    """
    if not key or not expected_key:
        return False
    return secrets.compare_digest(key, expected_key)

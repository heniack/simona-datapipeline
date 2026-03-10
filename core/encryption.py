"""
Sistema de cifrado de contraseñas sensibles usando Fernet (AES)
"""
from cryptography.fernet import Fernet
from django.conf import settings
import base64
import hashlib

def get_cipher():
    """Genera el cipher Fernet usando SECRET_KEY de Django"""
    # Usar SECRET_KEY para derivar una clave Fernet de 32 bytes
    key = hashlib.sha256(settings.SECRET_KEY.encode()).digest()
    fernet_key = base64.urlsafe_b64encode(key)
    return Fernet(fernet_key)

def encrypt_password(password):
    """Cifra una contraseña"""
    if not password:
        return ''
    cipher = get_cipher()
    encrypted = cipher.encrypt(password.encode())
    return encrypted.decode()

def decrypt_password(encrypted_password):
    """Descifra una contraseña"""
    if not encrypted_password:
        return ''
    try:
        cipher = get_cipher()
        decrypted = cipher.decrypt(encrypted_password.encode())
        return decrypted.decode()
    except Exception:
        # Si falla el descifrado, asumir que es texto plano (migración)
        return encrypted_password

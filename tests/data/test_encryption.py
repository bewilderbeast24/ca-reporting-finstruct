import pytest
from data.encryption import encrypt, decrypt

def test_encrypt_decrypt():
    original = "secret data"
    encrypted = encrypt(original)
    assert encrypted != original
    assert type(encrypted) == str
    
    decrypted = decrypt(encrypted)
    assert decrypted == original

def test_encrypt_empty():
    assert encrypt("") == ""
    assert encrypt(None) == None

def test_decrypt_empty():
    assert decrypt("") == ""
    assert decrypt(None) == None

def test_decrypt_invalid():
    # Invalid token should return original value as per implementation
    assert decrypt("invalid") == "invalid"

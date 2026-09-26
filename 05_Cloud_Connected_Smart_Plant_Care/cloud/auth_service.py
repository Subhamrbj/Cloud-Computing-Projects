import hashlib
import hmac
import os
import secrets
import jwt
import time
from fastapi import HTTPException, Header

def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()

def hash_password(password):
    salt = secrets.token_hex(16)
    return salt + ':' + hashlib.scrypt(password.encode(), salt=salt.encode(), n=16384, r=8, p=1).hex()

def verify_password(password, encoded):
    salt, expected = encoded.split(':')
    return hmac.compare_digest(hashlib.scrypt(password.encode(), salt=salt.encode(), n=16384, r=8, p=1).hex(), expected)

def secret():
    value = os.getenv('JWT_SECRET', '')
    if len(value) < 32:
        raise RuntimeError('Set JWT_SECRET to at least 32 random characters in .env')
    return value

def token(uid):
    return jwt.encode({'sub': uid, 'exp': int(time.time()) + 3600, 'iat': int(time.time()), 'iss': 'verdant'}, secret(), algorithm='HS256')

def current_user(authorization: str = Header(default='')):
    try:
        if not authorization.startswith('Bearer '):
            raise ValueError()
        return jwt.decode(authorization[7:], secret(), algorithms=['HS256'], issuer='verdant')['sub']
    except (jwt.PyJWTError, ValueError):
        raise HTTPException(401, 'Sign in required')

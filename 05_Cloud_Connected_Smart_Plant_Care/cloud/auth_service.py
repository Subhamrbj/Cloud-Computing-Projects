import hashlib
import hmac
import os
import secrets
import jwt
import time
from fastapi import HTTPException, Header, Request
from cloud.database_service import Session
from backend.models import User, AccountSecurity, GuestAccount

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
    if len(value) < 32 or value.startswith('replace-'):
        raise RuntimeError('Set JWT_SECRET to at least 32 random characters in .env')
    return value

def token(uid, version=0):
    return jwt.encode({'sub': uid, 'ver': version, 'exp': int(time.time()) + 3600, 'iat': int(time.time()), 'iss': 'plantcare'}, secret(), algorithm='HS256')

def current_user(request: Request, authorization: str = Header(default='')):
    try:
        raw = authorization[7:] if authorization.startswith('Bearer ') else request.cookies.get('plantcare_session')
        if not raw:
            raise ValueError()
        payload = jwt.decode(raw, secret(), algorithms=['HS256'], issuer='plantcare')
        with Session() as db:
            user = db.get(User, payload['sub'])
            security = db.get(AccountSecurity, payload['sub'])
            guest = db.get(GuestAccount, payload['sub'])
            if guest and guest.expires_at <= time.time():
                raise ValueError()
            if not user or payload.get('ver', 0) != (security.auth_version if security else 0):
                raise ValueError()
        return payload['sub']
    except (jwt.PyJWTError, ValueError):
        raise HTTPException(401, 'Sign in required')

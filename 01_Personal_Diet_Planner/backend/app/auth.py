import base64, hashlib, hmac, secrets
from datetime import datetime, timedelta, timezone
import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from .config import settings
from .db import get_db
from .models import User, RevokedToken

bearer = HTTPBearer(auto_error=False)
def hash_password(password):
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 600_000)
    return 'pbkdf2_sha256$600000$'+base64.b64encode(salt).decode()+'$'+base64.b64encode(digest).decode()

def verify_password(password, stored):
    try:
        _, count, salt, digest = stored.split('$')
        actual = hashlib.pbkdf2_hmac('sha256', password.encode(), base64.b64decode(salt), int(count))
        return hmac.compare_digest(actual, base64.b64decode(digest))
    except (ValueError, TypeError): return False

def issue_token(user):
    at = datetime.now(timezone.utc)
    return jwt.encode({'sub': user.id, 'jti': secrets.token_hex(16), 'iat': at, 'exp': at+timedelta(minutes=60)}, settings.secret_key, algorithm='HS256')

def get_claims(creds: HTTPAuthorizationCredentials | None = Depends(bearer), db: Session = Depends(get_db)):
    if not creds: raise HTTPException(401, 'Authentication required')
    try:
        claims=jwt.decode(creds.credentials, settings.secret_key, algorithms=['HS256'])
        if db.get(RevokedToken, claims['jti']): raise ValueError('Revoked')
        if not db.get(User, claims['sub']): raise ValueError('Unknown user')
        return claims
    except (jwt.PyJWTError, ValueError, KeyError): raise HTTPException(401, 'Invalid or expired token')

def current_user(claims: dict = Depends(get_claims), db: Session = Depends(get_db)):
    return db.get(User, claims['sub'])

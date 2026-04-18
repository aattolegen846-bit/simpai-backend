import datetime
import hashlib
import jwt
import os
import secrets
from passlib.hash import pbkdf2_sha256
from typing import Optional, Tuple

from app.models.db_models import RefreshToken
from app.models.user import User
from app.database import db

# Secret key should be at least 32 bytes for HS256 to avoid warnings and potential issues
DEFAULT_SECRET = "senior-secret-key-that-is-at-least-32-bytes-long-for-security"
SECRET_KEY = os.getenv("SECRET_KEY", DEFAULT_SECRET)
ACCESS_TOKEN_HOURS = int(os.getenv("JWT_EXP_HOURS", "24"))
REFRESH_TOKEN_DAYS = int(os.getenv("JWT_REFRESH_DAYS", "30"))
MAX_FAILED_LOGIN_ATTEMPTS = int(os.getenv("MAX_FAILED_LOGIN_ATTEMPTS", "5"))
LOGIN_LOCK_MINUTES = int(os.getenv("LOGIN_LOCK_MINUTES", "15"))


class AuthService:
    @staticmethod
    def register_user(username: str, email: str, password: str) -> Tuple[bool, str]:
        if User.query.filter_by(username=username).first():
            return False, "Username already exists"
        if User.query.filter_by(email=email).first():
            return False, "Email already exists"

        hashed_password = pbkdf2_sha256.hash(password)
        new_user = User(username=username, email=email, password_hash=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        return True, "User registered successfully"

    @staticmethod
    def authenticate_user(identifier: str, password: str) -> Optional[User]:
        user = User.query.filter((User.username == identifier) | (User.email == identifier)).first()
        if not user:
            return None
        now = datetime.datetime.now(datetime.timezone.utc)
        if user.locked_until and user.locked_until > now:
            return None
        if pbkdf2_sha256.verify(password, user.password_hash):
            user.failed_login_count = 0
            user.locked_until = None
            db.session.commit()
            return user
        user.failed_login_count += 1
        if user.failed_login_count >= MAX_FAILED_LOGIN_ATTEMPTS:
            user.locked_until = now + datetime.timedelta(minutes=LOGIN_LOCK_MINUTES)
            user.failed_login_count = 0
        db.session.commit()
        return None

    @staticmethod
    def generate_token(user_id: int) -> str:
        payload = {
            "exp": datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=ACCESS_TOKEN_HOURS),
            "iat": datetime.datetime.now(datetime.timezone.utc),
            "sub": str(user_id),
            "type": "access",
        }
        return jwt.encode(payload, SECRET_KEY, algorithm="HS256")

    @staticmethod
    def generate_refresh_token(user_id: int) -> str:
        raw = secrets.token_urlsafe(48)
        token_hash = hashlib.sha256(raw.encode("utf-8")).hexdigest()
        refresh = RefreshToken(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=datetime.datetime.now(datetime.timezone.utc)
            + datetime.timedelta(days=REFRESH_TOKEN_DAYS),
        )
        db.session.add(refresh)
        db.session.commit()
        return raw

    @staticmethod
    def rotate_refresh_token(raw_refresh_token: str) -> Optional[tuple[str, str]]:
        token_hash = hashlib.sha256(raw_refresh_token.encode("utf-8")).hexdigest()
        record = RefreshToken.query.filter_by(token_hash=token_hash, revoked=False).first()
        if not record:
            return None
        expiry = record.expires_at
        if expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=datetime.timezone.utc)
        if expiry < datetime.datetime.now(datetime.timezone.utc):
            return None
        user = db.session.get(User, record.user_id)
        if not user:
            return None
        record.revoked = True
        access = AuthService.generate_token(user.id)
        new_refresh = AuthService.generate_refresh_token(user.id)
        db.session.commit()
        return access, new_refresh

    @staticmethod
    def revoke_refresh_token(raw_refresh_token: str) -> bool:
        token_hash = hashlib.sha256(raw_refresh_token.encode("utf-8")).hexdigest()
        record = RefreshToken.query.filter_by(token_hash=token_hash, revoked=False).first()
        if not record:
            return False
        record.revoked = True
        db.session.commit()
        return True

    @staticmethod
    def decode_token(token: str) -> Optional[int]:
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
            if payload.get("type") != "access":
                return None
            return int(payload["sub"])
        except Exception as e:
            print(f"JWT Decode Error: {e}")
            return None

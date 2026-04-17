import datetime
import jwt
import os
from passlib.hash import pbkdf2_sha256
from typing import Optional, Tuple

from app.models.user import User
from app.database import db

# Secret key should be at least 32 bytes for HS256 to avoid warnings and potential issues
DEFAULT_SECRET = "senior-secret-key-that-is-at-least-32-bytes-long-for-security"
SECRET_KEY = os.getenv("SECRET_KEY", DEFAULT_SECRET)


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
        if user and pbkdf2_sha256.verify(password, user.password_hash):
            return user
        return None

    @staticmethod
    def generate_token(user_id: int) -> str:
        payload = {
            "exp": datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=1),
            "iat": datetime.datetime.now(datetime.timezone.utc),
            "sub": str(user_id)
        }
        return jwt.encode(payload, SECRET_KEY, algorithm="HS256")

    @staticmethod
    def decode_token(token: str) -> Optional[int]:
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
            return int(payload["sub"])
        except Exception as e:
            print(f"JWT Decode Error: {e}")
            return None

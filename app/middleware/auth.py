from functools import wraps
import logging
from flask import jsonify, request, g
from app.database import db
from app.models.user import User
from app.services.auth_service import AuthService

auth_service = AuthService()
logger = logging.getLogger(__name__)

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get("Authorization")
        if not token:
            return jsonify({"error": "unauthorized", "message": "Token is missing"}), 401
        
        if token.startswith("Bearer "):
            token = token.split(" ")[1]
            
        user_id = auth_service.decode_token(token)
        if not user_id:
            return jsonify({"error": "unauthorized", "message": "Token is invalid or expired"}), 401
            
        current_user = db.session.get(User, user_id)
        if not current_user:
            return jsonify({"error": "unauthorized", "message": "User not found"}), 401
            
        if hasattr(current_user, 'is_active') and not current_user.is_active:
             return jsonify({"error": "forbidden", "message": "User account is inactive"}), 403

        g.current_user = current_user
        return f(current_user, *args, **kwargs)
    return decorated

def role_required(*roles):
    def wrapper(fn):
        @wraps(fn)
        @token_required
        def decorated(current_user, *args, **kwargs):
            if current_user.role not in roles:
                logger.warning(
                    "forbidden_access_attempt",
                    extra={
                        "user_id": current_user.id,
                        "role": current_user.role,
                        "required_roles": roles,
                        "path": request.path
                    }
                )
                return jsonify({"error": "forbidden", "message": "You do not have permission to access this resource"}), 403
            return fn(current_user, *args, **kwargs)

        return decorated

    return wrapper

"""
MADN-X Authentication Module
=============================
JWT-based authentication with user registration and login.

Features:
- User registration with hashed passwords
- JWT token generation and validation
- Protected endpoint decorator
- Token refresh capability
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from dataclasses import dataclass, field, asdict
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import hashlib
import secrets
import json
import os
import jwt

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

# Secret key for JWT - in production, use environment variable
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "madn-x-super-secret-key-change-in-production-2024")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours
REFRESH_TOKEN_EXPIRE_DAYS = 7

# Simple file-based user storage (use a real DB in production)
USERS_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "users.json")

security = HTTPBearer(auto_error=False)


# ═══════════════════════════════════════════════════════════════════════════════
# DATA MODELS
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class User:
    """User model."""
    id: str
    email: str
    password_hash: str
    name: str
    role: str = "user"  # user, admin, clinician
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    last_login: Optional[str] = None
    is_active: bool = True


@dataclass
class TokenPayload:
    """JWT token payload."""
    sub: str  # user_id
    email: str
    name: str
    role: str
    exp: datetime
    iat: datetime
    type: str = "access"  # access or refresh


@dataclass
class AuthTokens:
    """Authentication token pair."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = ACCESS_TOKEN_EXPIRE_MINUTES * 60


# ═══════════════════════════════════════════════════════════════════════════════
# PASSWORD HASHING
# ═══════════════════════════════════════════════════════════════════════════════

def hash_password(password: str) -> str:
    """Hash a password using SHA-256 with salt."""
    salt = secrets.token_hex(16)
    password_hash = hashlib.sha256(f"{salt}{password}".encode()).hexdigest()
    return f"{salt}:{password_hash}"


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a password against its hash."""
    try:
        salt, stored_hash = password_hash.split(":")
        computed_hash = hashlib.sha256(f"{salt}{password}".encode()).hexdigest()
        return computed_hash == stored_hash
    except ValueError:
        return False


# ═══════════════════════════════════════════════════════════════════════════════
# USER STORAGE
# ═══════════════════════════════════════════════════════════════════════════════

def _ensure_data_dir():
    """Ensure the data directory exists."""
    os.makedirs(os.path.dirname(USERS_FILE), exist_ok=True)


def _load_users() -> Dict[str, Dict]:
    """Load users from file."""
    _ensure_data_dir()
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r") as f:
            return json.load(f)
    return {}


def _save_users(users: Dict[str, Dict]):
    """Save users to file."""
    _ensure_data_dir()
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=2)


def get_user_by_email(email: str) -> Optional[User]:
    """Get a user by email."""
    users = _load_users()
    for user_data in users.values():
        if user_data.get("email") == email:
            return User(**user_data)
    return None


def get_user_by_id(user_id: str) -> Optional[User]:
    """Get a user by ID."""
    users = _load_users()
    if user_id in users:
        return User(**users[user_id])
    return None


def create_user(email: str, password: str, name: str, role: str = "user") -> User:
    """Create a new user."""
    # Check if email already exists
    if get_user_by_email(email):
        raise ValueError("Email already registered")
    
    user_id = f"USER-{secrets.token_hex(8).upper()}"
    user = User(
        id=user_id,
        email=email,
        password_hash=hash_password(password),
        name=name,
        role=role
    )
    
    users = _load_users()
    users[user_id] = asdict(user)
    _save_users(users)
    
    return user


def update_last_login(user_id: str):
    """Update user's last login timestamp."""
    users = _load_users()
    if user_id in users:
        users[user_id]["last_login"] = datetime.utcnow().isoformat()
        _save_users(users)


# ═══════════════════════════════════════════════════════════════════════════════
# JWT TOKEN OPERATIONS
# ═══════════════════════════════════════════════════════════════════════════════

def create_access_token(user: User) -> str:
    """Create a JWT access token for a user."""
    now = datetime.utcnow()
    expire = now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    payload = {
        "sub": user.id,
        "email": user.email,
        "name": user.name,
        "role": user.role,
        "exp": expire,
        "iat": now,
        "type": "access"
    }
    
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(user: User) -> str:
    """Create a JWT refresh token for a user."""
    now = datetime.utcnow()
    expire = now + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    
    payload = {
        "sub": user.id,
        "type": "refresh",
        "exp": expire,
        "iat": now
    }
    
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def create_tokens(user: User) -> AuthTokens:
    """Create both access and refresh tokens."""
    return AuthTokens(
        access_token=create_access_token(user),
        refresh_token=create_refresh_token(user)
    )


def decode_token(token: str) -> Dict[str, Any]:
    """Decode and validate a JWT token."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired"
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# AUTHENTICATION FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def authenticate_user(email: str, password: str) -> User:
    """Authenticate a user with email and password."""
    user = get_user_by_email(email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    if not verify_password(password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled"
        )
    
    update_last_login(user.id)
    return user


def refresh_access_token(refresh_token: str) -> AuthTokens:
    """Get new tokens using a refresh token."""
    payload = decode_token(refresh_token)
    
    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type"
        )
    
    user = get_user_by_id(payload["sub"])
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    return create_tokens(user)


# ═══════════════════════════════════════════════════════════════════════════════
# FASTAPI DEPENDENCIES
# ═══════════════════════════════════════════════════════════════════════════════

async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[User]:
    """
    Get the current authenticated user from JWT token.
    Returns None if no token provided (for optional auth).
    """
    if not credentials:
        return None
    
    payload = decode_token(credentials.credentials)
    
    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type"
        )
    
    user = get_user_by_id(payload["sub"])
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    return user


async def require_auth(
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())
) -> User:
    """
    Require authentication - raises 401 if not authenticated.
    Use this for protected endpoints.
    """
    payload = decode_token(credentials.credentials)
    
    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type"
        )
    
    user = get_user_by_id(payload["sub"])
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    return user


async def require_admin(user: User = Depends(require_auth)) -> User:
    """Require admin role."""
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return user


async def require_clinician(user: User = Depends(require_auth)) -> User:
    """Require clinician or admin role."""
    if user.role not in ["admin", "clinician"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Clinician access required"
        )
    return user

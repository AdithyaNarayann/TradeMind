"""
Authentication routes — Register & Login using MySQL.

POST /api/v1/auth/register  → create user, return JWT
POST /api/v1/auth/login     → verify credentials, return JWT
GET  /api/v1/auth/me        → return current user from JWT
"""
import bcrypt
import jwt
import datetime
import os
import time
import hashlib
from collections import defaultdict
from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr, field_validator
import re
import structlog

from ...infrastructure.database.session import get_conn
from ...core.config import get_settings
from ..middleware import limiter

_settings = get_settings()
logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])

# JWT config — read from pydantic Settings (which loads .env)
JWT_SECRET = _settings.jwt_secret
if not JWT_SECRET:
    raise RuntimeError(
        "FATAL: JWT_SECRET is not set in .env. "
        "Generate one with: python -c \"import secrets; print(secrets.token_hex(32))\""
    )
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = 1  # Shortened from 24h to 1h for security

# ── Account lockout tracking (in-memory) ──────────────────────────
_failed_attempts: dict = defaultdict(list)  # key -> [timestamps]
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_WINDOW_SECONDS = 900  # 15 minutes


def _check_lockout(key: str) -> None:
    """Raise 429 if too many failed attempts in the lockout window."""
    now = time.time()
    # Prune old entries
    _failed_attempts[key] = [
        t for t in _failed_attempts[key]
        if now - t < LOCKOUT_WINDOW_SECONDS
    ]
    if len(_failed_attempts[key]) >= MAX_FAILED_ATTEMPTS:
        raise HTTPException(
            status_code=429,
            detail="Too many failed attempts. Try again in 15 minutes.",
        )


def _record_failure(key: str) -> None:
    """Record a failed login attempt."""
    _failed_attempts[key].append(time.time())


def _clear_failures(key: str) -> None:
    """Clear failed attempts on successful login."""
    _failed_attempts.pop(key, None)

security = HTTPBearer(auto_error=False)


# ── Request / Response models ─────────────────────────────────────

class RegisterRequest(BaseModel):
    full_name: str
    email: EmailStr
    password: str

    @field_validator("full_name")
    @classmethod
    def name_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("Full name is required")
        return v.strip()

    @field_validator("password")
    @classmethod
    def password_strong(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one digit")
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", v):
            raise ValueError("Password must contain at least one special character")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class AuthResponse(BaseModel):
    token: str
    user: dict


class UserResponse(BaseModel):
    id: int
    full_name: str
    email: str


# ── Helpers ────────────────────────────────────────────────────────

def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))


def _create_token(user_id: int, email: str, full_name: str) -> str:
    payload = {
        "sub": str(user_id),
        "email": email,
        "full_name": full_name,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=JWT_EXPIRE_HOURS),
        "iat": datetime.datetime.utcnow(),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Dependency: decode JWT **or** validate a tm_ API key and return user dict."""
    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")

    token = credentials.credentials

    # ── API-key path (starts with tm_) ─────────────────────────────
    if token.startswith("tm_"):
        import aiomysql
        async with get_conn() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(
                    """SELECT ak.user_id, u.email, u.full_name
                       FROM api_keys ak
                       JOIN users u ON u.id = ak.user_id
                       WHERE ak.api_key = %s AND ak.is_active = 1""",
                    (token,),
                )
                row = await cur.fetchone()
                if not row:
                    raise HTTPException(status_code=401, detail="Invalid or revoked API key")
                # touch last_used_at
                await cur.execute(
                    "UPDATE api_keys SET last_used_at = NOW() WHERE api_key = %s",
                    (token,),
                )
        return {
            "id": int(row["user_id"]),
            "email": row["email"],
            "full_name": row["full_name"],
        }

    # ── JWT path ───────────────────────────────────────────────────
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return {
            "id": int(payload["sub"]),
            "email": payload["email"],
            "full_name": payload["full_name"],
        }
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


# ── Routes ─────────────────────────────────────────────────────────

@router.post("/register", response_model=AuthResponse)
@limiter.limit("5/minute")
async def register(request: Request, body: RegisterRequest):
    """Create a new user account."""
    async with get_conn() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            # Check if email already exists
            await cur.execute("SELECT id FROM users WHERE email = %s", (body.email,))
            existing = await cur.fetchone()
            if existing:
                raise HTTPException(status_code=409, detail="Email already registered")

            # Insert new user
            hashed = _hash_password(body.password)
            await cur.execute(
                "INSERT INTO users (full_name, email, password_hash) VALUES (%s, %s, %s)",
                (body.full_name, body.email, hashed),
            )
            user_id = cur.lastrowid

    token = _create_token(user_id, body.email, body.full_name)
    return AuthResponse(
        token=token,
        user={"id": user_id, "full_name": body.full_name, "email": body.email},
    )


@router.post("/login", response_model=AuthResponse)
@limiter.limit("5/minute")
async def login(request: Request, body: LoginRequest):
    """Authenticate and return a JWT."""
    # Check lockout before attempting login
    lockout_key = hashlib.sha256(body.email.lower().encode()).hexdigest()[:16]
    _check_lockout(lockout_key)

    async with get_conn() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute(
                "SELECT id, full_name, email, password_hash FROM users WHERE email = %s",
                (body.email,),
            )
            user = await cur.fetchone()

    if not user or not _verify_password(body.password, user["password_hash"]):
        _record_failure(lockout_key)
        logger.warning("login_failed", email_hash=lockout_key)
        raise HTTPException(status_code=401, detail="Invalid email or password")

    _clear_failures(lockout_key)
    token = _create_token(user["id"], user["email"], user["full_name"])
    return AuthResponse(
        token=token,
        user={"id": user["id"], "full_name": user["full_name"], "email": user["email"]},
    )


@router.get("/me", response_model=UserResponse)
async def me(user=Depends(get_current_user)):
    """Return the currently authenticated user."""
    return UserResponse(**user)


# Need to import aiomysql for DictCursor
import aiomysql

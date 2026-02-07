"""
Authentication routes — Register & Login using MySQL.

POST /api/v1/auth/register  → create user, return JWT
POST /api/v1/auth/login     → verify credentials, return JWT
GET  /api/v1/auth/me        → return current user from JWT
"""
import bcrypt
import jwt
import datetime
from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr, field_validator
import re

from ..db.mysql import get_conn

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])

JWT_SECRET = "trademind-secret-key-change-in-production"
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = 24

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
        if len(v) < 6:
            raise ValueError("Password must be at least 6 characters")
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
    """Dependency: decode JWT and return user dict."""
    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
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
async def register(body: RegisterRequest):
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
async def login(body: LoginRequest):
    """Authenticate and return a JWT."""
    async with get_conn() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute(
                "SELECT id, full_name, email, password_hash FROM users WHERE email = %s",
                (body.email,),
            )
            user = await cur.fetchone()

    if not user or not _verify_password(body.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")

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

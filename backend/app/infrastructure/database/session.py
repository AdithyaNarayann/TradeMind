"""
MySQL async connection pool using aiomysql.
"""
import aiomysql
import os
from contextlib import asynccontextmanager

# SECURITY: No default passwords — all must come from env vars
MYSQL_HOST = os.getenv("MYSQL_HOST", "127.0.0.1")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
MYSQL_USER = os.getenv("MYSQL_USER", "")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
MYSQL_DB = os.getenv("MYSQL_DB", "trademind")

if not MYSQL_USER or not MYSQL_PASSWORD:
    import warnings
    warnings.warn(
        "MYSQL_USER and MYSQL_PASSWORD should be set via environment variables. "
        "Do not use default/hardcoded credentials in production.",
        stacklevel=2,
    )

_pool: aiomysql.Pool | None = None


async def get_pool() -> aiomysql.Pool:
    """Get or create the global connection pool."""
    global _pool
    if _pool is None:
        _pool = await aiomysql.create_pool(
            host=MYSQL_HOST,
            port=MYSQL_PORT,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            db=MYSQL_DB,
            autocommit=True,
            minsize=1,
            maxsize=10,
            charset="utf8mb4",
        )
    return _pool


@asynccontextmanager
async def get_conn():
    """Yield an aiomysql connection from the pool."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        yield conn


async def close_pool():
    """Close the pool on shutdown."""
    global _pool
    if _pool is not None:
        _pool.close()
        await _pool.wait_closed()
        _pool = None

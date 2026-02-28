"""
MySQL async connection pool using aiomysql.
"""
import aiomysql
import structlog
from contextlib import asynccontextmanager
from ...core.config import get_settings

_settings = get_settings()
_logger = structlog.get_logger("database")

# SECURITY: Read all DB config from pydantic Settings (which loads .env)
MYSQL_HOST = _settings.mysql_host
MYSQL_PORT = _settings.mysql_port
MYSQL_USER = _settings.mysql_user
MYSQL_PASSWORD = _settings.mysql_password
MYSQL_DB = _settings.mysql_db

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
        try:
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
                pool_recycle=3600,  # Reconnect stale connections after 1 hour
            )
            _logger.info("mysql_pool_created", host=MYSQL_HOST, port=MYSQL_PORT, db=MYSQL_DB)
        except Exception as e:
            _logger.error("mysql_pool_creation_failed", error=str(e), host=MYSQL_HOST, port=MYSQL_PORT)
            raise
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

import os
import redis as redis_module
from redis.exceptions import RedisError
import ssl
import sqlite3
import time
from common.logging.logger import log_info, log_error
from typing import Dict

# Environment variables
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_DB = int(os.getenv("REDIS_DB", 0))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD")
REDIS_USE_SSL = os.getenv("REDIS_USE_SSL", "false").lower() == "true"
REDIS_SSL_CA_CERTS = os.getenv("REDIS_SSL_CA_CERTS")
REDIS_SSL_CERT = os.getenv("REDIS_SSL_CERT")
REDIS_SSL_KEY = os.getenv("REDIS_SSL_KEY")

# Redis connection with SQLite fallback
redis = None
USE_FALLBACK = False
fallback_db = sqlite3.connect(":memory:")
fallback_db.execute("CREATE TABLE IF NOT EXISTS cache (key TEXT PRIMARY KEY, value TEXT, expiry REAL)")

try:
    if REDIS_USE_SSL:
        ssl_context = ssl.create_default_context(cafile=REDIS_SSL_CA_CERTS)
        ssl_context.load_cert_chain(certfile=REDIS_SSL_CERT, keyfile=REDIS_SSL_KEY)
        pool = redis_module.ConnectionPool.from_url(
            f"rediss://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}",
            password=REDIS_PASSWORD,
            ssl_context=ssl_context,
            decode_responses=True
        )
    else:
        pool = redis_module.ConnectionPool(
            host=REDIS_HOST,
            port=REDIS_PORT,
            db=REDIS_DB,
            password=REDIS_PASSWORD,
            decode_responses=True
        )

    redis = redis_module.Redis(connection_pool=pool)
    redis.ping()
    log_info("Redis connection established", extra={"host": REDIS_HOST, "ssl": REDIS_USE_SSL})
except RedisError as e:
    USE_FALLBACK = True
    log_error("Redis connection failed, switching to SQLite fallback", extra={"error": str(e)})

class RedisClientError(Exception):
    pass

def get(key: str) -> str | None:
    try:
        if USE_FALLBACK:
            cursor = fallback_db.execute("SELECT value, expiry FROM cache WHERE key = ?", (key,))
            result = cursor.fetchone()
            if result and (result[1] is None or result[1] > time.time()):
                return result[0]
            return None
        value = redis.get(key)
        log_info("Redis get", extra={"key": key, "value": value})
        return value
    except (RedisError, sqlite3.Error) as e:
        log_error("Redis get failed", extra={"key": key, "error": str(e)})
        raise RedisClientError(f"Failed to get key {key}: {str(e)}")

def setex(key: str, ttl: int, value: str):
    try:
        if USE_FALLBACK:
            expiry = time.time() + ttl if ttl else None
            fallback_db.execute("INSERT OR REPLACE INTO cache (key, value, expiry) VALUES (?, ?, ?)", (key, value, expiry))
            fallback_db.commit()
        else:
            redis.setex(key, ttl, value)
        log_info("Redis setex", extra={"key": key, "ttl": ttl})
    except (RedisError, sqlite3.Error) as e:
        log_error("Redis setex failed", extra={"key": key, "error": str(e)})
        raise RedisClientError(f"Failed to set key {key}: {str(e)}")

def delete(key: str) -> int:
    try:
        if USE_FALLBACK:
            result = fallback_db.execute("DELETE FROM cache WHERE key = ?", (key,))
            fallback_db.commit()
            return result.rowcount
        result = redis.delete(key)
        log_info("Redis delete", extra={"key": key, "deleted": result})
        return result
    except (RedisError, sqlite3.Error) as e:
        log_error("Redis delete failed", extra={"key": key, "error": str(e)})
        raise RedisClientError(f"Failed to delete key {key}: {str(e)}")

def keys(pattern: str) -> list:
    try:
        if USE_FALLBACK:
            cursor = fallback_db.execute("SELECT key FROM cache WHERE key LIKE ?", (pattern.replace("*", "%"),))
            result = [row[0] for row in cursor.fetchall()]
            return result
        result = redis.keys(pattern)
        log_info("Redis keys", extra={"pattern": pattern, "result": result})
        return result
    except (RedisError, sqlite3.Error) as e:
        log_error("Redis keys failed", extra={"pattern": pattern, "error": str(e)})
        raise RedisClientError(f"Failed to fetch keys with pattern {pattern}: {str(e)}")

def hset(key: str, mapping: dict):
    try:
        if USE_FALLBACK:
            for field, value in mapping.items():
                expiry = time.time() + 3600
                fallback_db.execute("INSERT OR REPLACE INTO cache (key, value, expiry) VALUES (?, ?, ?)", (f"{key}:{field}", str(value), expiry))
            fallback_db.commit()
        else:
            redis.hset(key, mapping=mapping)
        log_info("Redis hset", extra={"key": key})
    except (RedisError, sqlite3.Error) as e:
        log_error("Redis hset failed", extra={"key": key, "error": str(e)})
        raise RedisClientError(f"Failed to set hash {key}: {str(e)}")

def hgetall(key: str) -> dict:
    try:
        if USE_FALLBACK:
            cursor = fallback_db.execute("SELECT key, value FROM cache WHERE key LIKE ?", (f"{key}:%",))
            return {row[0].split(":", 1)[1]: row[1] for row in cursor.fetchall() if row[1] and (row[1] is None or row[1] > time.time())}
        result = redis.hgetall(key)
        log_info("Redis hgetall", extra={"key": key, "result": result})
        return result
    except (RedisError, sqlite3.Error) as e:
        log_error("Redis hgetall failed", extra={"key": key, "error": str(e)})
        raise RedisClientError(f"Failed to get hash {key}: {str(e)}")

def incr(key: str) -> int:
    try:
        if USE_FALLBACK:
            cursor = fallback_db.execute("SELECT value FROM cache WHERE key = ?", (key,))
            value = int(cursor.fetchone()[0] or 0) + 1 if cursor.rowcount > 0 else 1
            fallback_db.execute("INSERT OR REPLACE INTO cache (key, value, expiry) VALUES (?, ?, NULL)", (key, str(value)))
            fallback_db.commit()
            return value
        value = redis.incr(key)
        log_info("Redis incr", extra={"key": key, "value": value})
        return value
    except (RedisError, sqlite3.Error) as e:
        log_error("Redis incr failed", extra={"key": key, "error": str(e)})
        raise RedisClientError(f"Failed to increment key {key}: {str(e)}")

def expire(key: str, ttl: int):
    try:
        if USE_FALLBACK:
            expiry = time.time() + ttl
            fallback_db.execute("UPDATE cache SET expiry = ? WHERE key = ?", (expiry, key))
            fallback_db.commit()
        else:
            redis.expire(key, ttl)
        log_info("Redis expire", extra={"key": key, "ttl": ttl})
    except (RedisError, sqlite3.Error) as e:
        log_error("Redis expire failed", extra={"key": key, "error": str(e)})
        raise RedisClientError(f"Failed to set expiration for key {key}: {str(e)}")

def ttl(key: str) -> int:
    try:
        if USE_FALLBACK:
            cursor = fallback_db.execute("SELECT expiry FROM cache WHERE key = ?", (key,))
            result = cursor.fetchone()
            if result and result[0]:
                return int(result[0] - time.time())
            return -1
        value = redis.ttl(key)
        log_info("Redis ttl", extra={"key": key, "value": value})
        return value
    except (RedisError, sqlite3.Error) as e:
        log_error("Redis ttl failed", extra={"key": key, "error": str(e)})
        raise RedisClientError(f"Failed to get TTL for key {key}: {str(e)}")
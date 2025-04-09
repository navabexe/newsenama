# File: src/domain/auth/services/session_service.py
from redis.asyncio import Redis
from typing import List, Dict

from common.logging.logger import log_info
from common.utils.string_utils import decode_value
from common.config.settings import settings
from infrastructure.database.redis.repositories.otp_repository import OTPRepository

class SessionService:
    def __init__(self, repo: OTPRepository):
        self.repo = repo

    async def delete_incomplete_sessions(self, user_id: str):
        session_keys = await self.repo.scan_keys(f"sessions:{user_id}:*")
        for key in session_keys:
            session_data = await self.repo.hgetall(key)
            status = session_data.get(b"status") or session_data.get("status", b"")
            if decode_value(status) != "active":
                await self.repo.delete(key)
                log_info("Deleted incomplete session", extra={"user_id": user_id, "session_key": key})

    async def get_sessions(self, user_id: str, client_ip: str, status_filter: str = "active") -> List[Dict]:
        session_keys = await self.repo.scan_keys(f"sessions:{user_id}:*")
        sessions = []
        redis = await self.repo.redis

        for key in session_keys:
            key_type = await redis.type(key)
            key_type_str = key_type.decode() if isinstance(key_type, bytes) else str(key_type)

            if key_type_str != "hash":
                log_info("Skipping non-hash key during session read", extra={
                    "key": key,
                    "type": key_type_str,
                    "user_id": user_id,
                    "ip": client_ip
                })
                continue

            session_data = await self.repo.hgetall(key)
            session_id = key.split(":")[-1]
            raw_status = session_data.get(b"status") or session_data.get("status", b"unknown")
            is_active = decode_value(raw_status) == "active"

            log_info("Processing session", extra={
                "key": key,
                "session_id": session_id,
                "raw_status": raw_status,
                "is_active": is_active,
                "status_filter": status_filter,
                "user_id": user_id,
                "ip": client_ip
            })

            if status_filter == "active" and not is_active:
                log_info("Session filtered out due to inactive status", extra={
                    "session_id": session_id,
                    "user_id": user_id,
                    "ip": client_ip
                })
                continue

            session_ttl = await redis.ttl(key)
            log_info("Session TTL checked", extra={
                "session_id": session_id,
                "ttl": session_ttl,
                "user_id": user_id,
                "ip": client_ip
            })
            if session_ttl == -2:
                log_info("Session skipped due to expired key", extra={
                    "session_id": session_id,
                    "user_id": user_id,
                    "ip": client_ip
                })
                continue
            ttl_label = "no-expiry" if session_ttl == -1 else f"{session_ttl} seconds"

            # اصلاح: کلیدها رو هم به‌صورت str و هم bytes چک می‌کنیم
            sessions.append({
                "session_id": session_id,
                "user_id": user_id,
                "device_name": decode_value(session_data.get(b"device_name") or session_data.get("device_name")) or "Unknown Device",
                "device_type": decode_value(session_data.get(b"device_type") or session_data.get("device_type")) or "Desktop",
                "os": decode_value(session_data.get(b"os") or session_data.get("os")) or "Unknown",
                "browser": decode_value(session_data.get(b"browser") or session_data.get("browser")) or "Unknown",
                "user_agent": decode_value(session_data.get(b"user_agent") or session_data.get("user_agent")) or "Unknown",
                "ip_address": decode_value(session_data.get(b"ip") or session_data.get("ip")) or "unknown",
                "location": decode_value(session_data.get(b"location") or session_data.get("location")) or "Unknown",
                "is_active": is_active,
                "created_at": decode_value(session_data.get(b"created_at") or session_data.get("created_at")) or "unknown",
                "last_seen_at": decode_value(session_data.get(b"last_seen_at") or session_data.get("last_seen_at")),
                "ttl": ttl_label
            })

        log_info("Sessions retrieved successfully", extra={
            "user_id": user_id,
            "session_count": len(sessions),
            "status_filter": status_filter,
            "ip": client_ip
        })
        return sessions

def get_session_service(redis: Redis = None) -> SessionService:
    repo = OTPRepository(redis)
    return SessionService(repo)
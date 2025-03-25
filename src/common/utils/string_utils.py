import uuid
import hashlib
import secrets
from datetime import datetime, UTC

def generate_token(prefix: str = "token", user_id: str = None, ttl: int = 300) -> str:
    now = datetime.now(UTC).isoformat()
    random_str = secrets.token_hex(8)
    base = f"{prefix}-{user_id or ''}-{now}-{random_str}-{str(uuid.uuid4())}"

    return hashlib.sha256(base.encode()).hexdigest()



def generate_otp_code(length: int = 6) -> str:
    return ''.join(secrets.choice("0123456789") for _ in range(length))

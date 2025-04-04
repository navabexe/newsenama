# File: common/utils/token_utils.py

import jwt
from typing import Dict
from jwt import ExpiredSignatureError, InvalidTokenError
from datetime import datetime, timezone


SECRET_KEY_PLACEHOLDER = "replace_me"  # replace when decoding requires signature validation


def get_token_payload(token: str) -> Dict:
    """
    Decodes JWT and returns payload without verifying signature.
    Useful for extracting non-sensitive claims.
    """
    try:
        return jwt.decode(token, options={"verify_signature": False, "verify_exp": False}, algorithms=["HS256"])
    except InvalidTokenError:
        raise ValueError("Invalid token format")


def get_token_exp(token: str) -> int:
    payload = get_token_payload(token)
    exp = payload.get("exp")
    if exp is None:
        raise ValueError("Token has no expiration (exp) field")
    return exp


def is_token_expired(token: str) -> bool:
    try:
        exp = get_token_exp(token)
        return datetime.now(timezone.utc).timestamp() > exp
    except ValueError:
        return True

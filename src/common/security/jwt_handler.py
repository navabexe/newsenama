"""
JWT Handler Module

This module aggregates all JWT-related functionality, including token generation,
decoding, revocation, and authentication utilities. It serves as a central import
point for JWT operations in the application.

Key components:
- Token generation: Access, refresh, and temporary tokens.
- Token decoding and validation.
- Token revocation management.
- Authentication utilities for extracting user information.
"""

from common.security.jwt.tokens import (
    generate_temp_token,
    generate_access_token,
    generate_refresh_token
)
from common.security.jwt.decode import decode_token
from common.security.jwt.revoke import revoke_token, revoke_all_user_tokens
from common.security.jwt.auth import get_token_from_header, get_current_user
from common.security.jwt.errors import JWTError
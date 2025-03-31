# File: common/security/jwt/errors.py
class JWTError(Exception):
    """Base exception class for JWT-related errors."""

    def __init__(self, message: str, status_code: int = 401):
        """
        Initialize JWTError with a message and optional status code.

        Args:
            message (str): Error message describing the issue.
            status_code (int): HTTP status code associated with the error (default: 401).
        """
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class TokenRevokedError(JWTError):
    """Exception raised when a token is revoked."""

    def __init__(self, jti: str):
        super().__init__(f"Token with jti '{jti}' has been revoked", status_code=401)


class TokenTypeMismatchError(JWTError):
    """Exception raised when token type does not match expected type."""

    def __init__(self, expected: str, actual: str):
        super().__init__(f"Token type mismatch: expected '{expected}', got '{actual}'", status_code=401)
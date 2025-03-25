import secrets
from typing import Literal

def generate_otp_code(length: int = 6, type: Literal["numeric", "alphanumeric"] = "numeric") -> str:
    """
    Generate a secure OTP code.

    Args:
        length (int): Length of the OTP code (default: 6).
        type (Literal["numeric", "alphanumeric"]): Type of OTP code (default: "numeric").

    Returns:
        str: Generated OTP code.

    Raises:
        ValueError: If length is less than 4 or invalid type is provided.
    """
    if length < 4:
        raise ValueError("OTP length must be at least 4 characters for security")

    if type == "numeric":
        characters = "0123456789"
    elif type == "alphanumeric":
        characters = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
    else:
        raise ValueError("Invalid OTP type. Use 'numeric' or 'alphanumeric'")

    return ''.join(secrets.choice(characters) for _ in range(length))
# File: common/validators/email.py

import re

EMAIL_REGEX = re.compile(
    r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
)

def is_valid_email(email: str) -> bool:
    """
    Validates an email address using regex.

    Args:
        email (str): The input email address.

    Returns:
        bool: True if valid, False otherwise.
    """
    return bool(EMAIL_REGEX.fullmatch(email.strip()))

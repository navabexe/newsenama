# File: common/validators/phone.py

import phonenumbers


def validate_and_format_phone(phone: str) -> str:
    """
    Validates and formats a phone number to E.164 standard.

    Args:
        phone (str): The input phone number.

    Returns:
        str: Validated and formatted phone number.

    Raises:
        ValueError: If the phone number is invalid or unparseable.
    """
    try:
        parsed = phonenumbers.parse(phone)
        if not phonenumbers.is_valid_number(parsed):
            raise ValueError("Invalid phone number")
        return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
    except phonenumbers.NumberParseException:
        raise ValueError("Phone number must be in international format (e.g., +989123456789)")

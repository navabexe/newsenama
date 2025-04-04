# File: domain/notification/notification_services/builder.py

from typing import Literal
from common.translations.messages import get_message

SUPPORTED_LANGUAGES = ["fa", "en"]


async def build_notification_content(
    template_key: str,
    language: Literal["fa", "en"] = "fa",
    variables: dict = None
) -> dict:
    """
    Build localized notification content based on a template key.

    Args:
        template_key (str): Message key suffix, e.g. 'otp_requested'
        language (str): Target language (default: fa)
        variables (dict): Variables to inject into template

    Returns:
        dict: { title: str, body: str }
    """
    if language not in SUPPORTED_LANGUAGES:
        language = "fa"

    variables = variables or {}

    title_key = f"notification.{template_key}.title"
    body_key = f"notification.{template_key}.body"

    title = get_message(title_key, lang=language).format(**variables)
    body = get_message(body_key, lang=language).format(**variables)

    return {"title": title, "body": body}

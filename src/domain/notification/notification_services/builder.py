# File: domain/notification/notification_services/builder.py
from typing import Literal
from common.translations.messages import get_message
from common.logging.logger import log_info, log_error

SUPPORTED_LANGUAGES = ["fa", "en"]


async def build_notification_content(
        template_key: str,
        language: Literal["fa", "en"] = "fa",
        variables: dict = None
) -> dict:
    if language not in SUPPORTED_LANGUAGES:
        language = "fa"

    variables = variables or {}
    title_key = f"notification.{template_key}.title"
    body_key = f"notification.{template_key}.body"

    try:
        title = get_message(title_key, lang=language).format(**variables)
        # Provide default values for missing variables in body
        default_vars = {"phone": "unknown", "purpose": "general", "otp": "N/A"}
        body_vars = {**default_vars, **variables}  # Merge defaults with provided vars
        body = get_message(body_key, lang=language).format(**body_vars)
        log_info("Notification content built", extra={
            "template_key": template_key,
            "language": language,
            "variables": variables
        })
        return {"title": title, "body": body}
    except KeyError as e:
        log_error("Template key not found", extra={"template_key": template_key, "error": str(e)})
        raise ValueError(f"Template {template_key} missing variable {str(e)} for language {language}")
    except Exception as e:
        log_error("Failed to build notification content", extra={"error": str(e)})
        raise
import os
from common.logging.logger import log_info, log_error

# Read SMS panel key from .env
SMS_API_KEY = os.getenv("SMS_PANEL_KEY")
MOCK_SMS = os.getenv("MOCK_SMS", "true").lower() == "true"  # true = no actual sending

def send_sms(to: str, message: str) -> bool:
    if not SMS_API_KEY:
        log_error("SMS_PANEL_KEY not set in environment.")
        return False

    if MOCK_SMS:
        log_info("MOCK SMS sent", extra={"to": to, "message": message})
        return True

    try:
        # === Replace with actual panel logic here ===
        # Example placeholder:
        print(f"[SEND_SMS] To: {to} | Message: {message} | API_KEY: {SMS_API_KEY[:6]}...")

        # Example: requests.post(...) to real SMS provider
        log_info("SMS sent", extra={"to": to})
        return True

    except Exception as e:
        log_error("Failed to send SMS", extra={"to": to, "error": str(e)})
        return False

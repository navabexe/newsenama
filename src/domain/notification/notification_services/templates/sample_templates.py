# File: Root/src/domain/notification/notification_services/templates/sample_templates.py

# This file serves as a registry of sample keys used in notification translations.
# The actual messages should be defined in: common/translations/messages.py

# Example usage in builder.py:
#   get_message("notification.login_success.title", lang)
#   get_message("notification.login_success.body", lang)

TEMPLATE_KEYS = [
    "login_success",
    "otp_requested",
    "otp_verified",
    "account_deleted",
    "profile_completed",
    "admin_alert_login_failure"
]

# Corresponding keys in messages.py:
#   notification.login_success.title
#   notification.login_success.body
#   ... and so on

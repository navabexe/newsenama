import re

USERNAME_REGEX = re.compile(r"^[a-zA-Z0-9._]{3,30}$")

def is_valid_username(username: str) -> bool:
    if not username:
        return False

    if not USERNAME_REGEX.match(username):
        return False

    if username.startswith(('.', '_')) or username.endswith(('.', '_')):
        return False

    if '__' in username or '..' in username:
        return False

    return True

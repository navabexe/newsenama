import re

def is_valid_username(username: str) -> bool:
    return re.match(r"^[a-zA-Z0-9_.]{3,30}$", username) is not None

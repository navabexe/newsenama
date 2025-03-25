from fastapi import HTTPException

# Reserved or restricted usernames
RESERVED_USERNAMES = {
    "admin",
    "administrator",
    "root",
    "system",
    "support",
    "login",
    "logout",
    "auth",
    "superuser",
    "api",
    "v1",
    "me",
    "you",
    "username",
    "profile",
    "settings",
    "dashboard",
    "help",
    "search",
    "contact",
    "terms",
    "privacy",
    "about",
    "signup",
    "signin",
    "register",
    "vendor",
    "user",
}

def check_reserved_username(username: str):
    username_lower = username.lower()

    if username_lower in RESERVED_USERNAMES:
        raise HTTPException(
            status_code=400,
            detail="This username is reserved and cannot be used."
        )

    return True

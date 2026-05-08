import secrets


def new_session_id() -> str:
    """Cookie value for an audience participant. URL-safe, 24 bytes ~ 32 chars."""
    return secrets.token_urlsafe(24)


def new_presenter_token() -> str:
    """Secret room presenter token. 32 bytes ~ 43 chars URL-safe."""
    return secrets.token_urlsafe(32)

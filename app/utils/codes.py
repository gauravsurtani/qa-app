import secrets

# 26 chars: clear, unambiguous in print, no homoglyphs
ROOM_CODE_ALPHABET = "ACDEFGHJKLMNPQRTUVWXY3479"
ROOM_CODE_LENGTH = 6


def generate_room_code() -> str:
    return "".join(secrets.choice(ROOM_CODE_ALPHABET) for _ in range(ROOM_CODE_LENGTH))


def is_valid_room_code(code: str) -> bool:
    if len(code) != ROOM_CODE_LENGTH:
        return False
    return all(c in ROOM_CODE_ALPHABET for c in code)

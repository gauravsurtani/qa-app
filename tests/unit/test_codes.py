from app.utils.codes import (
    ROOM_CODE_ALPHABET,
    ROOM_CODE_LENGTH,
    generate_room_code,
    is_valid_room_code,
)
from app.utils.ids import new_presenter_token, new_session_id


def test_generated_code_has_correct_length():
    code = generate_room_code()
    assert len(code) == ROOM_CODE_LENGTH


def test_generated_code_only_uses_alphabet():
    for _ in range(100):
        code = generate_room_code()
        assert all(c in ROOM_CODE_ALPHABET for c in code)


def test_alphabet_excludes_ambiguous():
    for c in "01OIlB85S2Z":
        assert c not in ROOM_CODE_ALPHABET, f"{c} should not be in alphabet"


def test_codes_are_random():
    seen = {generate_room_code() for _ in range(1000)}
    # 25^6 = ~244M codes; collisions in 1000 should be vanishingly rare
    assert len(seen) > 990


def test_is_valid_room_code():
    assert is_valid_room_code("ACDEFG")
    assert not is_valid_room_code("abcdef")
    assert not is_valid_room_code("ACD")
    assert not is_valid_room_code("ACDEFGH")
    assert not is_valid_room_code("ACDEF0")  # 0 excluded


def test_session_id_unique():
    ids = {new_session_id() for _ in range(1000)}
    assert len(ids) == 1000


def test_presenter_token_unique_and_long():
    t = new_presenter_token()
    assert len(t) >= 40
    assert len({new_presenter_token() for _ in range(1000)}) == 1000

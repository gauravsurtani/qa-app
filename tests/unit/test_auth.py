from app.auth import constant_time_eq


def test_constant_time_eq_matches():
    assert constant_time_eq("abc", "abc") is True


def test_constant_time_eq_mismatch():
    assert constant_time_eq("abc", "abd") is False


def test_constant_time_eq_different_length():
    assert constant_time_eq("abc", "abcd") is False

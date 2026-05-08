from app.services.ratelimit import RateLimiter


def test_allows_up_to_max():
    rl = RateLimiter(max_actions=3, window_seconds=60)
    assert rl.allow("k", now=0)
    assert rl.allow("k", now=1)
    assert rl.allow("k", now=2)
    assert not rl.allow("k", now=3)


def test_window_slides():
    rl = RateLimiter(max_actions=2, window_seconds=10)
    assert rl.allow("k", now=0)
    assert rl.allow("k", now=5)
    assert not rl.allow("k", now=9)
    # both prior actions out of window now
    assert rl.allow("k", now=20)
    assert rl.allow("k", now=21)


def test_keys_are_isolated():
    rl = RateLimiter(max_actions=1, window_seconds=60)
    assert rl.allow("a", now=0)
    assert rl.allow("b", now=0)
    assert not rl.allow("a", now=1)
    assert not rl.allow("b", now=1)


def test_reset():
    rl = RateLimiter(max_actions=1, window_seconds=60)
    assert rl.allow("k", now=0)
    rl.reset("k")
    assert rl.allow("k", now=1)

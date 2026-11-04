from app.rate_limit import FixedWindowCounter


class FakeClock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


def test_counts_hits_per_key():
    counter = FixedWindowCounter(60, 5, clock=FakeClock())
    assert [counter.hit("a") for _ in range(3)] == [1, 2, 3]
    assert counter.hit("b") == 1
    assert counter.count("a") == 3
    assert counter.count("khong-co") == 0


def test_window_resets_after_it_expires():
    clock = FakeClock()
    counter = FixedWindowCounter(60, 5, clock=clock)
    for _ in range(4):
        counter.hit("a")
    clock.now += 61
    assert counter.count("a") == 0
    assert counter.hit("a") == 1


def test_retry_after_is_remaining_seconds():
    clock = FakeClock()
    counter = FixedWindowCounter(60, 5, clock=clock)
    counter.hit("a")
    clock.now += 20
    assert counter.retry_after("a") == 40


def test_expired_keys_are_purged_when_table_grows(monkeypatch):
    clock = FakeClock()
    counter = FixedWindowCounter(60, 5, clock=clock)
    monkeypatch.setattr(FixedWindowCounter, "_PURGE_ABOVE", 3)
    for i in range(4):
        counter.hit(f"ip{i}")
    clock.now += 61
    counter.hit("moi")
    assert list(counter._entries) == ["moi"]

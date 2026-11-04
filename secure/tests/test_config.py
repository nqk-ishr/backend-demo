import pytest

from app.config import ConfigError, load_config

BASE = {"DATABASE_URL": "postgres://user:pass@localhost:5432/shop"}


def test_refuses_to_start_without_jwt_secret():
    with pytest.raises(ConfigError, match="JWT_SECRET"):
        load_config(BASE)


def test_refuses_to_start_with_short_jwt_secret():
    with pytest.raises(ConfigError, match="32 ký tự"):
        load_config({**BASE, "JWT_SECRET": "secret"})


def test_refuses_to_start_without_database_url():
    with pytest.raises(ConfigError, match="DATABASE_URL"):
        load_config({"JWT_SECRET": "x" * 40})


def test_starts_normally_with_full_config():
    config = load_config({**BASE, "JWT_SECRET": "x" * 40})
    assert len(config.jwt_secret) == 40
    assert config.cors_origins == ["http://localhost:3002"]
    assert config.login_rate_max == 5


def test_cors_origins_are_split_and_trimmed():
    env = {**BASE, "JWT_SECRET": "x" * 40, "CORS_ORIGINS": "http://a.test, http://b.test ,"}
    assert load_config(env).cors_origins == ["http://a.test", "http://b.test"]

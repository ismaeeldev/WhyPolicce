import pytest

from app.core.config import normalize_database_url


@pytest.mark.parametrize(
    "raw",
    [
        "postgres://u:p@host/db",
        "postgresql://u:p@host/db",
        "postgresql+psycopg://u:p@host/db",
        "postgresql+psycopg2://u:p@host/db",
        '"postgres://u:p@host/db"',
    ],
)
def test_postgres_urls_use_psycopg2_driver(raw):
    assert normalize_database_url(raw) == "postgresql://u:p@host/db"


def test_other_urls_untouched():
    assert normalize_database_url("sqlite://") == "sqlite://"
    assert normalize_database_url("") == ""

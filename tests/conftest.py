from pathlib import Path

import pytest

from opds_server.app import create_app

FIXTURES_ROOT = Path(__file__).parent / "fixtures" / "books"


@pytest.fixture
def books_root() -> Path:
    return FIXTURES_ROOT


@pytest.fixture
def app(books_root):
    return create_app(books_root)


@pytest.fixture
def client(app):
    return app.test_client()

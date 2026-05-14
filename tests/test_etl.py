"""
Tests for the ETL pipeline.
All HTTP calls are mocked — no real network requests.
"""

import sqlite3
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from etl.db import get_connection, get_counts, init_db, upsert_comments, upsert_posts, upsert_users
from etl.__main__ import run

# ── Fixtures ──────────────────────────────────────────────────────────────────

USERS = [
    {
        "id": 1,
        "name": "John Doe",
        "username": "johndoe",
        "email": "john@example.com",
        "phone": "123",
        "website": "example.com",
        "company": {"name": "Acme"},
        "address": {"street": "Main St", "city": "Springfield"},
    }
]

POSTS = [
    {"id": 1, "userId": 1, "title": "Hello", "body": "World"}
]

COMMENTS = [
    {"id": 1, "postId": 1, "name": "Alice", "email": "alice@example.com", "body": "Nice post"}
]


@pytest.fixture
def db(tmp_path: Path) -> sqlite3.Connection:
    """In-memory-like DB in a temp file, initialized with schema."""
    db_path = tmp_path / "test.db"
    with get_connection(db_path) as conn:
        init_db(conn)
        yield conn


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    return tmp_path / "test.db"


# ── Unit tests: db ────────────────────────────────────────────────────────────

def test_upsert_users_inserts(db):
    n = upsert_users(db, USERS)
    assert n == 1
    row = db.execute("SELECT * FROM users WHERE id=1").fetchone()
    assert row["name"] == "John Doe"
    assert row["company"] == "Acme"
    assert row["address"] == "Main St, Springfield"


def test_upsert_users_idempotent(db):
    upsert_users(db, USERS)
    upsert_users(db, USERS)
    count = db.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    assert count == 1


def test_upsert_users_updates_existing(db):
    upsert_users(db, USERS)
    updated = [{**USERS[0], "name": "Jane Doe"}]
    upsert_users(db, updated)
    row = db.execute("SELECT name FROM users WHERE id=1").fetchone()
    assert row["name"] == "Jane Doe"


def test_upsert_posts_inserts(db):
    upsert_users(db, USERS)
    n = upsert_posts(db, POSTS)
    assert n == 1
    row = db.execute("SELECT * FROM posts WHERE id=1").fetchone()
    assert row["title"] == "Hello"


def test_upsert_posts_idempotent(db):
    upsert_users(db, USERS)
    upsert_posts(db, POSTS)
    upsert_posts(db, POSTS)
    count = db.execute("SELECT COUNT(*) FROM posts").fetchone()[0]
    assert count == 1


def test_upsert_comments_inserts(db):
    upsert_users(db, USERS)
    upsert_posts(db, POSTS)
    n = upsert_comments(db, COMMENTS)
    assert n == 1


def test_upsert_comments_idempotent(db):
    upsert_users(db, USERS)
    upsert_posts(db, POSTS)
    upsert_comments(db, COMMENTS)
    upsert_comments(db, COMMENTS)
    count = db.execute("SELECT COUNT(*) FROM comments").fetchone()[0]
    assert count == 1


def test_get_counts(db):
    upsert_users(db, USERS)
    upsert_posts(db, POSTS)
    upsert_comments(db, COMMENTS)
    counts = get_counts(db)
    assert counts == {"users": 1, "posts": 1, "comments": 1}


# ── Integration test: full run ─────────────────────────────────────────────────

def test_full_run_idempotent(db_path):
    """Two consecutive runs must produce the same row counts."""
    with patch("etl.__main__.fetch") as mock_fetch:
        mock_fetch.side_effect = lambda endpoint: {
            "/users": USERS,
            "/posts": POSTS,
            "/comments": COMMENTS,
        }[endpoint]

        run(db_path)
        run(db_path)

    with get_connection(db_path) as conn:
        counts = get_counts(conn)

    assert counts == {"users": 1, "posts": 1, "comments": 1}


def test_full_run_api_failure_exits(db_path):
    """If fetch fails, run() must call sys.exit(1)."""
    with patch("etl.__main__.fetch", side_effect=Exception("network error")):
        with pytest.raises(SystemExit) as exc_info:
            run(db_path)
    assert exc_info.value.code == 1

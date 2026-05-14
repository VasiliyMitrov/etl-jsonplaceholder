import logging
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

log = logging.getLogger(__name__)

SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS users (
    id        INTEGER PRIMARY KEY,
    name      TEXT    NOT NULL,
    username  TEXT    NOT NULL,
    email     TEXT    NOT NULL,
    phone     TEXT,
    website   TEXT,
    company   TEXT,
    address   TEXT
);

CREATE TABLE IF NOT EXISTS posts (
    id       INTEGER PRIMARY KEY,
    user_id  INTEGER NOT NULL,
    title    TEXT    NOT NULL,
    body     TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS comments (
    id       INTEGER PRIMARY KEY,
    post_id  INTEGER NOT NULL,
    name     TEXT    NOT NULL,
    email    TEXT    NOT NULL,
    body     TEXT,
    FOREIGN KEY (post_id) REFERENCES posts(id)
);
"""


@contextmanager
def get_connection(db_path: Path) -> Generator[sqlite3.Connection, None, None]:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    log.debug("Schema initialized")


def upsert_users(conn: sqlite3.Connection, rows: list[dict]) -> int:
    sql = """
        INSERT INTO users (id, name, username, email, phone, website, company, address)
        VALUES (:id, :name, :username, :email, :phone, :website, :company, :address)
        ON CONFLICT(id) DO UPDATE SET
            name     = excluded.name,
            username = excluded.username,
            email    = excluded.email,
            phone    = excluded.phone,
            website  = excluded.website,
            company  = excluded.company,
            address  = excluded.address
    """
    data = [
        {
            "id": r["id"],
            "name": r["name"],
            "username": r["username"],
            "email": r["email"],
            "phone": r.get("phone"),
            "website": r.get("website"),
            "company": r["company"]["name"],
            "address": f"{r['address']['street']}, {r['address']['city']}",
        }
        for r in rows
    ]
    conn.executemany(sql, data)
    return len(data)


def upsert_posts(conn: sqlite3.Connection, rows: list[dict]) -> int:
    sql = """
        INSERT INTO posts (id, user_id, title, body)
        VALUES (:id, :userId, :title, :body)
        ON CONFLICT(id) DO UPDATE SET
            user_id = excluded.user_id,
            title   = excluded.title,
            body    = excluded.body
    """
    conn.executemany(sql, rows)
    return len(rows)


def upsert_comments(conn: sqlite3.Connection, rows: list[dict]) -> int:
    sql = """
        INSERT INTO comments (id, post_id, name, email, body)
        VALUES (:id, :postId, :name, :email, :body)
        ON CONFLICT(id) DO UPDATE SET
            post_id = excluded.post_id,
            name    = excluded.name,
            email   = excluded.email,
            body    = excluded.body
    """
    conn.executemany(sql, rows)
    return len(rows)


def get_counts(conn: sqlite3.Connection) -> dict[str, int]:
    return {
        table: conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        for table in ("users", "posts", "comments")
    }

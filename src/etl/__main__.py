"""
ETL pipeline: JSONPlaceholder → SQLite

Usage:
    python -m etl [--db PATH]

Environment variables:
    API_BASE_URL      Base URL for the API  (default: https://jsonplaceholder.typicode.com)
    DB_PATH           Path to SQLite file   (default: data.db)
    REQUEST_TIMEOUT   HTTP timeout seconds  (default: 30)
"""

import argparse
import logging
import sys
from pathlib import Path

from .config import DB_PATH, ENDPOINTS
from .db import get_connection, get_counts, init_db, upsert_comments, upsert_posts, upsert_users
from .fetcher import fetch

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Load JSONPlaceholder data into SQLite")
    parser.add_argument(
        "--db",
        type=Path,
        default=DB_PATH,
        help="Path to SQLite database file (default: data.db)",
    )
    return parser.parse_args()


def run(db_path: Path) -> None:
    log.info("Starting ETL pipeline → %s", db_path)

    try:
        users = fetch(ENDPOINTS["users"])
        posts = fetch(ENDPOINTS["posts"])
        comments = fetch(ENDPOINTS["comments"])
    except Exception as e:
        log.error("Failed to fetch data: %s", e)
        sys.exit(1)

    try:
        with get_connection(db_path) as conn:
            init_db(conn)

            counts_before = get_counts(conn)

            n_users = upsert_users(conn, users)
            n_posts = upsert_posts(conn, posts)
            n_comments = upsert_comments(conn, comments)

            counts_after = get_counts(conn)

    except Exception as e:
        log.error("Database error: %s", e)
        sys.exit(1)

    log.info("ETL complete. Summary:")
    log.info("  %-10s  fetched=%d  db_before=%d  db_after=%d", "users",    n_users,    counts_before["users"],    counts_after["users"])
    log.info("  %-10s  fetched=%d  db_before=%d  db_after=%d", "posts",    n_posts,    counts_before["posts"],    counts_after["posts"])
    log.info("  %-10s  fetched=%d  db_before=%d  db_after=%d", "comments", n_comments, counts_before["comments"], counts_after["comments"])


def main() -> None:
    args = parse_args()
    run(args.db)


if __name__ == "__main__":
    main()

from pathlib import Path
import os

API_BASE_URL: str = os.getenv("API_BASE_URL", "https://jsonplaceholder.typicode.com")
DB_PATH: Path = Path(os.getenv("DB_PATH", "data.db"))
REQUEST_TIMEOUT: int = int(os.getenv("REQUEST_TIMEOUT", "30"))

ENDPOINTS: dict[str, str] = {
    "users": "/users",
    "posts": "/posts",
    "comments": "/comments",
}

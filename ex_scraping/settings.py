from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATABASES = {
    "sync": {
        "drivername": "sqlite",
        "database": f"{BASE_DIR}/db/database.db",
    },
    "a_sync": {
        "drivername": "sqlite+aiosqlite",
        "database": f"{BASE_DIR}/db/database.db",
    },
}
API_OPTIONS = {
    "get_data": {
        "url": "http://localhost:8060/api/",
        "timeout": 15.0,
    },
    "post_data": {
        "url": "http://localhost:8000/api/",
        "timeout": 7.0,
    },
}
LOG_OPTIONS = {"directory_path": f"{BASE_DIR}/log/"}

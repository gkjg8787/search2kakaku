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

SELENIUM_OPTIONS = {
    "REMOTE_URL": "http://selenium:4444/wd/hub",
}
SOFMAP_OPTIONS = {
    "selenium": {
        "PAGE_LOAD_TIMEOUT": 30,
        "TAG_WAIT_TIMEOUT": 15,
    }
}
API_SENDING_OPTIONS = {
    "urls": {
        "base_url": "http://localhost:8000/api/",
    }
}
API_OPTIONS = {
    "get_data": {
        "url": "http://localhost:8060/api/",
    },
    "post_data": {
        "url": "http://localhost:8000/api/",
    },
}
LOG_OPTIONS = {"directory_path": f"{BASE_DIR}/log/"}

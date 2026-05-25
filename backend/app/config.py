import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
UPLOAD_DIR = BASE_DIR / "data" / "uploads"

MAX_UPLOAD_SIZE = 500 * 1024 * 1024  # 500MB
ALLOWED_EXTENSIONS = {".csv", ".xlsx", ".xls"}
SAMPLE_DATA_DIR = BASE_DIR / "app" / "sample_data"
DB_PATH = BASE_DIR / "data" / "sessions.db"

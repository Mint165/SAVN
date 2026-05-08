import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import declarative_base, sessionmaker

load_dotenv()

DEFAULT_SQLITE_URL = "sqlite:///./heartbits.db"


def normalize_database_url(raw_url: str | None) -> str:
    if not raw_url:
        return DEFAULT_SQLITE_URL

    url = raw_url.strip()
    if not url:
        return DEFAULT_SQLITE_URL

    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)

    if "[YOUR_PASSWORD]" in url or "YOUR_PASSWORD" in url:
        print("DATABASE_URL still contains a placeholder password. Falling back to SQLite.")
        return DEFAULT_SQLITE_URL

    if not url.startswith("postgresql"):
        return url

    try:
        parsed = make_url(url)
    except Exception:
        print("DATABASE_URL is malformed. Falling back to SQLite.")
        return DEFAULT_SQLITE_URL

    if not parsed.username or not parsed.password or not parsed.host:
        print("DATABASE_URL is incomplete. Falling back to SQLite.")
        return DEFAULT_SQLITE_URL

    return url


SQLALCHEMY_DATABASE_URL = normalize_database_url(os.getenv("DATABASE_URL"))

if SQLALCHEMY_DATABASE_URL.startswith("postgresql"):
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        pool_size=5,
        max_overflow=10,
        pool_timeout=30,
        pool_recycle=1800,
        pool_pre_ping=True,
    )
else:
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        connect_args={"check_same_thread": False},
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

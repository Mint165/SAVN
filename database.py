from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

import os
# On Vercel, the filesystem is read-only except for /tmp
if os.environ.get("VERCEL"):
    SQLALCHEMY_DATABASE_URL = "sqlite:////tmp/heartbits.db"
else:
    SQLALCHEMY_DATABASE_URL = "sqlite:///./heartbits.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

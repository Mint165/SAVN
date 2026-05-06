import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

load_dotenv()

# Lấy URL kết nối từ biến môi trường (Ưu tiên Supabase Postgres)
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL")

# Kiểm tra môi trường để quyết định database
if not SQLALCHEMY_DATABASE_URL:
    if os.environ.get("VERCEL"):
        # Trên Vercel bắt buộc phải có DATABASE_URL để kết nối Supabase
        raise RuntimeError("DATABASE_URL environment variable is missing on Vercel!")
    else:
        # Fallback về SQLite khi phát triển ở máy cá nhân (Local) nếu chưa config .env
        SQLALCHEMY_DATABASE_URL = "sqlite:///./heartbits.db"

# CHUẨN HÓA URL CHO SUPABASE
if SQLALCHEMY_DATABASE_URL.startswith("postgres://"):
    # SQLAlchemy yêu cầu postgresql:// (có chữ l)
    SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Fix lỗi Prepared Statements khi dùng cổng 6543 (Transaction Mode)
if ":6543" in SQLALCHEMY_DATABASE_URL:
    if "?" in SQLALCHEMY_DATABASE_URL:
        if "prepared_statements" not in SQLALCHEMY_DATABASE_URL:
            SQLALCHEMY_DATABASE_URL += "&prepared_statements=false"
    else:
        SQLALCHEMY_DATABASE_URL += "?prepared_statements=false"

# Cấu hình Engine dựa trên loại Database
if "postgresql" in SQLALCHEMY_DATABASE_URL:
    # Cấu hình tối ưu cho Supabase Postgres
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        pool_size=5,
        max_overflow=10,
        pool_timeout=30,
        pool_recycle=1800,
    )
else:
    # Cấu hình cho SQLite local
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL, 
        connect_args={"check_same_thread": False}
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

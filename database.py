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

# Cấu hình Engine dựa trên loại Database
if SQLALCHEMY_DATABASE_URL.startswith("postgresql"):
    # Cấu hình tối ưu cho Supabase Postgres
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        pool_size=5,             # Duy trì 5 kết nối sẵn sàng
        max_overflow=10,         # Cho phép mở rộng tối đa 10 kết nối khi quá tải
        pool_timeout=30,         # Đợi tối đa 30 giây để lấy kết nối từ pool
        pool_recycle=1800,       # Tự động làm mới kết nối sau mỗi 30 phút
    )
else:
    # Cấu hình cho SQLite local
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL, 
        connect_args={"check_same_thread": False}
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

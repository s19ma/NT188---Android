from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from app.core.config import settings


# Base class cho tất cả SQLAlchemy Models
class Base(DeclarativeBase):
    pass


# Engine kết nối đến Neon PostgreSQL qua Pooler
engine = create_engine(
    settings.database_url,
    connect_args={"connect_timeout": 8},
    pool_pre_ping=True,   # Kiểm tra kết nối trước khi dùng
    pool_size=5,          # Số kết nối tối đa trong pool
    max_overflow=10,      # Cho phép thêm tối đa 10 kết nối vượt pool_size
    echo=False,           # Đặt True để in SQL ra terminal khi debug
)

# Session factory
SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
)


# Dependency inject vào FastAPI route
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

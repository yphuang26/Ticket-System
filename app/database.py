from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .models import Base

# 資料庫連線字串 (對應 docker-compose 中的設定)
DATABASE_URL = "postgresql://postgres:postgres_pass@db:5432/ticket_db"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    # 自動建立資料表
    Base.metadata.create_all(bind=engine)
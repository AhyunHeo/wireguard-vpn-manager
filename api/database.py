from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# 데이터베이스 URL
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql://vpn:vpnpass@postgres:5432/vpndb"
)

# SQLAlchemy 엔진 생성
engine = create_engine(DATABASE_URL)

# 세션 생성
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base 모델
Base = declarative_base()
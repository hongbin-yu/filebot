from sqlalchemy import create_engine, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

load_dotenv()

# 数据库配置
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./filebot.db"
)

# SQLite特定配置
connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

# 创建SQLAlchemy引擎
engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    echo=False  # 设置为True查看SQL日志
)

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 声明基类
Base = declarative_base()


def get_db():
    """依赖注入数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """初始化数据库，创建所有表"""
    Base.metadata.create_all(bind=engine)


def drop_db():
    """删除所有表（仅用于测试）"""
    Base.metadata.drop_all(bind=engine)
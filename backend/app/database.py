from sqlalchemy.orm import sessionmaker,DeclarativeBase,Mapped,mapped_column
from sqlalchemy import create_engine,DateTime
from app.config import settings
from datetime import datetime

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,   # 取连接前先探活，避免 MySQL 长连接断开后报错
    pool_recycle=3600,    # 连接每小时回收一次
)

SessionLocal = sessionmaker(
    bind = engine,autoflush=False
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class Base(DeclarativeBase):
    id: Mapped[int] = mapped_column(primary_key=True,autoincrement=True,comment="主键Id")
    create_time:Mapped[datetime]  = mapped_column(DateTime,default=datetime.now,comment="创建时间")
    updatetime:Mapped[datetime] = mapped_column(DateTime,default=datetime.now,onupdate=datetime.now,comment="更新时间" )
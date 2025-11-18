from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.declarative import declarative_base
from contextlib import contextmanager
import os
from typing import Generator
from pathlib import Path

# Ensure the database directory exists
if os.getenv("DOCKER_ENV"):
    # In Docker, use a simple relative path
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./projects.db")
else:
    # Local development
    db_path = Path(__file__).parent / "projects.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
    pool_size=10,
    max_overflow=20
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_context():
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def init_db():
    from models import Base
    Base.metadata.create_all(bind=engine)
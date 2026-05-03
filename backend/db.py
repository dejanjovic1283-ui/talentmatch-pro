import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

# Load environment variables before the database engine is created.
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./talentmatch.db")

# SQLite needs this flag for local threaded development.
connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""


def get_db():
    """Yield a database session for request-scoped usage."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

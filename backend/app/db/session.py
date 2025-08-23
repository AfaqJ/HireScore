from sqlmodel import SQLModel, create_engine, Session
from app.core.config import settings

# Using SQLite (local file)
engine = create_engine(settings.db_url, echo=True)

def init_db():
    """Create tables if they don't exist yet."""
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session

from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    db_url: str = "sqlite:///./app.db"   # SQLite file in project root
    class Config:
        env_file = ".env"

settings = Settings()

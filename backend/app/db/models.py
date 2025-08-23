from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime

class Job(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    jd_text: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Resume(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    text: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

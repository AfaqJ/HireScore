from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
from app.schemas.common import ResumeIn
from app.db.session import get_session
from app.db import crud

router = APIRouter(prefix="/ingest", tags=["ingest"])

@router.post("/resume")
def ingest_resume(payload: ResumeIn, session: Session = Depends(get_session)):
    text = (payload.text or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="resume text is empty")
    resume = crud.create_resume(session, text)
    return {"resume_id": resume.id}

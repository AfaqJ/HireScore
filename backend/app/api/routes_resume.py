from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlmodel import Session
from app.schemas.common import ResumeIn
from app.db.session import get_session
from app.db import crud
from app.utils.file import parse_file

router = APIRouter(prefix="/ingest", tags=["ingest"])

@router.post("/resume")
def ingest_resume(payload: ResumeIn, session: Session = Depends(get_session)):
    text = (payload.text or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="resume text is empty")
    resume = crud.create_resume(session, text)
    return {"resume_id": resume.id}

@router.post("/resume-file")
async def ingest_resume_file(file: UploadFile = File(...), session: Session = Depends(get_session)):
    name = file.filename or "upload"
    data = await file.read()
    if len(data) == 0:
        raise HTTPException(status_code=400, detail="empty file")
    if len(data) > 5 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="file too large (max 5 MB)")
    text = parse_file(name, data).strip()
    if not text:
        raise HTTPException(status_code=422, detail="could not extract text from file")
    resume = crud.create_resume(session, text)
    return {"resume_id": resume.id, "chars": len(text)}

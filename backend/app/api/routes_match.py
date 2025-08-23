from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
from app.schemas.common import MatchIn
from app.db.session import get_session
from app.db import crud

router = APIRouter(tags=["match"])

@router.post("/match")
def match(req: MatchIn, session: Session = Depends(get_session)):
    job = crud.get_job(session, req.job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")

    if req.resume_id is None:
        return {"cv_match": {"score": 0, "gaps": ["no resume provided"]}}

    resume = crud.get_resume(session, req.resume_id)
    if not resume:
        raise HTTPException(status_code=404, detail="resume not found")

    # placeholder until we add AI alignment
    return {
        "cv_match": {
            "score": 42.0,
            "gaps": ["(placeholder, AI coming next)"],
            "job_title": job.title,
            "resume_chars": len(resume.text)
        }
    }

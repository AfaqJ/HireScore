from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
from app.schemas.common import MatchIn
from app.db.session import get_session
from app.db import crud
from app.services.aligner import extract_jd_skills, score_resume_against_skills

router = APIRouter(tags=["match"])

@router.post("/match")
def match(req: MatchIn, session: Session = Depends(get_session)):
    job = crud.get_job(session, req.job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")

    collection_name = f"jd_{job.id}"
    skills = extract_jd_skills(collection_name)
    if not skills:
        # either JD was empty or indexing failed (rare). Return safe fallback.
        skills = [{"skill": "communication", "importance": 3, "must_have": False}]

    result = {"cv_match": None}

    if req.resume_id is not None:
        resume = crud.get_resume(session, req.resume_id)
        if not resume:
            raise HTTPException(status_code=404, detail="resume not found")
        cv_res = score_resume_against_skills(resume.text, skills)
        result["cv_match"] = cv_res

    return result

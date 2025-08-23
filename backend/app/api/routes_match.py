from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
from app.schemas.common import MatchIn
from app.db.session import get_session
from app.db import crud
from app.services.aligner import extract_jd_skills_langchain, score_resume_against_skills

router = APIRouter(tags=["match"])

def fit_badge(cv_score: float | None, quiz_score: float | None):
    if cv_score is None and quiz_score is None:
        return None, "Provide a resume and/or complete a quiz."
    if cv_score is not None and quiz_score is not None:
        if cv_score >= 70 and quiz_score >= 70:
            return "strong_fit", "✅ You’re a strong fit for this role."
        if cv_score >= 70 and quiz_score < 70:
            return "improve_quiz", "⚡ Your CV matches, improve interview readiness."
        if cv_score < 70 and quiz_score >= 70:
            return "improve_cv", "⚡ Good interview showing, strengthen your CV alignment."
        return "needs_work", "⚠️ Improve both CV alignment and interview responses."
    if cv_score is not None:
        return ("cv_only_strong", "✅ Solid CV match.") if cv_score >= 70 else ("cv_only_gaps", "⚠️ Address missing skills.")
    if quiz_score is not None:
        return ("quiz_only_strong", "✅ Strong quiz performance.") if quiz_score >= 70 else ("quiz_only_gaps", "⚠️ Improve interview answers.")
    return None, ""

@router.post("/match")
def match(req: MatchIn, session: Session = Depends(get_session)):
    job = crud.get_job(session, req.job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")

    # LangChain-based skill extraction
    skills = extract_jd_skills_langchain(job.id)
    if not skills:
        skills = [{"skill": "communication", "importance": 3, "must_have": False}]

    result: dict = {"cv_match": None, "quiz_match": None, "combined": None, "badge": None, "message": ""}

    # CV scoring
    cv_score = None
    if req.resume_id is not None:
        resume = crud.get_resume(session, req.resume_id)
        if not resume:
            raise HTTPException(status_code=404, detail="resume not found")
        cv_res = score_resume_against_skills(resume.text, skills)
        result["cv_match"] = cv_res
        cv_score = cv_res["score"]

    # Quiz score (from DB)
    quiz_score = None
    if req.quiz_id is not None:
        quiz = crud.get_quiz(session, req.quiz_id)
        if not quiz:
            raise HTTPException(status_code=404, detail="quiz not found")
        quiz_score = crud.quiz_overall(session, req.quiz_id)
        result["quiz_match"] = {"score": quiz_score}

    # Combined + badge
    if cv_score is not None and quiz_score is not None:
        result["combined"] = round((cv_score + quiz_score) / 2, 1)

    badge, msg = fit_badge(cv_score, quiz_score)
    result["badge"] = badge
    result["message"] = msg
    if cv_score is not None and result["cv_match"] and result["cv_match"].get("gaps"):
        result["recommend"] = {"top_cv_gaps": result["cv_match"]["gaps"][:3]}

    return result

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
from app.db.session import get_session
from app.db import crud
from app.schemas.common import QuizStartIn, QuizStartOut, QuizGradeIn, QuizGradeOut
from app.services.quiz import make_questions, grade_one

router = APIRouter(prefix="/quiz", tags=["quiz"])

@router.post("/start", response_model=QuizStartOut)
def quiz_start(req: QuizStartIn, session: Session = Depends(get_session)):
    job = crud.get_job(session, req.job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    quiz = crud.create_quiz(session, job.id)
    qs = make_questions(job.id, n=req.n)
    rows = crud.add_questions(session, quiz.id, qs)
    return {"quiz_id": quiz.id, "questions": [{"id": r.id, "idx": r.idx, "text": r.text} for r in rows]}

@router.post("/grade", response_model=QuizGradeOut)
def quiz_grade(req: QuizGradeIn, session: Session = Depends(get_session)):
    quiz = crud.get_quiz(session, req.quiz_id)
    if not quiz:
        raise HTTPException(status_code=404, detail="quiz not found")
    answers_map = {a["question_id"]: a["text"] for a in req.answers}
    crud.add_answers(session, req.quiz_id, answers_map)

    questions = crud.list_questions(session, req.quiz_id)
    if not questions:
        raise HTTPException(status_code=400, detail="no questions for this quiz")

    feedback = []
    for q in questions:
        raw = answers_map.get(q.id, "")
        g = grade_one(quiz.job_id, q.text, raw)
        a_row = crud.get_answer_for_question(session, req.quiz_id, q.id)
        if a_row:
            crud.update_answer_grade(
                session, a_row.id, g["accuracy"], g["completeness"], g["communication"], g["score_pct"], g["tip"]
            )
        feedback.append({"question_id": q.id, "score": g["score_pct"], "tip": g["tip"]})

    overall = crud.quiz_overall(session, req.quiz_id)
    return {"overall": overall, "feedback": feedback}

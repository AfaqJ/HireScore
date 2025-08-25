from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
from app.db.session import get_session
from app.db import crud
from app.schemas.common import QuizStartIn, QuizStartOut, QuizGradeIn, QuizGradeOut
from app.services.quiz import make_questions, grade_many

router = APIRouter(prefix="/quiz", tags=["quiz"])

@router.post("/start", response_model=QuizStartOut)
def quiz_start(req: QuizStartIn, session: Session = Depends(get_session)):
    job = crud.get_job(session, req.job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")

    quiz = crud.create_quiz(session, job.id)
    qs = make_questions(job.id, n=req.n, session=session)
    rows = crud.add_questions(session, quiz.id, qs)

    return {
        "quiz_id": quiz.id,
        "questions": [{"id": r.id, "idx": r.idx, "text": r.text} for r in rows],
    }


@router.post("/grade", response_model=QuizGradeOut)
def quiz_grade(req: QuizGradeIn, session: Session = Depends(get_session)):
    quiz = crud.get_quiz(session, req.quiz_id)
    if not quiz:
        raise HTTPException(status_code=404, detail="quiz not found")

    # Persist raw answers first (existing behavior)
    answers_map = {a["question_id"]: a["text"] for a in req.answers}
    crud.add_answers(session, req.quiz_id, answers_map)

    # Load questions in creation order
    questions = crud.list_questions(session, req.quiz_id)
    if not questions:
        raise HTTPException(status_code=400, detail="no questions for this quiz")

    # Build ordered (question_text, answer_text) pairs
    qas = [(q.text, answers_map.get(q.id, "")) for q in questions]

    # Batch grade & summarize (returns overall, feedback, quiz_match, per)
    summary = grade_many(quiz.job_id, qas, session)

    # Persist per-question grades
    for i, q in enumerate(questions):
        per = summary["per"][i]
        a_row = crud.get_answer_for_question(session, req.quiz_id, q.id)
        if a_row:
            crud.update_answer_grade(
                session,
                a_row.id,
                per["accuracy"],
                per["completeness"],
                per["communication"],
                per["score_pct"],
                per.get("tip", ""),
            )

    # Use computed overall (avoids extra DB read)
    overall = summary["overall"]

    # Build response: legacy fields + new quiz_match block
    resp = {
        "overall": overall,
        "feedback": [
            {
                "question_id": q.id,
                "score": summary["feedback"][i]["score"],
                "tip": summary["feedback"][i].get("tip", ""),
            }
            for i, q in enumerate(questions)
        ],
        "quiz_match": summary.get("quiz_match"),
    }
    return resp

from sqlmodel import Session, select
from app.db.models import Job, Resume, Quiz, Question, Answer

# --- Job ---
def create_job(session: Session, title: str, jd_text: str) -> Job:
    job = Job(title=title, jd_text=jd_text)
    session.add(job)
    session.commit()
    session.refresh(job)
    return job

def get_job(session: Session, job_id: int) -> Job | None:
    return session.get(Job, job_id)

# --- Resume ---
def create_resume(session: Session, text: str) -> Resume:
    resume = Resume(text=text)
    session.add(resume)
    session.commit()
    session.refresh(resume)
    return resume

def get_resume(session: Session, resume_id: int) -> Resume | None:
    return session.get(Resume, resume_id)

# --- Quiz ---
def create_quiz(session: Session, job_id: int) -> Quiz:
    q = Quiz(job_id=job_id)
    session.add(q)
    session.commit()
    session.refresh(q)
    return q

def get_quiz(session: Session, quiz_id: int) -> Quiz | None:
    return session.get(Quiz, quiz_id)

def add_questions(session: Session, quiz_id: int, questions: list[str]) -> list[Question]:
    rows: list[Question] = []
    for i, text in enumerate(questions):
        row = Question(quiz_id=quiz_id, idx=i, text=text)
        session.add(row)
        rows.append(row)
    session.commit()
    for r in rows:
        session.refresh(r)
    return rows

def list_questions(session: Session, quiz_id: int) -> list[Question]:
    stmt = select(Question).where(Question.quiz_id == quiz_id).order_by(Question.idx)
    return session.exec(stmt).all()

def add_answers(session: Session, quiz_id: int, answers: dict[int, str]) -> list[Answer]:
    rows: list[Answer] = []
    for qid, text in answers.items():
        row = Answer(quiz_id=quiz_id, question_id=qid, text=text)
        session.add(row)
        rows.append(row)
    session.commit()
    for r in rows:
        session.refresh(r)
    return rows

def get_answer_for_question(session: Session, quiz_id: int, question_id: int) -> Answer | None:
    stmt = select(Answer).where(
        Answer.quiz_id == quiz_id, Answer.question_id == question_id
    ).order_by(Answer.id.desc())
    return session.exec(stmt).first()

def update_answer_grade(
    session: Session, answer_id: int, acc: int, comp: int, comm: int, pct: int, tip: str
) -> Answer | None:
    row = session.get(Answer, answer_id)
    if not row:
        return None
    row.accuracy = acc
    row.completeness = comp
    row.communication = comm
    row.score_pct = pct
    row.tip = tip
    session.add(row)
    session.commit()
    session.refresh(row)
    return row

def quiz_overall(session: Session, quiz_id: int) -> int:
    stmt = select(Answer).where(Answer.quiz_id == quiz_id)
    rows = session.exec(stmt).all()
    if not rows:
        return 0
    vals = [a.score_pct or 0 for a in rows]
    return round(sum(vals) / len(vals))

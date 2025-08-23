from sqlmodel import Session, select
from app.db.models import Job, Resume

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



def create_quiz(session: Session, job_id: int) -> Quiz:
    q = Quiz(job_id=job_id)
    session.add(q); session.commit(); session.refresh(q)
    return q

def add_questions(session: Session, quiz_id: int, questions: list[str]) -> list[Question]:
    items = []
    for i, text in enumerate(questions):
        item = Question(quiz_id=quiz_id, idx=i, text=text)
        session.add(item); items.append(item)
    session.commit()
    for it in items: session.refresh(it)
    return items

def list_questions(session: Session, quiz_id: int) -> list[Question]:
    return session.exec(select(Question).where(Question.quiz_id == quiz_id).order_by(Question.idx)).all()

def add_answers(session: Session, quiz_id: int, answers: dict[int, str]) -> list[Answer]:
    """answers: {question_id: text}"""
    items = []
    for qid, text in answers.items():
        a = Answer(quiz_id=quiz_id, question_id=qid, text=text)
        session.add(a); items.append(a)
    session.commit()
    for it in items: session.refresh(it)
    return items

def update_answer_grade(session: Session, answer_id: int, acc:int, comp:int, comm:int, pct:int, tip:str):
    a = session.get(Answer, answer_id)
    if not a: return
    a.accuracy = acc; a.completeness = comp; a.communication = comm
    a.score_pct = pct; a.tip = tip
    session.add(a); session.commit(); session.refresh(a)
    return a

def quiz_overall(session: Session, quiz_id:int) -> int:
    rows = session.exec(select(Answer).where(Answer.quiz_id == quiz_id)).all()
    if not rows: return 0
    vals = [a.score_pct or 0 for a in rows]
    return round(sum(vals)/len(vals))
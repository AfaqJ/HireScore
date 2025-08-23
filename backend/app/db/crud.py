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

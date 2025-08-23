from pydantic import BaseModel

class JDIn(BaseModel):
    title: str
    jd_text: str

class ResumeIn(BaseModel):
    text: str  # we'll add file upload later; text is enough to start

class MatchIn(BaseModel):
    job_id: int
    resume_id: int | None = None
    mode: str = "cv_only"   # "cv_only" | "quiz_only" | "both" (quiz later)

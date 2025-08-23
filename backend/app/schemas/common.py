from pydantic import BaseModel
from typing import List, Dict

class JDIn(BaseModel):
    title: str
    jd_text: str

class ResumeIn(BaseModel):
    text: str  # we'll add file upload later; text is enough to start

class MatchIn(BaseModel):
    job_id: int
    resume_id: int | None = None
    quiz_id: int | None = None     # NEW
    mode: str = "cv_only"          # kept for compatibility



class QuizStartIn(BaseModel):
    job_id: int
    n: int = 5

class QuizStartOut(BaseModel):
    quiz_id: int
    questions: List[Dict]  # [{id, idx, text}]

class QuizGradeIn(BaseModel):
    quiz_id: int
    answers: List[Dict]    # [{question_id, text}]

class QuizGradeOut(BaseModel):
    overall: int
    feedback: List[Dict]   # [{question_id, score, tip}]
from pydantic import BaseModel
from typing import List, Dict, Optional

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


# ---- NEW structures ----
class QuizFeedbackItem(BaseModel):
    question_id: int
    score: float
    tip: str

class QuizMatch(BaseModel):
    score: float
    gaps: List[str] = []
    matched: int
    total_skills: int
    message: Optional[str] = None

class QuizGradeOut(BaseModel):
    overall: float
    feedback: List[QuizFeedbackItem]
    quiz_match: Optional[QuizMatch] = None

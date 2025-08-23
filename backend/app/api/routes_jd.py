from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
from app.schemas.common import JDIn
from app.db.session import get_session
from app.db import crud
from app.services.lc import index_job_description

router = APIRouter(prefix="/ingest", tags=["ingest"])

@router.post("/jd")
def ingest_jd(payload: JDIn, session: Session = Depends(get_session)):
    if not payload.jd_text.strip():
        raise HTTPException(status_code=400, detail="jd_text is empty")
    job = crud.create_job(session, payload.title, payload.jd_text)
    index_job_description(job.id, payload.jd_text)  # <- LangChain vector store
    return {"job_id": job.id}

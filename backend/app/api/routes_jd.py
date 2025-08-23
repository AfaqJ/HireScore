from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
from app.schemas.common import JDIn
from app.db.session import get_session
from app.db import crud
from app.services.retriever import index_jd

router = APIRouter(prefix="/ingest", tags=["ingest"])

@router.post("/jd")
def ingest_jd(payload: JDIn, session: Session = Depends(get_session)):
    if not payload.jd_text.strip():
        raise HTTPException(status_code=400, detail="jd_text is empty")
    job = crud.create_job(session, payload.title, payload.jd_text)
    # NEW: index JD into chroma using a predictable name
    collection_name = f"jd_{job.id}"
    index_jd(collection_name, payload.jd_text)
    return {"job_id": job.id}

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
    try:
        job = crud.create_job(session, payload.title, payload.jd_text)
        index_job_description(job.id, payload.jd_text)
        print(f"Returning job_id={job.id}")

        # embeddings
        return {"job_id": job.id}
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

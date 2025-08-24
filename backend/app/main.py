from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
app = FastAPI(title="JobFit AI Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # allow all origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.api.routes_jd import router as jd_router
from app.api.routes_resume import router as resume_router
from app.api.routes_match import router as match_router
from app.db.session import init_db
from app.api.routes_quiz import router as quiz_router

# init DB
@app.on_event("startup")
def on_startup():
    init_db()



@app.get("/")
def root():
    return {"ok": True, "service": "jobfit-ai"}

@app.get("/health")
def health():
    return {"status": "ok"}

app.include_router(jd_router)
app.include_router(resume_router)
app.include_router(match_router)
app.include_router(quiz_router)

# app/services/quiz.py
from typing import List, Dict
import json, re
from app.services.lc import get_retriever, make_quiz_chain, make_grade_chain

def _parse(text: str):
    t = text.strip()
    t = re.sub(r"^```json|```$", "", t, flags=re.I|re.M).strip()
    try:
        return json.loads(t)
    except Exception:
        return []

def make_questions(job_id: int, n: int = 5) -> List[str]:
    retriever = get_retriever(job_id, k=6)
    docs = retriever.get_relevant_documents("core responsibilities and required skills")
    ctx = "\n\n".join([d.page_content for d in docs])
    chain = make_quiz_chain()
    raw = chain.invoke({"context": ctx, "n": n})
    out = _parse(raw.content if hasattr(raw, "content") else str(raw))
    qs = [o.get("q","").strip() for o in out if isinstance(o, dict) and o.get("q")]
    if len(qs) < n:
        qs += ["Describe a project using the core tools from this JD."] * (n - len(qs))
    return qs[:n]

def grade_one(job_id: int, question: str, answer: str) -> Dict:
    retriever = get_retriever(job_id, k=4)
    docs = retriever.get_relevant_documents(question)
    ctx = "\n\n".join([d.page_content for d in docs])
    chain = make_grade_chain()
    raw = chain.invoke({"context": ctx, "question": question, "answer": answer})
    g = _parse(raw.content if hasattr(raw, "content") else str(raw))
    g = (g[0] if isinstance(g, list) and g else g) or {}
    acc = int(g.get("accuracy", 0))
    comp = int(g.get("completeness", 0))
    comm = int(g.get("communication", 0))
    acc = max(0, min(5, acc)); comp = max(0, min(5, comp)); comm = max(0, min(5, comm))
    pct = round((acc + comp + comm) / 15 * 100)
    return {"accuracy": acc, "completeness": comp, "communication": comm, "score_pct": pct, "tip": g.get("tip", "")}

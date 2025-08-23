# app/services/aligner.py
from typing import List, Dict
import json, re
from app.services.lc import get_retriever, make_skill_chain

def _parse_json(text: str):
    # tolerant JSON cleanup (handles fenced code blocks)
    t = text.strip()
    t = re.sub(r"^```json|```$", "", t, flags=re.I|re.M).strip()
    try:
        return json.loads(t)
    except Exception:
        return []

def extract_jd_skills_langchain(job_id: int, top_k_ctx: int = 6) -> List[Dict]:
    retriever = get_retriever(job_id, k=top_k_ctx)
    # pull context by asking a general query
    docs = retriever.get_relevant_documents("key skills, requirements, and tech stack")
    ctx = "\n\n".join([d.page_content for d in docs])
    chain = make_skill_chain()
    raw = chain.invoke(ctx)  # llm returns a string
    items = _parse_json(raw.content if hasattr(raw, "content") else str(raw))

    # dedupe + clamp
    seen = {}
    for it in items:
        s = str(it.get("skill","")).strip()
        if not s: 
            continue
        key = s.casefold()
        imp = int(it.get("importance", 3))
        mh  = bool(it.get("must_have", False))
        imp = min(max(imp,1),5)
        if key not in seen:
            seen[key] = {"skill": s, "importance": imp, "must_have": mh}
        else:
            seen[key]["importance"] = max(seen[key]["importance"], imp)
            seen[key]["must_have"] = seen[key]["must_have"] or mh
    return list(seen.values())[:20]

def _present(skill: str, text: str) -> bool:
    pat = re.escape(skill)
    rx = re.compile(pat, re.I)
    return bool(rx.search(text))

def score_resume_against_skills(resume_text: str, skills: List[Dict]) -> Dict:
    score = 0.0
    total = 0.0
    gaps: List[str] = []
    for s in skills:
        w = 1.0 + 0.5 * (int(s.get("importance",3)) - 1)
        if s.get("must_have", False):
            w += 1.0
        total += w
        if _present(s["skill"], resume_text):
            score += w
        else:
            gaps.append(s["skill"])
    pct = round(100.0 * score / max(total, 1.0), 1)
    return {"score": pct, "gaps": gaps[:8], "matched": len(skills) - len(gaps), "total_skills": len(skills)}

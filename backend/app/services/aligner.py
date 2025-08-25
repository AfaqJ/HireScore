# app/services/aligner.py
from typing import List, Dict
import json, re
from app.services.lc import get_retriever, make_skill_chain

def _parse_json(text: str):
    # tolerant JSON cleanup (handles fenced code blocks)
    t = text.strip()
    t = re.sub(r"^```(?:json)?|```$", "", t, flags=re.I | re.M).strip()
    try:
        return json.loads(t)
    except Exception:
        return []

# --- Skill extraction from JD via LangChain ---
def extract_jd_skills_langchain(job_id: int, top_k_ctx: int = 6) -> List[Dict]:
    retriever = get_retriever(job_id, k=top_k_ctx)
    # pull context by asking a general query
    docs = retriever.invoke("key skills, requirements, and tech stack")
    ctx = "\n\n".join([d.page_content for d in docs]) if docs else ""

    chain = make_skill_chain()
    raw = chain.invoke(ctx)  # llm returns a string or object
    items = _parse_json(getattr(raw, "content", str(raw)))

    # dedupe + clamp
    seen = {}
    for it in items:
        s = str(it.get("skill", "")).strip()
        if not s:
            continue
        key = s.casefold()
        imp = int(it.get("importance", 3))
        mh = bool(it.get("must_have", False))
        imp = min(max(imp, 1), 5)
        if key not in seen:
            seen[key] = {"skill": s, "importance": imp, "must_have": mh}
        else:
            seen[key]["importance"] = max(seen[key]["importance"], imp)
            seen[key]["must_have"] = seen[key]["must_have"] or mh
    # limit to 15 to keep scoring stable
    return list(seen.values())[:15]

# --- Matching helpers ---
_ALIASES = [
    # tuples of equivalent spellings to improve simple matching
    ("nodejs", "node.js", "node js", "node"),
    ("reactjs", "react"),
    ("typescript", "type script"),
    ("javascript", "java script", "js"),
    ("aws s3", "amazon s3", "s3"),
    ("postgresql", "postgres", "postgre sql"),
    ("ci/cd", "cicd", "ci cd"),
    ("docker", "docker-compose", "docker compose"),
]

def _normalize(text: str) -> str:
    # lowercase, collapse spaces, strip punctuation except dots/slashes for tech names
    t = text.casefold()
    t = re.sub(r"[_\-]+", " ", t)
    t = re.sub(r"\s+", " ", t)
    return t

def _mk_variants(skill: str) -> List[str]:
    s = _normalize(skill)
    variants = {s}
    for group in _ALIASES:
        if s in group:
            variants.update(group)
    # handle dots and spaces variants (e.g., "node.js" <-> "node js")
    if "." in s:
        variants.add(s.replace(".", " "))
    if " " in s:
        variants.add(s.replace(" ", ""))
    return list(variants)

def _present(skill: str, text: str) -> bool:
    """
    Token-aware, alias-aware presence check (still lightweight).
    Uses word boundaries for words; for tech tokens (with dots/slashes) allow loose match.
    """
    body = _normalize(text)
    for v in _mk_variants(skill):
        v_norm = re.escape(v)
        if re.search(rf"(?:\b|^){v_norm}(?:\b|$)", body):
            return True
    return False

# --- Scoring ---
def score_resume_against_skills(resume_text: str, skills: List[Dict]) -> Dict:
    score = 0.0
    total = 0.0
    gaps: List[str] = []
    matched_count = 0

    for s in skills:
        w = 1.0 + 0.5 * (int(s.get("importance", 3)) - 1)
        if s.get("must_have", False):
            w += 1.0
        total += w

        if _present(s["skill"], resume_text):
            score += w
            matched_count += 1
        else:
            gaps.append(s["skill"])

    pct = round(100.0 * score / max(total, 1.0), 1)
    # Return ALL gaps (no 8-item cap); caller/UI can choose to truncate for display.
    return {
        "score": pct,
        "gaps": gaps,
        "matched": matched_count,
        "total_skills": len(skills),
    }

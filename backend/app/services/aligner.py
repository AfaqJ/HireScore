from typing import List, Dict
import re
from .retriever import retrieve
from .llm import ask_json

_SKILL_SPEC = (
    'Return ONLY a JSON array like: '
    '[{"skill":"Python","importance":1-5,"must_have":true|false}, ...]'
)

def extract_jd_skills(collection_name: str, top_k_ctx: int = 6) -> List[Dict]:
    """Use JD context + LLM to produce a normalized skill list with weights."""
    ctx = "\n\n".join(retrieve(collection_name, "key skills, requirements, and tech stack", k=top_k_ctx))
    if not ctx.strip():
        return []
    prompt = f"""
You will read job description context and list the most important skills/technologies/tools.
- Normalize names (e.g., "Node" -> "Node.js", "AWS S3" -> "AWS").
- Limit to 15-20 items max.
{_SKILL_SPEC}

JOB DESCRIPTION CONTEXT:
{ctx}
"""
    items = ask_json(prompt)
    # dedupe by casefolded skill name, keep max importance and must_have if any says true
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
    # cap to 20 for readability
    return list(seen.values())[:20]

def _present(skill: str, text: str) -> bool:
    """Loose presence check for the skill name in resume text."""
    pat = re.escape(skill)
    rx = re.compile(pat, re.I)
    return bool(rx.search(text))

def score_resume_against_skills(resume_text: str, skills: List[Dict]) -> Dict:
    """
    Heuristic scoring:
    - each skill has weight w = 1 + 0.5*(importance-1) + 1 if must_have
    - if skill appears in resume_text → you get w points, else 0 and it becomes a gap
    """
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

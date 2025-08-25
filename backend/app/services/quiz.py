# app/services/quiz.py
from typing import List, Dict, Tuple
import json
import re
from sqlmodel import Session

from app.services.lc import (
    get_retriever,
    make_quiz_chain,
    make_grade_chain,
)
from app.services.aligner import extract_jd_skills_langchain


# -----------------------------
# Utilities
# -----------------------------
def _strip_code_fence(t: str) -> str:
    t = (t or "").strip()
    # remove single-line and fenced code blocks like ```json ... ```
    t = re.sub(r"^```(?:json)?", "", t, flags=re.I | re.M)
    t = re.sub(r"```$", "", t, flags=re.I | re.M)
    return t.strip()


def _parse_json_block(t: str):
    """
    Tolerant JSON parser for LLM outputs.
    Accepts plain arrays/objects or fenced code blocks.
    """
    try:
        return json.loads(_strip_code_fence(t))
    except Exception:
        return []


# -----------------------------
# Question generation
# -----------------------------
def make_questions(job_id: int, n: int, session: Session) -> List[str]:
    """
    Produce requirement/self-assessment style questions from the JD context.
    Returns List[str]. Guarantees JD-specific, non-generic, non-duplicate questions.
    """
    retriever = get_retriever(job_id, k=8)
    docs = retriever.invoke("key skills, hard requirements, preferred qualifications, and tech stack")
    context = "\n\n".join(getattr(d, "page_content", "") for d in (docs or []))

    # --- 1) Try LLM generation ---
    chain = make_quiz_chain()
    questions: List[str] = []
    try:
        raw = chain.invoke({"context": context, "n": n})
        content = getattr(raw, "content", str(raw))
        items = _parse_json_block(content)

        if isinstance(items, list):
            for it in items:
                q = str(it.get("q", "")).strip() if isinstance(it, dict) else str(it).strip()
                if q:
                    questions.append(q)
    except Exception:
        # if LLM fails, we’ll fall back below
        pass

    # --- 2) Clean up: drop generic/dupes ---
    def _is_generic(q: str) -> bool:
        qq = q.strip().lower()
        bad_phrases = [
            "key technologies listed in this jd",
            "key technologies in this jd",
            "describe your experience with the key technologies",
            "type your answer",
            "have you worked with the key technologies",
        ]
        return any(p in qq for p in bad_phrases) or len(qq) < 12

    dedup = []
    seen = set()
    for q in questions:
        qn = " ".join(q.split())
        if not _is_generic(qn) and qn not in seen:
            seen.add(qn)
            dedup.append(qn)
    questions = dedup

    # If the LLM didn't produce enough, fall back to JD skills
    if len(questions) < n:
        # --- 3) Fallback from JD skills so questions are JD-specific ---
        jd_skills = extract_jd_skills_langchain(job_id, top_k_ctx=8) or []
        # sort by importance (desc), must_have first
        jd_skills.sort(key=lambda s: (not s.get("must_have", False), -int(s.get("importance", 3))))
        skill_names = []
        seen_s = set()
        for s in jd_skills:
            name = str(s.get("skill", "")).strip()
            if name and name.lower() not in seen_s:
                seen_s.add(name.lower())
                skill_names.append(name)

        def mkq(skill: str) -> str:
            return (
                f"Have you used {skill}? If yes, how many years and at what depth (daily/weekly/POC)? "
                f"Name one project where you applied it."
            )

        for skill in skill_names:
            if len(questions) >= n:
                break
            q = mkq(skill)
            if q not in seen:
                seen.add(q)
                questions.append(q)

    # --- 4) Final safety: if still short, generate varied templates (no duplicates) ---
    templates = [
        "How many years have you worked with {x}? Mention notable projects.",
        "Have you implemented {x} in production? Describe your role and scope.",
        "Rate your proficiency with {x} (beginner/intermediate/advanced) and justify briefly.",
        "Have you integrated {x} with related tools from the JD? Give one example.",
    ]
    if len(questions) < n:
        # if we reached here, we likely had no skills; still avoid duplicates
        filler_targets = ["the primary database", "CI/CD pipelines", "cloud infrastructure", "testing/QA tooling"]
        i = 0
        while len(questions) < n:
            t = templates[i % len(templates)]
            x = filler_targets[i % len(filler_targets)]
            q = t.format(x=x)
            if q not in seen:
                seen.add(q)
                questions.append(q)
            i += 1

    # Cap to n and return
    return questions[:n]




# -----------------------------
# Grading (requirement alignment)
# -----------------------------
def _score_from_llm(result: Dict) -> Dict:
    """
    Map LLM fields to the schema our DB/routes expect.
    Supports both the new requirement-style fields and the older accuracy/completeness style.
    New-style fields:
      - relevance (0–5), qualification (0–5), communication (0–5), tip
    Old-style fields (fallback):
      - accuracy (0–5), completeness (0–5), communication (0–5), tip
    We convert to:
      {accuracy:int, completeness:int, communication:int, score_pct:float, tip:str}
    """
    # Prefer new fields if present
    if any(k in result for k in ("relevance", "qualification")):
        rel = float(result.get("relevance", 0))
        qual = float(result.get("qualification", 0))
        comm = float(result.get("communication", 0))
        tip = str(result.get("tip", "")).strip()
        # Weighted 0–100
        pct = (0.4 * rel + 0.5 * qual + 0.1 * comm) / 5.0 * 100.0
        return {
            "accuracy": int(round(rel)),
            "completeness": int(round(qual)),
            "communication": int(round(comm)),
            "score_pct": round(max(0.0, min(100.0, pct)), 1),
            "tip": tip or "Add years, scope, and concrete examples.",
        }

    # Fallback to old fields if the model returned that format
    acc = float(result.get("accuracy", 0))
    comp = float(result.get("completeness", 0))
    comm = float(result.get("communication", 0))
    tip = str(result.get("tip", "")).strip()
    # Simple average → 0–100
    pct = (acc + comp + comm) / 15.0 * 100.0
    return {
        "accuracy": int(round(acc)),
        "completeness": int(round(comp)),
        "communication": int(round(comm)),
        "score_pct": round(max(0.0, min(100.0, pct)), 1),
        "tip": tip or "Be specific: years, scope, and outcomes.",
    }


def grade_one(job_id: int, question: str, answer: str) -> Dict:
    """
    Grade a single Q/A using requirement-alignment criteria.
    Returns:
      {accuracy:int, completeness:int, communication:int, score_pct:float, tip:str}
    """
    retriever = get_retriever(job_id, k=6)
    # Pull context focused on the requirement in the question
    docs = retriever.invoke(f"job requirements and skills relevant to: {question}")
    context = "\n\n".join(getattr(d, "page_content", "") for d in (docs or []))

    chain = make_grade_chain()
    raw = chain.invoke({"context": context, "question": question, "answer": answer})
    content = getattr(raw, "content", str(raw))

    result = _parse_json_block(content)
    if isinstance(result, dict) and result:
        return _score_from_llm(result)

    # Very defensive fallback in case the model returns junk
    return {
        "accuracy": 0,
        "completeness": 0,
        "communication": 2,
        "score_pct": 10.0,
        "tip": "Clarify years, scale, and your role.",
    }


# -----------------------------
# Quiz-level summary (for homepage card)
# -----------------------------
def _keywordize(text: str) -> List[str]:
    """
    Very light keyword extraction from a question string.
    Keeps tech-ish tokens (react, node.js, kubernetes, ci/cd, s3, etc.).
    """
    t = re.sub(r"[^a-zA-Z0-9+.#/ ]+", " ", (text or "")).lower()
    stop = set("the a an for to of and or in with do does have has how what is are on".split())
    toks = [w for w in t.split() if len(w) > 1 and w not in stop]
    return list(dict.fromkeys(toks))[:6]


def _make_quiz_match(
    questions: List[Dict], per_results: List[Dict], jd_skills: List[Dict]
) -> Dict:
    """
    Compose quiz-level summary similar to cv_match block:
      {score, gaps, matched, total_skills, message}
    """
    scores = [float(r.get("score_pct", 0.0)) for r in per_results]
    overall = round(sum(scores) / max(len(scores), 1), 1)

    # Anything below 60% is considered a weakness
    weak_idxs = [i for i, s in enumerate(scores) if s < 60]
    matched = len(scores) - len(weak_idxs)
    total = len(scores)

    # Collect keywords from weak questions
    kw_counts: Dict[str, int] = {}
    for i in weak_idxs:
        for k in _keywordize(questions[i]["text"]):
            kw_counts[k] = kw_counts.get(k, 0) + 1

    # Map JD skills to canonical case for nicer display
    jd_skill_map = {s.get("skill", "").lower(): s.get("skill", "") for s in (jd_skills or [])}

    # Try to align collected keywords to actual JD skills (simple contains)
    gaps: List[str] = []
    for k, _ in sorted(kw_counts.items(), key=lambda x: -x[1]):
        best = next((orig for low, orig in jd_skill_map.items() if k in low), None)
        if best and best not in gaps:
            gaps.append(best)
        elif k not in gaps and len(k) > 2:
            gaps.append(k)

    gaps = gaps[:8]
    msg = "Good overall alignment." if overall >= 70 else "Improve experience on highlighted areas."

    return {
        "score": overall,
        "gaps": gaps,
        "matched": matched,
        "total_skills": total,
        "message": msg,
    }


def grade_many(job_id: int, qas: List[Tuple[str, str]], session: Session) -> Dict:
    """
    Grade multiple Q/As and return:
      - 'overall' + 'feedback' (legacy fields used by the UI)
      - 'quiz_match' block for the homepage card
      - 'per' detailed list (one item per question) for the route to persist
    """
    # Per-question grading
    per: List[Dict] = []
    for q_text, a_text in qas:
        g = grade_one(job_id, q_text, a_text)
        per.append(g)

    # Overall (0–100)
    overall = round(sum(g["score_pct"] for g in per) / max(len(per), 1), 1)

    # JD skills (to help name gaps)
    jd_skills = extract_jd_skills_langchain(job_id, top_k_ctx=6)

    # Quiz-level summary for the homepage card
    questions_only = [{"text": q} for q, _ in qas]
    quiz_match = _make_quiz_match(questions_only, per, jd_skills)

    # Legacy feedback array; route will attach question_id when responding
    feedback = [{"score": g["score_pct"], "tip": g.get("tip", "")} for g in per]

    return {
        "overall": overall,
        "feedback": feedback,
        "quiz_match": quiz_match,
        "per": per,
    }

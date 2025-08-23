from typing import List, Dict
from app.services.retriever import retrieve
from app.services.llm import ask_json

def make_questions(collection_name: str, n:int=5) -> List[str]:
    # retrieve JD context to ground questions
    ctx = "\n\n".join(retrieve(collection_name, "core responsibilities and required skills", k=6))
    prompt = f"""You are an interviewer. Based on the JD context, write {n} concise, practical interview questions.
Prefer: real-world tasks, short scenario prompts, and specific tools from the JD.
Return ONLY JSON: [{{"q":"..."}}, ...] (no extra text)

JD CONTEXT:
{ctx}
"""
    out = ask_json(prompt)
    qs = [o.get("q","").strip() for o in out if o.get("q")]
    # fallback if model returns junk
    if len(qs) < n:
        qs += ["Tell me about a project where you used the core tools from this JD."] * (n-len(qs))
    return qs[:n]

def grade_one(collection_name: str, question: str, answer: str) -> Dict:
    ctx = "\n\n".join(retrieve(collection_name, question, k=4))
    prompt = f"""JD CONTEXT:
{ctx}

QUESTION: {question}
CANDIDATE ANSWER: {answer}

Grade strictly with the JD in mind.
Give integer scores: accuracy(0-5), completeness(0-5), communication(0-5).
Give ONE actionable tip (max 20 words).
Return ONLY JSON: {{"accuracy":0,"completeness":0,"communication":0,"tip":"..."}}"""
    g = ask_json(prompt)
    if not g:
        return {"accuracy":0,"completeness":0,"communication":0,"tip":"Be concrete, cite tools from the JD."}
    g = g[0] if isinstance(g, list) else g
    acc = int(g.get("accuracy",0)); comp = int(g.get("completeness",0)); comm = int(g.get("communication",0))
    subs = [max(0,min(5,acc)), max(0,min(5,comp)), max(0,min(5,comm))]
    pct = round(sum(subs)/15*100)
    return {"accuracy":subs[0], "completeness":subs[1], "communication":subs[2], "score_pct":pct, "tip":g.get("tip","")}

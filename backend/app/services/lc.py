# app/services/lc.py
from langchain_ollama import ChatOllama
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain.schema.runnable import RunnablePassthrough
from langchain.prompts import PromptTemplate
from typing import List, Dict
from langchain.text_splitter import RecursiveCharacterTextSplitter

# ---- LLM ----
def get_llm():
    # Any local model you pulled with Ollama works here
    # e.g., "mistral:7b-instruct-q4_0" or "llama3.1:8b-instruct-q4_0"
    return ChatOllama(model="mistral:latest", temperature=0.2)

# ---- Embeddings ----
def get_embedder():
    # Same model you used before, now via LangChain
    return HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

# ---- Vector store per Job ----
def collection_name_for_job(job_id: int) -> str:
    return f"jd_{job_id}"

def get_vectorstore(job_id: int) -> Chroma:
    embeddings = get_embedder()
    return Chroma(
        collection_name=collection_name_for_job(job_id),
        embedding_function=embeddings,
        persist_directory="./.chroma",
    )
from langchain.text_splitter import RecursiveCharacterTextSplitter


def index_job_description(job_id: int, jd_text: str):
    print(f"⚡ Starting index_job_description for job {job_id}")
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    persist_dir = f"chroma_db/job_{job_id}"
    try:
        vs = Chroma.from_texts(
            [jd_text],
            embedding=embeddings,
            persist_directory=persist_dir
        )
        print(f"✅ Successfully built Chroma store at {persist_dir}")
        return vs
    except Exception as e:
        import traceback
        print("❌ Exception in Chroma.from_texts")
        traceback.print_exc()
        raise e




def get_retriever(job_id: int, k: int = 4):
    vs = get_vectorstore(job_id)
    return vs.as_retriever(search_kwargs={"k": k})

# ---- Chains ----

# 1) Skill extraction chain (JD -> JSON list of skills with weights)
skill_prompt = PromptTemplate.from_template("""
You are given job description context. Extract the most important skills/technologies/tools.
Normalize names (e.g., "Node" -> "Node.js", "AWS S3" -> "AWS").
Limit to 15–20 items max.
Return ONLY JSON array like:
[{{"skill":"Python","importance":1-5,"must_have":true|false}}, ...]

JD CONTEXT:
{context}
""")

def make_skill_chain():
    llm = get_llm()
    return (
        {"context": RunnablePassthrough()} 
        | skill_prompt 
        | llm
    )

# 2) Quiz question generation
quiz_prompt = PromptTemplate.from_template("""
You are an interviewer. Based on the JD context, write {n} concise, practical interview questions.
Prefer real-world tasks, short scenarios, and specific tools from the JD.
Return ONLY JSON: [{{"q":"..."}}, ...] (no extra text)

JD CONTEXT:
{context}
""")


def make_quiz_chain():
    llm = get_llm()
    return (
        {"context": RunnablePassthrough(), "n": RunnablePassthrough()} 
        | quiz_prompt 
        | llm
    )

# 3) Grading chain
grade_prompt = PromptTemplate.from_template("""
JD CONTEXT:
{context}

QUESTION: {question}
CANDIDATE ANSWER: {answer}

Grade strictly with the JD in mind.
Give integer scores: accuracy(0-5), completeness(0-5), communication(0-5).
Give ONE actionable tip (max 20 words).
Return ONLY JSON: {{"accuracy":0,"completeness":0,"communication":0,"tip":"..."}}.
""")

def make_grade_chain():
    llm = get_llm()
    return (
        {"context": RunnablePassthrough(), "question": RunnablePassthrough(), "answer": RunnablePassthrough()}
        | grade_prompt
        | llm
    )

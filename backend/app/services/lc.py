# app/services/lc.py
from typing import List
from langchain_ollama import ChatOllama
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain.schema.runnable import RunnablePassthrough
from langchain.prompts import PromptTemplate
from langchain.text_splitter import RecursiveCharacterTextSplitter

# ---- Constants ----
PERSIST_ROOT = "chroma_db"  # single root used for both indexing + retrieval

# ---- LLM ----
def get_llm():
    # Any local model you pulled with Ollama works here
    # e.g., "mistral:7b-instruct-q4_0" or "llama3.1:8b-instruct-q4_0"
    return ChatOllama(model="mistral:latest", temperature=0.2)

# ---- Embeddings ----
def get_embedder():
    return HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

# ---- Vector store per Job ----
def collection_name_for_job(job_id: int) -> str:
    return f"jd_{job_id}"

def persist_dir_for_job(job_id: int) -> str:
    return f"{PERSIST_ROOT}/job_{job_id}"

def get_vectorstore(job_id: int) -> Chroma:
    """
    Open the SAME collection + persist directory used during indexing.
    """
    embeddings = get_embedder()
    return Chroma(
        collection_name=collection_name_for_job(job_id),
        embedding_function=embeddings,
        persist_directory=persist_dir_for_job(job_id),
    )
# ---- Indexing ----
def index_job_description(job_id: int, jd_text: str):
    """
    Chunk the JD and index into a collection specific to the job.
    Uses the same persist directory/collection that retrieval expects.
    With langchain_chroma, data is persisted automatically when a
    persist_directory is provided—no .persist() call exists.
    """
    print(f"⚡ Starting index_job_description for job {job_id}")
    embeddings = get_embedder()
    persist_dir = persist_dir_for_job(job_id)

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=900, chunk_overlap=120, separators=["\n\n", "\n", ". ", " ", ""]
    )
    chunks: List[str] = [c for c in splitter.split_text(jd_text) if c.strip()]

    try:
        vs = Chroma(
            collection_name=collection_name_for_job(job_id),
            embedding_function=embeddings,
            persist_directory=persist_dir,
        )

        if chunks:
            # add_texts writes to the persistent DB immediately in this integration
            vs.add_texts(chunks)

        print(
            f"✅ Chroma store ready at {persist_dir} "
            f"(collection={collection_name_for_job(job_id)}, chunks={len(chunks)})"
        )
        return vs
    except Exception as e:
        import traceback
        print("❌ Exception during JD indexing")
        traceback.print_exc()
        raise e


# ---- Retriever ----
def get_retriever(job_id: int, k: int = 4):
    vs = get_vectorstore(job_id)
    # similarity works well for skill extraction context
    return vs.as_retriever(search_type="similarity", search_kwargs={"k": k})

# ---- Chains ----

# 1) Skill extraction chain (JD -> JSON list of skills with weights)
skill_prompt = PromptTemplate.from_template(
    """
You are given job description context. Extract the most important, concrete skills/technologies/tools.
- Normalize names (e.g., "Node" -> "Node.js", "AWS S3" -> "AWS S3", "ReactJS" -> "React").
- Prefer skills explicitly present in context.
- Limit to at most 15 items.
- Each item: importance 1–5 (5 = critical), and must_have true/false.

Return ONLY a JSON array like:
[{{"skill":"Python","importance":5,"must_have":true}}, ...]


JD CONTEXT:
{context}
""".strip()
)

def make_skill_chain():
    llm = get_llm()
    return ({"context": RunnablePassthrough()} | skill_prompt | llm)

# 2) Quiz question generation
quiz_prompt = PromptTemplate.from_template(
    """
You are generating a candidate self-assessment quiz based on the job description.

Write {n} concise, direct questions that explicitly ask the candidate about:
- Their prior experience with the listed tools, frameworks, and skills.
- How much experience (years, projects, usage level) they have with each.
- Whether they have performed tasks mentioned in the requirements.

Do NOT phrase as interview problems or scenarios. Instead, use plain questions like:
- "Have you worked with Kubernetes before? If yes, how many years?"
- "How much experience do you have with React.js?"
- "Have you implemented CI/CD pipelines? Please describe your involvement."

Use only skills and requirements mentioned in the JD.
Return ONLY JSON in this format:
[{{"q":"Have you worked with React.js? If yes, how many years?"}}, ...]

JD CONTEXT:
{context}
""".strip()
)

def make_quiz_chain():
    llm = get_llm()
    return ({"context": RunnablePassthrough(), "n": RunnablePassthrough()} | quiz_prompt | llm)

# 3) Grading chain

grade_prompt = PromptTemplate.from_template(
    """
JD CONTEXT:
{context}

QUESTION: {question}
CANDIDATE ANSWER: {answer}

You are assessing whether the candidate's answer demonstrates that they meet the job requirements.

Evaluate on these dimensions:
- Relevance (0–5): Does the answer show they have the required skill/experience mentioned in the JD?
- Qualification Level (0–5): Based on the answer (years of experience, depth, scope), how well does this match the JD's expectations?
- Communication (0–5): Is the answer clear and professional?

If the candidate does not demonstrate the requirement, give low Relevance and Qualification Level scores.

Also decide:
- "qualified": true if the answer strongly suggests the candidate meets this requirement; false otherwise.

Return ONLY JSON in this format:
{{
  "relevance": 0,
  "qualification": 0,
  "communication": 0,
  "qualified": false,
  "tip": "short actionable advice (max 20 words)"
}}
""".strip()
)


def make_grade_chain():
    llm = get_llm()
    return (
        {
            "context": RunnablePassthrough(),
            "question": RunnablePassthrough(),
            "answer": RunnablePassthrough(),
        }
        | grade_prompt
        | llm
    )

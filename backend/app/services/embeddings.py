# purpose: load one embedding model and one chroma client for the whole app

from sentence_transformers import SentenceTransformer
import chromadb

# loads a small, fast embedding model; good enough for JD/resume text
_emb = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

# local persistent vector store folder (created automatically)
_chroma = chromadb.PersistentClient(path="./.chroma")

def embed_texts(texts: list[str]) -> list[list[float]]:
    """Return numeric vectors for each text."""
    return _emb.encode(texts, convert_to_numpy=False).tolist()

def get_or_create_collection(name: str):
    """Fetch or create a Chroma collection by name."""
    try:
        return _chroma.get_collection(name)
    except Exception:
        return _chroma.create_collection(name)

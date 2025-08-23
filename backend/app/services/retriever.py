# purpose: chunk JD, add to chroma, and retrieve relevant chunks later

from .embeddings import embed_texts, get_or_create_collection

def chunk(text: str, max_chars=1000, overlap=150) -> list[str]:
    """Simple char-based chunker with overlap to keep context coherent."""
    chunks = []
    i = 0
    L = len(text)
    while i < L:
        j = min(i + max_chars, L)
        chunks.append(text[i:j])
        if j == L:
            break
        i = max(0, j - overlap)
    return chunks

def index_jd(collection_name: str, jd_text: str) -> None:
    """Create/add chunks for this JD into a named Chroma collection."""
    col = get_or_create_collection(collection_name)
    parts = chunk(jd_text)
    vecs = embed_texts(parts)
    ids = [f"d{i}" for i in range(len(parts))]
    # if re-indexing, chroma requires unique ids; for MVP assume one index per collection
    col.add(documents=parts, embeddings=vecs, ids=ids)

def retrieve(collection_name: str, query: str, k: int = 4) -> list[str]:
    """Return top-k relevant JD chunks for a query."""
    col = get_or_create_collection(collection_name)
    res = col.query(query_texts=[query], n_results=k)
    return res["documents"][0] if res and res["documents"] else []

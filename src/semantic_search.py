import os

import chromadb
import pandas as pd
import numpy as np
from sentence_transformers import SentenceTransformer

# ── Configuration ─────────────────────────────────────────────────────────────

CSV_PATH = "data/processed/cbsa_wiki_wikivoyage_summaries_df.csv"
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PERSIST_DIR = os.path.join(BASE_DIR, "chroma_db")
COLLECTION_NAME = "cbsa"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"

# ── Initialization ─────────────────────────────────────────────────────────────

print("Loading embedding model...")
model = SentenceTransformer(EMBEDDING_MODEL)

print("Starting ChromaDB client...")
client = chromadb.PersistentClient(path=PERSIST_DIR)
collection = client.get_or_create_collection(
    name=COLLECTION_NAME,
    metadata={"hnsw:space": "cosine"},  # cosine distance: 0 (identical) → 1 (opposite)
)

# ── Database ───────────────────────────────────────────────────────────────────

def build_db(force_rebuild: bool = False) -> None:
    """Build the ChromaDB vector store from the city summaries CSV.

    Reads city summaries from ``CSV_PATH``, generates sentence embeddings
    using ``EMBEDDING_MODEL``, and stores them in the ChromaDB collection.

    Args:
        force_rebuild: If ``True``, deletes the existing collection before
            rebuilding. Use this when the CSV data or embedding model has
            changed. Defaults to ``False``.

    Raises:
        FileNotFoundError: If ``CSV_PATH`` does not exist.
        KeyError: If expected columns (``summary``, ``cbsa_name``,
            ``cbsa_code``) are missing from the CSV.
    """
    global collection

    if force_rebuild:
        print(f"Deleting existing collection '{COLLECTION_NAME}'...")
        client.delete_collection(name=COLLECTION_NAME)
        collection = client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )

    print(f"Loading data from {CSV_PATH}...")
    df = pd.read_csv(CSV_PATH)

    texts = df["summary"].tolist()
    cbsa_names = df["cbsa_name"].tolist()
    cbsa_ids = df["cbsa_code"].astype(str).tolist()

    print(f"Generating embeddings for {len(texts)} cities...")
    embeddings = model.encode(texts, show_progress_bar=True)

    print("Storing embeddings in ChromaDB...")
    collection.add(
            embeddings=embeddings.tolist(),
            documents=texts,
            metadatas=[{"cbsa": name, "cbsa_code": code} for name, code in zip(cbsa_names, cbsa_ids)],
            ids=cbsa_ids
        )

    print(f"Database built — {len(texts)} cities indexed.")


# ── Search ─────────────────────────────────────────────────────────────────────

def search(query: str, top_k: int = 5) -> list[dict]:
    """Search for cities semantically similar to the given free-text query.

    Encodes ``query`` into an embedding and retrieves the ``top_k`` most
    similar city documents from ChromaDB using cosine similarity.

    The returned ``score`` is a **similarity** value on ``[0, 1]``:
    - ``1.0`` — perfect match
    - ``0.5`` — unrelated
    - ``0.0`` — opposite meaning

    Args:
        query: Free-text description of the desired city
            (e.g. ``"warm coastal city with vibrant nightlife"``).
        top_k: Number of results to return. Defaults to ``5``.

    Returns:
        List of dicts sorted by descending similarity, each containing:
        - ``id``      — CBSA code (string)
        - ``cbsa``    — CBSA name
        - ``score``   — cosine similarity on [0, 1]
        - ``summary`` — stored city description
    """
    query_embedding = model.encode([query])

    results = collection.query(
        query_embeddings=query_embedding.tolist(),
        n_results=top_k,
    )

    return [
        {
            "cbsa_code": id_,
            "cbsa": meta["cbsa"],
            # "cbsa_code": meta["cbsa_code"],
            "score": float(np.clip(1 - dist, 0.0, 1.0)),   # cosine distance → similarity
            "summary": doc,
        }
        for doc, meta, dist, id_ in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
            results["ids"][0],
        )
    ]

# ── Main ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    build_db()
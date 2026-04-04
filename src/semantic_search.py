import chromadb
from sentence_transformers import SentenceTransformer
import pandas as pd
import os

# CONFIGURATION
# -----------------------------
# Path to input dataset
CSV_PATH = "data/processed/cbsa_wiki_wikivoyage_summaries_df.csv"

# Directory where ChromaDB will store data
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PERSIST_DIR = os.path.join(BASE_DIR, "chroma_db")
# Name of the collection inside ChromaDB
COLLECTION_NAME = "cbsa"


# INITIALIZATION
# -----------------------------
print("Loading model...")

# Load embedding model
model = SentenceTransformer("all-MiniLM-L6-v2")

print("Starting Chroma client...")

# Initialize persistent ChromaDB client
client = chromadb.PersistentClient(path=PERSIST_DIR)

# Create or get collection
collection = client.get_or_create_collection(name=COLLECTION_NAME)


# BUILD DATABASE
# -----------------------------
def build_db():
    """
    Reads CSV, generates embeddings, and stores them in ChromaDB.
    Run this once to build the database.
    """

    print("Loading data...")
    df = pd.read_csv(CSV_PATH)

    # Extract required fields
    texts = df["summary"].tolist()
    cbsa_names = df["cbsa_name"].tolist()
    cbsa_ids = df["cbsa_code"].astype(str).tolist()

    print("Generating embeddings...")

    # Convert text data into vector embeddings
    embeddings = model.encode(texts)

    print("Storing in Chroma...")

    # Add embeddings + metadata to the collection
    collection.add(
        embeddings=embeddings.tolist(),
        documents=texts,
        metadatas=[{"cbsa": name} for name in cbsa_names],
        ids=cbsa_ids
    )

    print("Database built!")


# SEARCH FUNCTION
# -----------------------------
def search2(query, top_k=5):
    """
    Takes a user query and returns the most similar results from ChromaDB.
    """

    # Convert query into embedding
    query_embedding = model.encode([query])

    # Perform similarity search
    results = collection.query(
        query_embeddings=query_embedding.tolist(),
        n_results=top_k
    )

    # Format results into a clean output
    output = []
    for doc, meta, dist ,id in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
        results["ids"][0]
    ):
        output.append({
            "cbsa": meta["cbsa"],
            "score": float(dist),
            "summary": doc,
            "id": id
        })

    return output

def search(query, top_k=5):
    query_embedding = model.encode([query])

    results = collection.query(
        query_embeddings=query_embedding.tolist(),
        n_results=top_k
    )

    output = []
    for doc, meta, dist, id_ in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
        results["ids"][0]
    ):
        output.append({
            "id": id_,
            "cbsa": meta["cbsa"],
            "score": float(dist),
            "summary": doc
        })

    return output

    return results

# MAIN EXECUTION
# -----------------------------
if __name__ == "__main__":
    # Build database (run once)
    build_db()
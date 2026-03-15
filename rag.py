import faiss
import numpy as np
import pickle
import os
import re
from sentence_transformers import SentenceTransformer
from rank_bm25 import BM25Okapi
from resume import extract_resume_text
from config import RESUME_PATH

# BGE model from Hugging Face — better than MiniLM for retrieval tasks
# Hosted on HuggingFace: https://huggingface.co/BAAI/bge-small-en-v1.5
MODEL_NAME = "BAAI/bge-small-en-v1.5"
INDEX_PATH = "resume_index.faiss"
CHUNKS_PATH = "resume_chunks.pkl"

model = SentenceTransformer(MODEL_NAME)

def chunk_resume(text):
    """Split resume into meaningful sections"""
    # Split on section headers and bullet points
    sections = re.split(r'\n(?=(?:Skills|Experience|Education|Projects|Certifications))', text)
    
    chunks = []
    for section in sections:
        # Further split long sections into smaller chunks
        if len(section.split()) > 150:
            words = section.split()
            for i in range(0, len(words), 120):
                chunk = " ".join(words[i:i+120])
                if chunk.strip():
                    chunks.append(chunk)
        else:
            if section.strip():
                chunks.append(section.strip())
    
    return chunks

def build_resume_index():
    """Build FAISS index from resume using HuggingFace BGE embeddings"""
    resume_text = extract_resume_text(RESUME_PATH)
    chunks = chunk_resume(resume_text)

    print(f"Building index from {len(chunks)} resume chunks...")

    # BGE models work better with this prefix for indexing
    prefixed = ["Represent this sentence for searching: " + c for c in chunks]
    embeddings = model.encode(prefixed, normalize_embeddings=True)

    # Build FAISS index
    dim = embeddings.shape[1]
    index = faiss.IndexFlatIP(dim)  # Inner product = cosine similarity for normalized vectors
    index.add(np.array(embeddings).astype("float32"))

    # Save index and chunks
    faiss.write_index(index, INDEX_PATH)
    with open(CHUNKS_PATH, "wb") as f:
        pickle.dump(chunks, f)

    print(f"Index built — {len(chunks)} chunks, dimension {dim}")
    return index, chunks

def load_index():
    """Load existing FAISS index"""
    if not os.path.exists(INDEX_PATH) or not os.path.exists(CHUNKS_PATH):
        return build_resume_index()
    index = faiss.read_index(INDEX_PATH)
    with open(CHUNKS_PATH, "rb") as f:
        chunks = pickle.load(f)
    return index, chunks

def semantic_search(query, index, chunks, top_k=3):
    """Find resume chunks most similar to job description using FAISS"""
    # BGE query prefix
    query_embedding = model.encode(
        ["Represent this sentence for searching: " + query],
        normalize_embeddings=True
    )
    scores, indices = index.search(
        np.array(query_embedding).astype("float32"), top_k
    )
    return [chunks[i] for i in indices[0] if i < len(chunks)]

def keyword_search(query, chunks, top_k=2):
    """BM25 keyword search to catch exact skill matches RAG might miss"""
    tokenized_chunks = [c.lower().split() for c in chunks]
    bm25 = BM25Okapi(tokenized_chunks)
    scores = bm25.get_scores(query.lower().split())
    top_indices = np.argsort(scores)[::-1][:top_k]
    return [chunks[i] for i in top_indices if scores[i] > 0]

def get_relevant_resume_chunks(job_description, top_k=4):
    """
    Hybrid search — combines semantic (FAISS) + keyword (BM25)
    Ensures both conceptual matches AND exact skill keywords are found
    """
    index, chunks = load_index()

    semantic_results = semantic_search(job_description, index, chunks, top_k=3)
    keyword_results = keyword_search(job_description, chunks, top_k=2)

    # Combine and deduplicate
    seen = set()
    combined = []
    for chunk in semantic_results + keyword_results:
        if chunk not in seen:
            seen.add(chunk)
            combined.append(chunk)

    return "\n\n".join(combined[:top_k])

if __name__ == "__main__":
    build_resume_index()
    print("\nTest — 'Kubernetes AWS DevOps CI/CD':")
    result = get_relevant_resume_chunks("Kubernetes AWS DevOps CI/CD pipeline Terraform")
    print(result)
    print("\nTest — 'Python FastAPI microservices':")
    result = get_relevant_resume_chunks("Python FastAPI microservices REST API")
    print(result)
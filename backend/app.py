# backend/app.py (excerpt)

# Import pipeline components (Extractor -> Chunker -> Store)
from ingest.extractor import Extractor
from ingest.chunker import Chunker
from ingest.store import FaissStore

# 1) --- Set up dependencies ---

# PDF text extractor (converts raw PDF bytes -> cleaned text + metadata)
extractor = Extractor()

# Storage embedding function (OpenAI example)
from openai import OpenAI
import os

# Initialize OpenAI client (reads key from environment variable OPENAI_API_KEY)
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Wrapper around OpenAI embedding API
# Takes a list of strings -> returns list of embedding vectors (list of floats)
def embed_fn(texts: list[str]) -> list[list[float]]:
    resp = client.embeddings.create(model="text-embedding-3-large", input=texts)
    return [d.embedding for d in resp.data]

# Chunker: splits cleaned text into semantic chunks, embeds them with embed_fn
chunker = Chunker(
    embed_fn=embed_fn,
    breakpoint_threshold_type="percentile",     # chunking strategy
    breakpoint_threshold_amount=95              # higher = fewer, larger chunks
)

# Vector store (FAISS) for similarity search
# NOTE: dim must match embedding model dimension (3072 for text-embedding-3-large)
store = FaissStore(dim=3072, data_dir="data/index", metric="ip")

# 2) --- Upload flow (used by /upload endpoint) ---
def handle_upload(pdf_bytes: bytes, doc_id: str):
    # Extract text + metadata from PDF
    extracted = extractor.ingest_pdf(pdf_bytes, doc_id)  # -> {"text": ..., "meta": {...}}

    # Chunk + embed the extracted text
    items = chunker.process(extracted["text"], doc_id=doc_id, base_meta=extracted["meta"])

    # Save embeddings + metadata into FAISS store
    store.upsert(items)

    # Return summary of what was indexed
    return {"doc_id": doc_id, "chunks_indexed": len(items)}

# 3) --- Retrieval flow (used by /retrieve endpoint or agents) ---
def retrieve(query: str, top_k: int = 8):
    # Embed the query, then search top_k most similar chunks in FAISS
    return store.search_by_text(query, embed_fn=embed_fn, top_k=top_k)

from __future__ import annotations
from typing import List, Dict, Any, Optional
import os, json
import numpy as np
import faiss  # pip install faiss-cpu

class FaissStore:
    """
    Minimal FAISS + JSONL metadata store.

    Expects items shaped like:
      {"id": str, "text": str, "vector": List[float], "metadata": Dict[str, Any]}

    Methods:
      - upsert(items)                # insert/update items into FAISS + metadata
      - search_by_vector(vector)     # search by embedding vector
      - search_by_text(query, embed_fn) # search by raw query text
      - load()/persist()             # reload or save the index + metadata
    """
    def __init__(
        self,
        dim: int,
        data_dir: str = "data/index",
        metric: str = "ip",   # "ip" (inner product; use if embeddings normalized) or "l2"
    ) -> None:
        # Ensure storage directory exists
        os.makedirs(data_dir, exist_ok=True)
        self.data_dir = data_dir
        self.idx_path = os.path.join(data_dir, "faiss.index")
        self.ids_path = os.path.join(data_dir, "ids.json")
        self.meta_path = os.path.join(data_dir, "meta.jsonl")

        # Initialize FAISS index based on metric type
        if metric == "ip":
            self.index = faiss.IndexFlatIP(dim)
        elif metric == "l2":
            self.index = faiss.IndexFlatL2(dim)
        else:
            raise ValueError("metric must be 'ip' or 'l2'")

        # Keep a list of chunk IDs in memory
        self.ids: List[str] = []

        # Create metadata file if it doesn't exist
        if not os.path.exists(self.meta_path):
            open(self.meta_path, "w", encoding="utf-8").close()

    # ---------- persistence ----------

    def persist(self) -> None:
        """
        Save the FAISS index and IDs list to disk.
        Called after upsert to make the index durable.
        """
        faiss.write_index(self.index, self.idx_path)
        with open(self.ids_path, "w", encoding="utf-8") as f:
            json.dump(self.ids, f)

    def load(self) -> None:
        """
        Load FAISS index and IDs list from disk (if they exist).
        Call this at startup if you want to reuse an existing index.
        """
        if os.path.exists(self.idx_path):
            self.index = faiss.read_index(self.idx_path)
        if os.path.exists(self.ids_path):
            with open(self.ids_path, "r", encoding="utf-8") as f:
                self.ids = json.load(f)

    # ---------- write ----------

    def upsert(self, items: List[Dict[str, Any]]) -> None:
        """
        Insert items (id, text, vector, metadata) into FAISS + metadata store.
        - Adds vectors to FAISS.
        - Appends metadata and text to JSONL file.
        - Persists index and IDs after update.
        """
        if not items:
            return
        # Collect vectors into numpy array for FAISS
        vecs = np.array([it["vector"] for it in items], dtype="float32")
        self.index.add(vecs)

        # Track IDs in memory
        self.ids.extend([it["id"] for it in items])

        # Append metadata/text for each item
        with open(self.meta_path, "a", encoding="utf-8") as f:
            for it in items:
                f.write(json.dumps({
                    "id": it["id"],
                    "text": it.get("text", ""),
                    "metadata": it.get("metadata", {}),
                }) + "\n")

        # Save updated index and IDs
        self.persist()

    # ---------- read/search ----------

    def _load_meta_map(self) -> Dict[str, Dict[str, Any]]:
        """
        Load all metadata/text from JSONL into a dict keyed by ID.
        Used when retrieving search results.
        """
        meta_map: Dict[str, Dict[str, Any]] = {}
        with open(self.meta_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    j = json.loads(line)
                    meta_map[j["id"]] = j
        return meta_map

    def search_by_vector(self, vector: List[float], top_k: int = 10) -> List[Dict[str, Any]]:
        """
        Search FAISS using a raw embedding vector.
        Returns top_k results with their text, metadata, and similarity score.
        """
        if not self.ids:
            return []
        q = np.array([vector], dtype="float32")
        scores, I = self.index.search(q, top_k)
        meta_map = self._load_meta_map()

        hits: List[Dict[str, Any]] = []
        for rank, idx in enumerate(I[0]):
            if idx < 0 or idx >= len(self.ids):
                continue
            chunk_id = self.ids[idx]
            rec = meta_map.get(chunk_id, {"id": chunk_id, "text": "", "metadata": {}})
            rec["score"] = float(scores[0][rank])
            hits.append(rec)
        return hits

    def search_by_text(self, query: str, embed_fn, top_k: int = 10) -> List[Dict[str, Any]]:
        """
        Convenience method: embed a raw query string with the same embed_fn as chunks,
        then call search_by_vector to get the nearest neighbors.
        """
        vec = embed_fn([query])[0]
        return self.search_by_vector(vec, top_k=top_k)

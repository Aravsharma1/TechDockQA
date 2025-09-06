# backend/ingest/chunker.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Callable, List, Dict, Any, Optional

from langchain_openai import OpenAIEmbeddings
from langchain_experimental.text_splitter import SemanticChunker

# Type for your storage embedding function
EmbedFn = Callable[[List[str]], List[List[float]]]


@dataclass
class ChunkRecord:
    id: str
    text: str
    metadata: Dict[str, Any]


class Chunker:
    """
    1) Semantic-chunk cleaned text (no file I/O here).
    2) Embed chunk texts with embed_fn (OpenAI or other).
    3) Return items ready for vector-store upsert (store.py saves them).

    Args:
      embed_fn: List[str] -> List[List[float]] (your storage embeddings)

      # for the chunker to work, we need to determine when to break apart
      # the sentences: we do this by looking at the differences in the embeddings
      # between any two sentences.
      # when the difference is past some threshold, then they are split.
      # this "threshold" is determined by:
      # breakpoint_threshold_type arg, which can take in the following values:
      # percentile, standard deviation, gradient

      breakpoint_threshold_type: str
      breakpoint_threshold_amount: int
      splitter_model: str
    """

    def __init__(
        self,
        embed_fn: EmbedFn,
        breakpoint_threshold_type: str = "percentile",
        breakpoint_threshold_amount: int = 95,
        splitter_model: str = "text-embedding-3-large",
    ) -> None:
        self.embed_fn = embed_fn

        # Create the Text Splitter (SemanticChunker).
        # for the chunker to work, we need to determine when to break apart
        # the sentences: we do this by looking at the differences in the embeddings
        # between any two sentences.
        # when the difference is past some threshold, then they are split.
        # this "threshold" is determined by:
        # breakpoint_threshold_type arg, which can take in the following values:
        # percentile, standard deviation, gradient
        self.splitter = SemanticChunker(
            OpenAIEmbeddings(model=splitter_model),
            breakpoint_threshold_type=breakpoint_threshold_type,
            breakpoint_threshold_amount=breakpoint_threshold_amount,
        )

    def process(
        self,
        text: str,
        doc_id: str,
        base_meta: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        End-to-end: text -> semantic chunks -> storage embeddings -> items for store.upsert(items)
        Returns: [{id, text, vector, metadata}, ...]
        """
        base_meta = base_meta or {}
        chunks = self._make_chunks(text=text, doc_id=doc_id, base_meta=base_meta)
        if not chunks:
            return []

        vectors = self._embed_chunks([c.text for c in chunks])
        if len(vectors) != len(chunks):
            raise ValueError("Embedding count mismatch with chunk count")

        items: List[Dict[str, Any]] = []
        for rec, vec in zip(chunks, vectors):
            items.append({
                "id": rec.id,
                "text": rec.text,
                "vector": vec,
                "metadata": rec.metadata,
            })
        return items

    # ---------- internals ----------

    def _make_chunks(
        self,
        text: str,
        doc_id: str,
        base_meta: Dict[str, Any],
    ) -> List[ChunkRecord]:
        """
        Semantic chunking of the provided text.

        # for the chunker to work, we need to determine when to break apart
        # the sentences: we do this by looking at the differences in the embeddings
        # between any two sentences.
        # when the difference is past some threshold, then they are split.
        # this "threshold" is determined by:
        # breakpoint_threshold_type arg, which can take in the following values:
        # percentile, standard deviation, gradient
        """
        if not text or not text.strip():
            return []

        docs = self.splitter.create_documents([text])  # List[Document] with .page_content, .metadata
        out: List[ChunkRecord] = []
        for i, d in enumerate(docs):
            out.append(
                ChunkRecord(
                    id=f"{doc_id}::chunk_{i:05d}",
                    text=d.page_content,
                    metadata={**base_meta, "doc_id": doc_id, "chunk_index": i},
                )
            )
        return out

    def _embed_chunks(self, chunk_texts: List[str]) -> List[List[float]]:
        """Create storage embeddings using your provided embed_fn."""
        return self.embed_fn(chunk_texts)

from __future__ import annotations
from typing import Callable, List
from langchain_openai import OpenAI

class EmbeddingAgent: 
    '''
    Constructor for the Embedding Agent. Agent that converts a PDF document to Vector embeddings. 
    (1) PDF document is converted into chunks. 
    (2) Chunks are converted into vector embeddings.
    (3) Vector embeddings are stored in a Vector Database.
    Args:
            embed_fn: a function that takes a list of strings (chunks)
                      and returns a list of embeddings (list of floats).
                      e.g., wraps the OpenAI API call.
            vector_store: the vector database client (FAISS/Chroma/etc.)
                          must expose an upsert(doc_id, items) method.
            chunk_size: maximum size of each chunk in characters.
            chunk_overlap: number of characters to overlap between chunks.  
    '''
    def __init__(self, embed_fn, vector_store, chunk_size=1000, chunk_overlap=150):
        self.embed_fn = embed_fn
        self.vector_store = vector_store
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
    
    def _make_chunks(self, text: str):
        '''
        Converts PDF document into chunks using ______. 
        '''
    
    def _embed_chunks():
        '''
        Embeds chunks using the OpenAI API. 
        '''
    
    def _store_embedded_chunks():
        '''
        Stores Embedded chunks in a Vector Database. 
        '''
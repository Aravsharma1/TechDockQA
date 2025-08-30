from __future__ import annotations
from typing import Callable, List
from langchain_openai import OpenAI
import re
from utils import utils
from langchain.embeddings import OpenAIEmbeddings
oaiembeds = OpenAIEmbeddings()

class Chunker: 
    '''
    Constructor for the Chunker Class. Class that converts a PDF document to Vector embeddings. 
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

        # run as a loop to scan through all pages of the document
        file_path='' # change this - TO DO 
        with open(file_path) as file:
            essay = file.read()
        
        # split stuff from the file_path based into 1 sentence chunks
        single_sentences_list = re.split(r'(?<=[.?!])\s+', essay)
        print(f"{len(single_sentences_list)} senteneces were found")
        sentences = [{'sentence': x, 'index' : i} for i, x in enumerate(single_sentences_list)]
        sentences[:3]

        # basically have a list of sentences for now, we want to combine these 
        # sentences to reduce noise and capture the relationships between sequential sentences
        Utils = utils()
        sentences = Utils.combine_sentences(sentences)

        return sentences
        
    def _embed_chunks(sentences):
        '''
        Embeds chunks using the OpenAI API. 
        '''
        embeddings = oaiembeds.embed_documents([x['combined_sentence'] for x in sentences])
        for i, sentence in enumerate(sentences):
            sentence['combined_sentence_embedding'] = embeddings[i]

    
    def _store_embedded_chunks():
        '''
        Stores Embedded chunks in a Vector Database. 
        '''
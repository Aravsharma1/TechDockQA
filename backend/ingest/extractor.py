from __future__ import annotations
import logging
import re
from typing import Dict
import fitz  # PyMuPDF

class Extractor: 
    '''
    Owns the Extractor workflow for one document upload. Document is getting uploaded as a PDF through the UI. 
    The IngestionAgent class: 
    (1) takes a PDF uploaded by the user, 
    (2) extracts its readable text,
    (3) and normalizes it for consistency.
    (4) It also gathers minimal metadata like page count and text length. 
    - Its output is clean text plus metadata, ready for chunking and embedding in the next stage of the pipeline.
    '''

    def __init__(self, logger: logging.Logger | None = None) -> None:
        # Use provided logger or default to module-level logger
        self.logger = logger or logging.getLogger(__name__)
    
    def ingest_pdf(self, pdf_bytes: bytes, doc_id: str) -> dict: 
        '''
        Extracts text and metadata from the given PDF.
        Args: 
            pdf_bytes: raw PDF file contents from the FastAPI upload
            doc_id: unique ID assigned for each document uploaded
        function that will be called by /upload endpoint, internally calls 
        the following set of functions.
        '''

        text, n_pages = self._extract_text(pdf_bytes)
        clean_version = self._clean_text(text)
        meta = self._make_meta(doc_id, n_pages, clean_version)
        return {"text": clean_version, "meta": meta}

    def _extract_text(self, pdf_bytes: bytes) -> tuple[str, int]:
        '''
        Uses PyMuPDF to read the PDF and return the text in it and the number of pages in it. 
        Args: 
            pdf_bytes: raw PDF file contents from the FastAPI endpoint.
        Output: 
            text: string that concatenates all of the text in the PDF document. 
            n_pages: integer i.e. page count of PDF. 
        '''
        try:
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        except Exception as e:
            self.logger.exception("Failed to open PDF bytes")
            raise ValueError(f"PDF open error: {e}") from e
        try:
            pages = []
            for page in doc: 
                pages.append(page.get_text("text"))
            text = "\n".join(pages)
            return text, doc.page_count
        except Exception as e: 
            self.logger.exception("Failed Extracting text from the PDF.")
            raise ValueError(f"PDF text extraction error: {e}") from e
        finally: 
            doc.close()


    def _clean_text(self, text: str) -> str:
        '''
        Normalize whitespace, remove weird stuff and make the text more consistent in formatting. 
        Args: 
            text: extracted text from the PDF returned by _extract_text()
        Output: 
            text: cleaned text with proper formatting. 
        '''
        if not text:
            return ""
        # normalize newlines and spaces
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)  # collapse 3+ newlines to 2
        # normalize common punctuation variants
        text = (text
                .replace("“", '"').replace("”", '"')
                .replace("’", "'").replace("–", "-").replace("—", "-"))
        return text.strip()
    
    def _make_meta(self, doc_id: str, n_pages: int, text: str) -> dict:
        '''
        Build Metadata directory. Final step in ingest_pdf.
        Args: 
            doc_id: provided by backend.
            n_pages: from _extract_text.
            text: cleaned text.
        Output: 
            dictionary with doc_id, n_pages, length_chars
        '''
        if text:
            length_chars = len(text)
        else:
            length_chars = 0

        metadata: Dict[str, int | str] = {
            "doc_id": doc_id,
            "n_pages": int(n_pages),
            "length_chars": int(length_chars),
        }

        return metadata
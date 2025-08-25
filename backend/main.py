from fastapi import FastAPI, UploadFile, File, HTTPException
from pydantic import BaseModel 
from agents.ingest import IngestionAgent
import uuid

app = FastAPI()
ingestor = IngestionAgent()

class UploadResponse(BaseModel):
    doc_id: str
    message: str

@app.post("/upload", response_model=UploadResponse)
async def upload(file: UploadFile = File(...)):
    pdf_bytes = await file.read()
    doc_id = uuid.uuid4().hex # generate a unique doc id using uuid
    result = ingestor.ingest_pdf(pdf_bytes, doc_id)

    return UploadResponse(doc_id=result["meta"]["doc_id"], message="PDF processed") 

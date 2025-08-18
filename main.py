from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import uvicorn
import os
from rag_pipeline import RAGPipeline

# Initialize FastAPI app
app = FastAPI(
    title="RAG Chat API", 
    description="Chat with your documents using RAG pipeline",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

rag = RAGPipeline()

class ChatMessage(BaseModel):
    message: str

class ChatResponse(BaseModel):
    response: str
    sources: List[str]
    num_sources: int = 0
    memory_length: int = 0

class MemoryResponse(BaseModel):
    memory: List[dict]
    total_exchanges: int

class MemorySearchResponse(BaseModel):
    results: List[dict]
    query: str
    total_found: int

class UploadResponse(BaseModel):
    message: str
    processed_files: List[str]
    total_chunks: int
    errors: List[str]

class StatusResponse(BaseModel):
    status: str
    rag_pipeline: dict

@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "RAG Chat API is running!",
        "version": "1.0.0",
        "status": "healthy",
        "endpoints": {
            "upload": "/upload-files/",
            "chat": "/chat/",
            "health": "/health/",
            "docs": "/docs"
        }
    }

@app.get("/health/")
async def health_check():
    """Health check endpoint"""
    try:
        rag_status = rag.get_status()
        return StatusResponse(
            status="healthy",
            rag_pipeline=rag_status
        )
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}

@app.post("/upload-files/", response_model=UploadResponse)
async def upload_files(files: List[UploadFile] = File(...)):
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded")
    
    try:
        result = rag.ingest_documents(files)
        
        return UploadResponse(
            message=f"Successfully processed {len(result['processed_files'])} files with {result['total_chunks']} chunks",
            processed_files=result['processed_files'],
            total_chunks=result['total_chunks'],
            errors=result['errors']
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing files: {str(e)}")

@app.post("/chat/", response_model=ChatResponse)
async def chat(chat_message: ChatMessage):
    """Chat with uploaded documents using RAG pipeline"""
    if not rag.documents_loaded:
        raise HTTPException(
            status_code=400, 
            detail="No documents loaded. Please upload and process files first."
        )
    
    try:
        result = rag.query(chat_message.message)
        
        if not result['success']:
            raise HTTPException(status_code=500, detail=result['response'])
        
        return ChatResponse(
            response=result['response'],
            sources=result['sources'],
            num_sources=result['num_sources'],
            memory_length=result.get('memory_length', 0)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing chat: {str(e)}")

@app.get("/memory/", response_model=MemoryResponse)
async def get_memory():
    """Get conversation memory"""
    try:
        memory = rag.get_memory()
        return MemoryResponse(
            memory=memory,
            total_exchanges=len(memory)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving memory: {str(e)}")

@app.delete("/memory/")
async def clear_memory():
    """Clear all conversation memory"""
    try:
        rag.clear_memory()
        return {"message": "Conversation memory cleared successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error clearing memory: {str(e)}")

@app.post("/reset/")
async def reset_pipeline():
    """Reset the RAG pipeline (clear all loaded documents)"""
    try:
        rag.reset()
        return {"message": "RAG pipeline reset successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error resetting pipeline: {str(e)}")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    print(f"Starting FastAPI server on port {port}")
    
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=port,
        log_level="info"
    )
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import uvicorn
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

@app.post("/upload-files/", response_model=UploadResponse)
async def upload_files(files: List[UploadFile] = File(...)):
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded")
    
    try:
        # Process files through RAG pipeline
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
    """
    Chat with uploaded documents using RAG pipeline
    """
    if not rag.documents_loaded:
        raise HTTPException(
            status_code=400, 
            detail="No documents loaded. Please upload and process files first."
        )
    
    try:
        # Process query through complete RAG pipeline
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

@app.get("/health/", response_model=StatusResponse)
async def health_check():
    """
    Check the health status of the API and RAG pipeline
    """
    rag_status = rag.get_status()
    
    return StatusResponse(
        status="healthy",
        rag_pipeline=rag_status
    )

@app.get("/memory/", response_model=MemoryResponse)
async def get_memory():
    """
    Get conversation memory
    """
    try:
        memory = rag.get_memory()
        return MemoryResponse(
            memory=memory,
            total_exchanges=len(memory)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving memory: {str(e)}")

@app.get("/memory/recent/{n}", response_model=MemoryResponse)
async def get_recent_memory(n: int):
    """
    Get recent n exchanges from memory
    """
    try:
        recent_memory = rag.get_recent_memory(n)
        return MemoryResponse(
            memory=recent_memory,
            total_exchanges=len(recent_memory)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving recent memory: {str(e)}")

@app.post("/memory/search/", response_model=MemorySearchResponse)
async def search_memory(query: ChatMessage, limit: int = 5):
    """
    Search conversation memory
    """
    try:
        results = rag.search_memory(query.message, limit)
        return MemorySearchResponse(
            results=results,
            query=query.message,
            total_found=len(results)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error searching memory: {str(e)}")

@app.delete("/memory/")
async def clear_memory():
    """
    Clear all conversation memory
    """
    try:
        rag.clear_memory()
        return {"message": "Conversation memory cleared successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error clearing memory: {str(e)}")

@app.get("/memory/summary/")
async def get_memory_summary():
    """
    Get memory summary and statistics
    """
    try:
        summary = rag.get_memory_summary()
        return summary
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting memory summary: {str(e)}")

@app.put("/memory/max-length/{max_length}")
async def set_memory_length(max_length: int):
    """
    Set maximum memory length
    """
    if max_length < 1:
        raise HTTPException(status_code=400, detail="Memory length must be at least 1")
    
    try:
        rag.set_memory_length(max_length)
        return {"message": f"Memory length set to {max_length}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error setting memory length: {str(e)}")

@app.post("/chat-no-memory/", response_model=ChatResponse)
async def chat_without_memory(chat_message: ChatMessage):
    """
    Chat without using conversation memory (one-time query)
    """
    if not rag.documents_loaded:
        raise HTTPException(
            status_code=400, 
            detail="No documents loaded. Please upload and process files first."
        )
    
    try:
        # Process query without memory context
        result = rag.query_with_memory_context(chat_message.message, use_memory=False)
        
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
async def reset_pipeline():
    """
    Reset the RAG pipeline (clear all loaded documents)
    """
    try:
        rag.reset()
        return {"message": "RAG pipeline reset successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error resetting pipeline: {str(e)}")

@app.get("/")
async def root():
    """
    Root endpoint with API information
    """
    return {
        "message": "RAG Chat API",
        "version": "1.0.0",
        "endpoints": {
            "upload": "/upload-files/",
            "chat": "/chat/",
            "chat_no_memory": "/chat-no-memory/",
            "memory": "/memory/",
            "memory_recent": "/memory/recent/{n}",
            "memory_search": "/memory/search/",
            "memory_summary": "/memory/summary/",
            "memory_clear": "/memory/",
            "memory_set_length": "/memory/max-length/{max_length}",
            "health": "/health/",
            "reset": "/reset/",
            "docs": "/docs"
        }
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
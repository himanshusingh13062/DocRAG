import os
import tempfile
import shutil
from typing import List, Dict, Any
from dotenv import load_dotenv

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnablePassthrough, RunnableLambda, RunnableParallel
from langchain_core.output_parsers import StrOutputParser
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain.docstore.document import Document

load_dotenv()

class RAGPipeline:
    def __init__(self):
        # Initialize components
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-pro",
            google_api_key=os.getenv("GEMINI_API_KEY"),
            temperature=0.1
        )
        self.embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
        self.text_splitter = RecursiveCharacterTextSplitter(chunk_size=4000, chunk_overlap=900)
        self.prompt = PromptTemplate(
            input_variables=["context", "chat_history", "question"],
            template="""
You are a helpful assistant. You are made by Hiamnshu Singh. 
Answer based on the provided context and conversation history.
Also explain as deeply as possible, highlighting the important portions too.
If the content is insufficient, just say you don't know.
But if the users ask for code, make it according to the context but if incomplete , complete yhe code on your own.
If the context contains code, 
reproduce it exactly as it is (keep indentation, spacing, and formatting).  
Do not explain or modify unless explicitly asked.  
Wrap all code inside ```language blocks.
Answer based on context and chat history:

CONTEXT: {context}

CHAT HISTORY: {chat_history}

QUESTION: {question}

ANSWER:"""
        )
        
        # State
        self.vectorstore = None
        self.rag_chain = None
        self.documents_loaded = False
        self.memory: List[Dict] = []
        self.max_memory = 20
    
    def ingest_documents(self, files: List[Any]) -> Dict[str, Any]:
        """Process uploaded files"""
        documents = []
        processed_files = []
        errors = []
        
        for file in files:
            try:
                with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file.filename.split('.')[-1]}") as tmp:
                    shutil.copyfileobj(file.file, tmp)
                    tmp_path = tmp.name
                
                # Load based on file type
                if file.filename.endswith('.pdf'):
                    docs = PyPDFLoader(tmp_path).load()
                elif file.filename.endswith(('.txt', '.md')):
                    docs = TextLoader(tmp_path).load()
                else:
                    with open(tmp_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                    docs = [Document(page_content=content, metadata={"source": file.filename})]
                
                # Add metadata
                for doc in docs:
                    doc.metadata["filename"] = file.filename
                
                documents.extend(docs)
                processed_files.append(file.filename)
                
            except Exception as e:
                errors.append(f"Error with {file.filename}: {str(e)}")
            finally:
                try:
                    os.unlink(tmp_path)
                except:
                    pass
        
        if not documents:
            raise ValueError("No documents processed")
        
        # Create vector store and chain
        chunks = self.text_splitter.split_documents(documents)
        self.vectorstore = FAISS.from_documents(chunks, self.embeddings)
        self._build_chain()
        self.documents_loaded = True
        
        return {
            "processed_files": processed_files,
            "total_chunks": len(chunks),
            "errors": errors,
            "success": True
        }
    
    def _build_chain(self):
        """Build RAG chain"""
        retriever = self.vectorstore.as_retriever(search_kwargs={"k": 4})
        
        def format_docs(docs):
            return "\n\n".join([f"[{doc.metadata.get('filename', 'Unknown')}]\n{doc.page_content}" for doc in docs])
        
        def format_memory():
            if not self.memory:
                return "No previous conversation."
            recent = self.memory[-5:]  # Last 5 exchanges
            return "\n".join([f"Q: {ex['question']}\nA: {ex['response'][:100]}...\n" for ex in recent])
        
        def get_sources(docs):
            return list(set([doc.metadata.get("filename", "Unknown") for doc in docs]))
        
        self.rag_chain = (
            RunnableParallel({
                "context": retriever | RunnableLambda(format_docs),
                "chat_history": RunnableLambda(lambda x: format_memory()),
                "question": RunnablePassthrough(),
                "source_docs": retriever,
            })
            | RunnableParallel({
                "response": self.prompt | self.llm | StrOutputParser(),
                "sources": lambda x: get_sources(x["source_docs"])
            })
        )
    
    def query(self, question: str) -> Dict[str, Any]:
        """Process query with memory"""
        if not self.documents_loaded:
            raise ValueError("No documents loaded")
        
        try:
            result = self.rag_chain.invoke(question)
            
            # Add to memory
            self._add_to_memory(question, result["response"], result["sources"])
            
            return {
                "response": result["response"],
                "sources": result["sources"],
                "num_sources": len(result["sources"]),
                "memory_length": len(self.memory),
                "success": True
            }
        except Exception as e:
            error_msg = f"Error: {str(e)}"
            self._add_to_memory(question, error_msg, [])
            return {
                "response": error_msg,
                "sources": [],
                "num_sources": 0,
                "memory_length": len(self.memory),
                "success": False
            }
    
    def _add_to_memory(self, question: str, response: str, sources: List[str]):
        """Add exchange to memory"""
        import datetime
        self.memory.append({
            "timestamp": datetime.datetime.now().isoformat(),
            "question": question,
            "response": response,
            "sources": sources,
            "exchange_id": len(self.memory) + 1
        })
        
        # Trim memory
        if len(self.memory) > self.max_memory:
            self.memory = self.memory[-self.max_memory:]
    
    # Memory methods
    def get_memory(self) -> List[Dict]:
        return self.memory.copy()
    
    def get_recent_memory(self, n: int = 5) -> List[Dict]:
        return self.memory[-n:] if self.memory else []
    
    def clear_memory(self):
        self.memory = []
    
    def search_memory(self, query: str, limit: int = 5) -> List[Dict]:
        """Simple keyword search in memory"""
        if not self.memory:
            return []
        
        query_lower = query.lower()
        results = []
        
        for ex in self.memory:
            if query_lower in ex["question"].lower() or query_lower in ex["response"].lower():
                results.append(ex)
        
        return results[-limit:]
    
    def get_memory_summary(self) -> Dict[str, Any]:
        return {
            "total_exchanges": len(self.memory),
            "memory_empty": len(self.memory) == 0,
            "memory_full": len(self.memory) >= self.max_memory,
            "latest_exchange_time": self.memory[-1]["timestamp"] if self.memory else None
        }
    
    def set_memory_length(self, length: int):
        self.max_memory = max(1, length)
        if len(self.memory) > self.max_memory:
            self.memory = self.memory[-self.max_memory:]
    
    def query_with_memory_context(self, question: str, use_memory: bool = True) -> Dict[str, Any]:
        if not use_memory:
            old_memory = self.memory
            self.memory = []
            result = self.query(question)
            self.memory = old_memory
            return result
        return self.query(question)
    
    def get_status(self) -> Dict[str, Any]:
        return {
            "documents_loaded": self.documents_loaded,
            "vectorstore_ready": self.vectorstore is not None,
            "rag_chain_ready": self.rag_chain is not None,
            "memory_status": self.get_memory_summary(),
            "max_memory_length": self.max_memory
        }
    
    def reset(self):
        """Reset everything"""
        self.vectorstore = None
        self.rag_chain = None
        self.documents_loaded = False
        self.memory = []

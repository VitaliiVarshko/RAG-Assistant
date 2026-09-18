from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import sys
import os

# Add the parent directory to the path to import multi_lang_qa
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from multi_lang_qa import MultiLangQA
from backend.models import QueryRequest, QueryResponse, HealthResponse, SourceDocument

# Global instance of the RAG system
rag_qa: MultiLangQA = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manages the life cycle of an application. 
Loads the embedding model once at startup.
    """
    global rag_qa
    print("🚀 Starting the backend...")
    
    
    MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY", "")
    
    print("⏳ Loading RAG-system (may take 15-20 seconds)...")
    rag_qa = MultiLangQA(mistral_api_key=MISTRAL_API_KEY)
    print("✅ RAG-system is ready for operation!")
    
    yield  # Здесь приложение работает
    
    print("🛑 Stopping the backend...")

# Создаём приложение FastAPI
app = FastAPI(
    title="RAG API for w34u.net",
    description="Multilingual RAG system for answering questions about the website",
    version="1.0.0",
    lifespan=lifespan
)

# Setting up CORS (so that the site can access the API)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development; in production, specify specific domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/", tags=["Root"])
async def root():
    """Main endpoint for checking the status of the backend"""
    return {
        "message": "RAG API is working!",
        "docs": "/docs",
        "health": "/health"
    }

@app.get("/health", response_model=HealthResponse, tags=["System"])
async def health_check():
    """Checking the backend status and available collections"""
    if rag_qa is None:
        raise HTTPException(status_code=503, detail="RAG-the system is not loaded yet")
    
    collections_stats = {}
    for lang, collection in rag_qa.collections.items():
        if collection:
            collections_stats[lang] = collection.count()
        else:
            collections_stats[lang] = 0
    
    return HealthResponse(
        status="ok",
        collections=collections_stats,
        mistral_available=bool(rag_qa.mistral_api_key)
    )

@app.post("/ask", response_model=QueryResponse, tags=["RAG"])
async def ask_question(request: QueryRequest):
    """
    Main endpoint for question-answer interactions.
    
    Accepts a question, searches for relevant fragments in the database,
    and generates an answer through Mistral or Ollama.
    """
    if rag_qa is None:
        raise HTTPException(status_code=503, detail="RAG-the system is not loaded yet")
    
    try:
        # We receive a response from the RAG system
        answer = rag_qa.answer_question(
            query=request.question,
            top_k=request.top_k,
            generator=request.generator,
            model=request.model,
            fallback_to_translation=request.fallback_to_translation
        )
        
        # We determine the language of the question
        query_lang = rag_qa.detect_language(request.question) or "ru"
        
        # Obtaining sources (for display on the website)
        results = rag_qa.search(request.question, query_lang, request.top_k)
        sources = []
        if results and results['documents']:
            for i, doc in enumerate(results['documents'][0]):
                meta = results['metadatas'][0][i] if results['metadatas'] else {}
                sources.append(SourceDocument(
                    content=doc[:300] + "..." if len(doc) > 300 else doc,
                    url=meta.get("url"),
                    title=meta.get("title"),
                    language=meta.get("language")
                ))
        
        return QueryResponse(
            question=request.question,
            answer=answer,
            language=query_lang,
            sources=sources,
            model=request.model or "mistral-small-latest"
        )
    
    except Exception as e:
        print(f"❌ Error processing question: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing question: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
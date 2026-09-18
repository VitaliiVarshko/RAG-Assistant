from pydantic import BaseModel, Field
from typing import Optional, List

class QueryRequest(BaseModel):
    """Model for user queries"""
    question: str = Field(..., description="User question", min_length=1, max_length=2000)
    top_k: int = Field(5, description="Number of fragments to search", ge=1, le=20)
    generator: str = Field("mistral", description="Generator: 'mistral' or 'ollama'")
    model: Optional[str] = Field(None, description="Model for the generator")
    fallback_to_translation: bool = Field(True, description="Use translation when no results are found")

    class Config:
        json_schema_extra = {
            "example": {
                "question": "What services do you provide?",
                "top_k": 5,
                "generator": "mistral",
                "model": "mistral-small-latest",
                "fallback_to_translation": True
            }
        }

class SourceDocument(BaseModel):
    """Model for found sources"""
    content: str
    url: Optional[str] = None
    title: Optional[str] = None
    language: Optional[str] = None
    score: Optional[float] = None

class QueryResponse(BaseModel):
    """User response model"""
    question: str
    answer: str
    language: str
    sources: List[SourceDocument] = []
    tokens_used: Optional[int] = None
    model: Optional[str] = None

class HealthResponse(BaseModel):
    """Model for health check responses"""
    status: str
    collections: dict
    mistral_available: bool
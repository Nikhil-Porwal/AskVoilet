from pydantic import BaseModel, ConfigDict
from typing import List, Optional, Dict, Any

# --- User & Token Schemas ---

class UserBase(BaseModel):
    username: str

class UserCreate(UserBase):
    password: str

class User(UserBase):
    id: int
    model_config = ConfigDict(from_attributes=True)

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

# --- LLM Configuration Schemas ---

class LLMProvider(BaseModel):
    """Available LLM providers"""
    provider: str  # "gemini" or "openai"
    model_name: Optional[str] = None  # e.g., "gemini-1.5-flash", "gpt-3.5-turbo"

class LLMListResponse(BaseModel):
    """List of available LLM providers"""
    providers: List[Dict[str, Any]]

# --- Application Schemas ---

class DocumentCollectionBase(BaseModel):
    collection_name: str

class DocumentCollectionCreate(DocumentCollectionBase):
    pass

class DocumentCollection(DocumentCollectionBase):
    id: int
    owner_id: int
    vector_store_session_id: str
    llm_provider: Optional[str] = "gemini"
    llm_model: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)

# --- Source Information for Highlighting ---

class SourceInfo(BaseModel):
    """Information about a source for highlighting"""
    source: str
    page: int
    file_path: str
    relevance_score: float
    text_preview: str
    text_blocks: List[Dict[str, Any]]

# --- Proactive Insights Schemas ---

class DocumentInsights(BaseModel):
    """Proactive insights about documents"""
    summary: str
    key_concepts: List[str]
    suggested_questions: List[str]
    document_stats: Dict[str, int]

# --- Upload Schemas ---

class UploadResponse(BaseModel):
    collection: DocumentCollection
    uploaded_files: List[str]
    processing_stats: Optional[Dict[str, Any]] = None
    insights: Optional[DocumentInsights] = None

# --- Chat Schemas ---

class ChatRequest(BaseModel):
    collection_id: int
    question: str
    llm_provider: Optional[str] = None  # Override collection's default
    llm_model: Optional[str] = None

class ChatResponse(BaseModel):
    collection_id: int
    question: str
    answer: str
    type: str  # "document_query" or "table_query"
    sources: List[SourceInfo]
    context_used: Optional[int] = None

class ChatMessage(BaseModel):
    id: int
    role: str
    content: str
    type: str
    sources: List[SourceInfo] = []
    context_used: Optional[int] = None
    created_at: str

# --- Insights Retrieval ---

class InsightsRequest(BaseModel):
    collection_id: int

class InsightsResponse(BaseModel):
    collection_id: int
    insights: DocumentInsights

# --- Table Query Schemas ---

class TableInfo(BaseModel):
    table_index: int
    source: str
    columns: List[str]
    row_count: int

class TablesListResponse(BaseModel):
    collection_id: int
    tables: List[TableInfo]
from sqlalchemy import Column, Integer, String, ForeignKey, Text, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    
    # Default LLM preferences for the user
    preferred_llm_provider = Column(String, default="gemini")
    preferred_llm_model = Column(String, default="gemini-3.8-flash")

    # Relationship: A user can have many collections
    collections = relationship("DocumentCollection", back_populates="owner", cascade="all, delete-orphan")

class DocumentCollection(Base):
    __tablename__ = "document_collections"

    id = Column(Integer, primary_key=True, index=True)
    collection_name = Column(String, index=True)
    
    # UUID for the FAISS vector store
    vector_store_session_id = Column(String, unique=True, index=True) 
    
    # LLM configuration for this collection
    llm_provider = Column(String, default="gemini")
    llm_model = Column(String, default="gemini-3.8-flash")
    
    # Link to user
    owner_id = Column(Integer, ForeignKey("users.id"))
    owner = relationship("User", back_populates="collections")
    messages = relationship("ChatMessage", back_populates="collection", cascade="all, delete-orphan", order_by="ChatMessage.created_at")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    collection_id = Column(Integer, ForeignKey("document_collections.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    message_type = Column(String, default="document_query", nullable=False)
    sources_json = Column(Text, default="[]", nullable=False)
    context_used = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    collection = relationship("DocumentCollection", back_populates="messages")
import uuid
import shutil
import json
from datetime import timezone
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Form
from sqlalchemy.orm import Session
from app.models import schemas, db_models
from app.db.database import get_db
from app.core.dependencies import get_current_user
from app.core.ai import process_files, get_chat_answer, get_insights

router = APIRouter()

# Define base directories
UPLOAD_DIR = Path("storage/uploads")
VECTOR_STORE_DIR = Path("storage/vector_store")

# Gemini's free tier is used by default. OpenAI remains available when configured.
AVAILABLE_LLMS = {
    "gemini": {
        "name": "Google Gemini",
        "models": ["gemini-3.8-flash"],
        "default": "gemini-3.8-flash"
    },
    "openai": {
        "name": "OpenAI GPT",
        "models": ["gpt-3.5-turbo", "gpt-4o-mini", "gpt-4", "gpt-4-turbo", "gpt-4o"],
        "default": "gpt-3.5-turbo"
    }
}


@router.get("/llm-providers", response_model=schemas.LLMListResponse)
async def get_llm_providers():
    """
    Get list of available LLM providers and their models.
    """
    providers = []
    for key, value in AVAILABLE_LLMS.items():
        providers.append({
            "id": key,
            "name": value["name"],
            "models": value["models"],
            "default_model": value["default"]
        })
    
    return {"providers": providers}


@router.post("/upload", response_model=schemas.UploadResponse)
async def upload_files(
    files: List[UploadFile] = File(...),
    collection_name: str = Form(...),
    llm_provider: str = Form("gemini"),
    llm_model: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_user)
):
    """
    Upload and process multiple PDF files with enhanced features:
    - Multi-document support with metadata
    - Table extraction
    - Image detection
    - Proactive insights generation
    - LLM selection
    """
    
    # Validate LLM provider
    if llm_provider not in AVAILABLE_LLMS:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid LLM provider. Available: {list(AVAILABLE_LLMS.keys())}"
        )
    
    # Set default model if not provided
    if not llm_model:
        llm_model = AVAILABLE_LLMS[llm_provider]["default"]
    
    # Generate unique session ID
    vector_store_session_id = str(uuid.uuid4())
    session_upload_dir = UPLOAD_DIR / vector_store_session_id
    session_upload_dir.mkdir(parents=True, exist_ok=True)
    
    uploaded_filenames = []

    try:
        # Save uploaded files temporarily
        file_paths = []
        for file in files:
            if not file.filename:
                continue
            
            # Only accept PDF files
            if not file.filename.lower().endswith('.pdf'):
                raise HTTPException(
                    status_code=400,
                    detail=f"Only PDF files are supported. Invalid file: {file.filename}"
                )
            
            file_path = session_upload_dir / file.filename
            uploaded_filenames.append(file.filename)
            
            with file_path.open("wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            
            file_paths.append(file_path)
        
        if not file_paths:
            raise HTTPException(status_code=400, detail="No valid PDF files uploaded")
        
        # Process files with AI logic
        vector_store_path = VECTOR_STORE_DIR / vector_store_session_id
        processing_result = process_files(
            file_paths=file_paths,
            vector_store_path=vector_store_path,
            llm_provider=llm_provider,
            llm_model=llm_model
        )
        
        # Create new DocumentCollection in database
        new_collection = db_models.DocumentCollection(
            collection_name=collection_name,
            vector_store_session_id=vector_store_session_id,
            llm_provider=llm_provider,
            llm_model=llm_model,
            owner_id=current_user.id
        )
        db.add(new_collection)
        db.commit()
        db.refresh(new_collection)
        
        # Prepare insights for response
        insights = None
        if "insights" in processing_result:
            insights = schemas.DocumentInsights(**processing_result["insights"])
        
        # Return response
        return schemas.UploadResponse(
            collection=new_collection,
            uploaded_files=uploaded_filenames,
            processing_stats={
                "chunks_created": processing_result.get("chunks_created", 0),
                "tables_extracted": processing_result.get("tables_extracted", 0),
                "images_found": processing_result.get("images_found", 0)
            },
            insights=insights
        )

    except Exception as e:
        # Clean up on failure
        shutil.rmtree(session_upload_dir, ignore_errors=True)
        vector_store_cleanup = VECTOR_STORE_DIR / vector_store_session_id
        shutil.rmtree(vector_store_cleanup, ignore_errors=True)
        
        raise HTTPException(
            status_code=500, 
            detail=f"File processing failed: {str(e)}"
        )
    
    finally:
        # Clean up temporary uploaded files
        shutil.rmtree(session_upload_dir, ignore_errors=True)


@router.post("/chat", response_model=schemas.ChatResponse)
async def chat_with_collection(
    request: schemas.ChatRequest,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_user)
):
    """
    Chat with a document collection - enhanced with:
    - Source highlighting information
    - Multi-document synthesis
    - Table querying
    - LLM selection override
    """
    
    # Find collection
    collection = db.query(db_models.DocumentCollection).filter(
        db_models.DocumentCollection.id == request.collection_id
    ).first()

    # Verify ownership
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")
    if collection.owner_id != current_user.id:
        raise HTTPException(
            status_code=403, 
            detail="Not authorized to access this collection"
        )

    # Determine LLM to use (request override or collection default)
    llm_provider = request.llm_provider or collection.llm_provider
    llm_model = request.llm_model or collection.llm_model
    
    # Get vector store path
    vector_store_path = VECTOR_STORE_DIR / collection.vector_store_session_id
    
    if not vector_store_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Vector store not found. Collection may be corrupted."
        )
    
    try:
        # Get answer with sources
        result = get_chat_answer(
            question=request.question,
            vector_store_path=vector_store_path,
            llm_provider=llm_provider,
            llm_model=llm_model
        )
        
        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])
        
        # Convert sources to schema format
        sources = [schemas.SourceInfo(**source) for source in result.get("sources", [])]
        
        user_message = db_models.ChatMessage(
            collection_id=collection.id,
            role="user",
            content=request.question,
            message_type=result.get("type", "document_query"),
            sources_json="[]",
            context_used=result.get("context_used"),
        )
        assistant_message = db_models.ChatMessage(
            collection_id=collection.id,
            role="assistant",
            content=result["answer"],
            message_type=result.get("type", "document_query"),
            sources_json=json.dumps(result.get("sources", [])),
            context_used=result.get("context_used"),
        )
        db.add_all([user_message, assistant_message])
        db.commit()

        return schemas.ChatResponse(
            collection_id=request.collection_id,
            question=request.question,
            answer=result["answer"],
            type=result.get("type", "document_query"),
            sources=sources,
            context_used=result.get("context_used")
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Chat processing failed: {str(e)}"
        )


@router.get("/collections/{collection_id}/messages", response_model=List[schemas.ChatMessage])
async def get_collection_messages(
    collection_id: int,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_user)
):
    """Return the persisted conversation for a collection."""
    collection = db.query(db_models.DocumentCollection).filter(
        db_models.DocumentCollection.id == collection_id
    ).first()

    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")
    if collection.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this collection")

    messages = db.query(db_models.ChatMessage).filter(
        db_models.ChatMessage.collection_id == collection_id
    ).order_by(db_models.ChatMessage.created_at, db_models.ChatMessage.id).all()

    return [
        schemas.ChatMessage(
            id=message.id,
            role=message.role,
            content=message.content,
            type=message.message_type,
            sources=[schemas.SourceInfo(**source) for source in json.loads(message.sources_json or "[]")],
            context_used=message.context_used,
            created_at=(message.created_at.replace(tzinfo=timezone.utc).isoformat()
                        if message.created_at.tzinfo is None else message.created_at.isoformat()),
        )
        for message in messages
    ]


@router.get("/insights/{collection_id}", response_model=schemas.InsightsResponse)
async def get_collection_insights(
    collection_id: int,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_user)
):
    """
    Get proactive insights for a collection:
    - Document summary
    - Key concepts
    - Suggested questions
    - Statistics
    """
    
    # Find collection
    collection = db.query(db_models.DocumentCollection).filter(
        db_models.DocumentCollection.id == collection_id
    ).first()

    # Verify ownership
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")
    if collection.owner_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Not authorized to access this collection"
        )
    
    # Get insights
    vector_store_path = VECTOR_STORE_DIR / collection.vector_store_session_id
    insights_data = get_insights(vector_store_path)
    
    if "error" in insights_data:
        raise HTTPException(status_code=404, detail=insights_data["error"])
    
    return schemas.InsightsResponse(
        collection_id=collection_id,
        insights=schemas.DocumentInsights(**insights_data)
    )


@router.get("/collections", response_model=List[schemas.DocumentCollection])
async def list_collections(
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_user)
):
    """
    List all collections for the current user.
    """
    collections = db.query(db_models.DocumentCollection).filter(
        db_models.DocumentCollection.owner_id == current_user.id
    ).all()
    
    return collections


@router.delete("/collections/{collection_id}")
async def delete_collection(
    collection_id: int,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_user)
):
    """
    Delete a collection and its associated vector store.
    """
    # Find collection
    collection = db.query(db_models.DocumentCollection).filter(
        db_models.DocumentCollection.id == collection_id
    ).first()

    # Verify ownership
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")
    if collection.owner_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Not authorized to delete this collection"
        )
    
    # Delete vector store files
    vector_store_path = VECTOR_STORE_DIR / collection.vector_store_session_id
    shutil.rmtree(vector_store_path, ignore_errors=True)
    
    # Delete from database
    db.delete(collection)
    db.commit()
    
    return {"message": "Collection deleted successfully"}

@router.delete("/collections")
async def delete_all_collections(
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_user)
):
    """
    Delete ALL collections for the current user (bulk delete).
    """
    # Get all collections for user
    collections = db.query(db_models.DocumentCollection).filter(
        db_models.DocumentCollection.owner_id == current_user.id
    ).all()
    
    if not collections:
        return {"message": "No collections found", "deleted_count": 0}
    
    deleted_count = 0
    errors = []
    
    # Delete each collection
    for collection in collections:
        try:
            # Delete vector store files
            vector_store_path = VECTOR_STORE_DIR / collection.vector_store_session_id
            shutil.rmtree(vector_store_path, ignore_errors=True)
            
            # Delete from database
            db.delete(collection)
            deleted_count += 1
        except Exception as e:
            errors.append(f"Failed to delete collection {collection.id}: {str(e)}")
    
    # Commit all deletions
    db.commit()
    
    response = {
        "message": f"Successfully deleted {deleted_count} collection(s)",
        "deleted_count": deleted_count
    }
    
    if errors:
        response["errors"] = errors
    
    return response

@router.get("/collections/{collection_id}/tables", response_model=schemas.TablesListResponse)
async def list_tables(
    collection_id: int,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_user)
):
    """
    List all extracted tables from a collection.
    """
    # Find collection
    collection = db.query(db_models.DocumentCollection).filter(
        db_models.DocumentCollection.id == collection_id
    ).first()

    # Verify ownership
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")
    if collection.owner_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Not authorized to access this collection"
        )
    
    # Load tables data
    vector_store_path = VECTOR_STORE_DIR / collection.vector_store_session_id
    tables_path = vector_store_path / "tables.json"
    
    if not tables_path.exists():
        return schemas.TablesListResponse(collection_id=collection_id, tables=[])
    
    with open(tables_path, "r") as f:
        tables_data = json.load(f)
    
    # Convert to response format
    tables = [
        schemas.TableInfo(
            table_index=t["table_index"],
            source=t["source"],
            columns=t["columns"],
            row_count=len(t["data"])
        )
        for t in tables_data
    ]
    
    return schemas.TablesListResponse(collection_id=collection_id, tables=tables)
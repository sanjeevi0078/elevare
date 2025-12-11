"""
Admin API - Knowledge Base Management

Provides endpoints for:
1. Document ingestion (PDF, TXT, MD)
2. Knowledge base querying
3. Knowledge base statistics and management
"""

import logging
from typing import Optional, List

from fastapi import APIRouter, UploadFile, File, HTTPException, Query, Depends
from pydantic import BaseModel, Field

from services.knowledge_base import KnowledgeBaseService, IngestionResult, QueryResult

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["Admin - Knowledge Base"])


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class TextIngestionRequest(BaseModel):
    """Request body for text ingestion."""
    text: str = Field(..., min_length=10, description="Raw text content to ingest")
    source_name: str = Field(default="manual_input", description="Name for the source")


class DeleteDocumentRequest(BaseModel):
    """Request to delete a document by ID."""
    document_id: str = Field(..., description="Document ID to delete")


class KnowledgeQueryRequest(BaseModel):
    """Request body for knowledge base query."""
    query: str = Field(..., min_length=3, description="Search query")
    n_results: int = Field(default=3, ge=1, le=10, description="Number of results")


# ============================================================================
# DEPENDENCY
# ============================================================================

def get_knowledge_service() -> KnowledgeBaseService:
    """Dependency to get the knowledge base service singleton."""
    return KnowledgeBaseService()


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.post("/ingest", response_model=IngestionResult)
async def ingest_document(
    file: UploadFile = File(..., description="PDF, TXT, or MD file to ingest"),
    service: KnowledgeBaseService = Depends(get_knowledge_service)
) -> IngestionResult:
    """
    Upload and ingest a document into the knowledge base.
    
    Supported formats:
    - PDF (.pdf) - Extracts text from all pages
    - Text (.txt) - Plain text files
    - Markdown (.md, .markdown) - Markdown documents
    
    The document will be:
    1. Parsed and text extracted
    2. Split into chunks (1000 chars with 200 overlap)
    3. Embedded using all-MiniLM-L6-v2
    4. Stored in ChromaDB for semantic search
    
    Returns ingestion result with chunk count and document ID.
    """
    logger.info(f"📥 Received file upload: {file.filename}")
    
    result = await service.ingest_document(file)
    
    if not result.success:
        logger.warning(f"Ingestion failed: {result.message}")
        raise HTTPException(status_code=400, detail=result.message)
    
    logger.info(f"✅ Ingested {result.chunks_created} chunks from {file.filename}")
    return result


@router.post("/ingest/text", response_model=IngestionResult)
async def ingest_text(
    request: TextIngestionRequest,
    service: KnowledgeBaseService = Depends(get_knowledge_service)
) -> IngestionResult:
    """
    Ingest raw text directly into the knowledge base.
    
    Useful for:
    - Adding content programmatically
    - Ingesting scraped web content
    - Adding manual knowledge entries
    """
    result = service.ingest_text(request.text, request.source_name)
    
    if not result.success:
        raise HTTPException(status_code=400, detail=result.message)
    
    return result


@router.post("/query", response_model=QueryResult)
async def query_knowledge(
    request: KnowledgeQueryRequest,
    service: KnowledgeBaseService = Depends(get_knowledge_service)
) -> QueryResult:
    """
    Query the knowledge base for relevant information.
    
    Uses semantic similarity search to find the most relevant
    document chunks for the given query.
    """
    result = service.query_knowledge(request.query, request.n_results)
    return result


@router.get("/query")
async def query_knowledge_get(
    q: str = Query(..., min_length=3, description="Search query"),
    n: int = Query(default=3, ge=1, le=10, description="Number of results"),
    service: KnowledgeBaseService = Depends(get_knowledge_service)
) -> QueryResult:
    """
    Query the knowledge base (GET version for easy testing).
    
    Example: GET /admin/query?q=how%20to%20raise%20funding&n=5
    """
    result = service.query_knowledge(q, n)
    return result


@router.get("/stats")
async def get_knowledge_stats(
    service: KnowledgeBaseService = Depends(get_knowledge_service)
):
    """
    Get statistics about the knowledge base.
    
    Returns:
    - Total chunks stored
    - Storage path
    - Embedding model info
    - Chunking configuration
    """
    stats = service.get_stats()
    return {
        "status": "healthy",
        "knowledge_base": stats
    }


@router.delete("/document/{document_id}")
async def delete_document(
    document_id: str,
    service: KnowledgeBaseService = Depends(get_knowledge_service)
):
    """
    Delete a document and all its chunks from the knowledge base.
    
    Use the document_id returned from the ingestion endpoint.
    """
    success = service.delete_document(document_id)
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete document")
    
    return {"success": True, "message": f"Document {document_id} deleted"}


@router.delete("/clear")
async def clear_knowledge_base(
    confirm: bool = Query(False, description="Set to true to confirm deletion"),
    service: KnowledgeBaseService = Depends(get_knowledge_service)
):
    """
    Clear all documents from the knowledge base.
    
    ⚠️ WARNING: This is destructive and cannot be undone!
    
    Requires `confirm=true` query parameter.
    """
    if not confirm:
        raise HTTPException(
            status_code=400,
            detail="Add ?confirm=true to confirm deletion of all documents"
        )
    
    success = service.clear_all()
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to clear knowledge base")
    
    return {"success": True, "message": "Knowledge base cleared"}


# ============================================================================
# HEALTH CHECK
# ============================================================================

@router.get("/health")
async def admin_health():
    """Health check for admin endpoints."""
    return {
        "status": "healthy",
        "service": "knowledge_base",
        "pdf_support": True  # Will be updated dynamically
    }

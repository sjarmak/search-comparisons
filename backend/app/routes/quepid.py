"""
Quepid API routes for the search-comparisons application.
"""
from fastapi import APIRouter, HTTPException, Query
from typing import List, Dict, Any
from ..services.quepid_service import QuepidService

router = APIRouter(
    tags=["quepid"],
    responses={404: {"description": "Not found"}}
)
quepid_service = QuepidService()

@router.get("/judgments/{case_id}")
async def get_judgments(
    case_id: int,
    query: str = Query(..., description="The search query to get judgments for")
) -> List[Dict[str, Any]]:
    """
    Get judged documents for a specific Quepid case and query.
    
    Args:
        case_id: The Quepid case ID
        query: The search query to get judgments for
        
    Returns:
        List[Dict[str, Any]]: List of judged documents with their metadata and scores
    """
    try:
        documents = await quepid_service.get_judged_documents_by_text(case_id, query)
        return documents
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error getting Quepid judgments: {str(e)}"
        )

@router.get("/documents")
async def get_judged_documents(
    case_id: int = Query(8914, description="The Quepid case ID"),
    query_text: str = Query("triton", description="The query text to match")
) -> List[Dict[str, Any]]:
    """
    Get judged documents from Quepid for a specific case and query.
    
    Args:
        case_id: The Quepid case ID (default: 8914)
        query_text: The query text to match (default: "triton")
    
    Returns:
        List[Dict[str, Any]]: List of documents with their judgments and metadata
    """
    try:
        documents = await quepid_service.get_judged_documents_by_text(case_id, query_text)
        return documents
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error getting Quepid documents: {str(e)}"
        ) 
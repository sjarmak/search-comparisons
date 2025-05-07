"""
Quepid API routes for the search-comparisons application.
"""
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Query
from ...services.quepid_service import QuepidService

router = APIRouter()
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
        judgments = await quepid_service.get_judged_documents_by_text(case_id, query)
        return judgments
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error getting Quepid judgments: {str(e)}"
        ) 
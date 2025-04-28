from fastapi import APIRouter, HTTPException
from typing import List, Optional
from ..services.quepid_service import QuepidService

router = APIRouter()
quepid_service = QuepidService()

@router.get("/documents", response_model=List[dict])
async def get_judged_documents(case_id: int = 8862, query_id: Optional[int] = None):
    """
    Get judged documents from Quepid for the weak lensing query.
    
    Args:
        case_id: The Quepid case ID (default: 8862)
        query_id: Optional query ID to filter by specific query
    
    Returns:
        List[dict]: List of documents with their judgments and metadata
    """
    try:
        documents = await quepid_service.get_judged_documents(case_id, query_id)
        return documents
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 
from fastapi import APIRouter, HTTPException
from typing import List
from ..services.quepid_service import QuepidService

router = APIRouter(
    tags=["quepid"],
    responses={404: {"description": "Not found"}}
)
quepid_service = QuepidService()

@router.get("/documents", response_model=List[dict])
async def get_judged_documents(case_id: int = 8914, query_text: str = "triton"):
    """
    Get judged documents from Quepid for a specific case and query.
    
    Args:
        case_id: The Quepid case ID (default: 8914)
        query_text: The query text to match (default: "triton")
    
    Returns:
        List[dict]: List of documents with their judgments and metadata
    """
    try:
        documents = await quepid_service.get_judged_documents_by_text(case_id, query_text)
        return documents
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 
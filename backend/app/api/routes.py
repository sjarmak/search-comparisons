from fastapi import APIRouter, HTTPException
from typing import Dict, Any
from ..services.query_intent_service import QueryIntentService

# Create router instance
router = APIRouter()

@router.post("/intent-transform-query")
async def transform_query_intent(query_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Transform a search query using the LLM service to understand user intent.
    
    Args:
        query_data: Dictionary containing the original query
        
    Returns:
        Dict containing the transformed query and metadata
    """
    try:
        query_intent_service = QueryIntentService()
        result = await query_intent_service.transform_query(query_data["query"])
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Export the router
__all__ = ['router']

# ... existing code ... 
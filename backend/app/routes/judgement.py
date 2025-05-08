"""API routes for judgement operations."""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.api.schemas.judgement import (
    JudgementCreate,
    JudgementResponse,
    JudgementStats,
    JudgementBatchCreate,
)
from app.core.database import get_db
from app.services.judgement_service import JudgementService
from app.services.session_service import get_current_rater_id

router = APIRouter(prefix="/judgements", tags=["judgements"])


@router.get("/query/all", response_model=List[JudgementResponse])
async def get_all_judgements(
    db: Session = Depends(get_db),
) -> List[JudgementResponse]:
    """Get all judgements in the database.

    Args:
        db: Database session.

    Returns:
        List[JudgementResponse]: List of all judgements.
    """
    service = JudgementService(db)
    return service.get_all_judgements()


@router.post("", response_model=JudgementResponse)
async def create_judgement(
    judgement: JudgementCreate,
    request: Request,
    db: Session = Depends(get_db),
) -> JudgementResponse:
    """Create a new judgement.

    Args:
        judgement: The judgement data to create.
        request: The FastAPI request object.
        db: Database session.

    Returns:
        JudgementResponse: The created judgement.
    """
    rater_id = get_current_rater_id(request)
    service = JudgementService(db)
    return service.create_judgement(
        rater_id=rater_id,
        query=judgement.query,
        information_need=judgement.information_need,
        record_title=judgement.record_title,
        publication_year=judgement.publication_year,
        record_bibcode=judgement.record_bibcode,
        record_source=judgement.record_source,
        judgement_score=judgement.judgement_score,
        judgement_note=judgement.judgement_note,
    )


@router.post("/batch", response_model=List[JudgementResponse])
async def create_judgements_batch(
    batch: JudgementBatchCreate,
    request: Request,
    db: Session = Depends(get_db),
) -> List[JudgementResponse]:
    """Create multiple judgements in a batch.

    Args:
        batch: The batch of judgements to create.
        request: The FastAPI request object.
        db: Database session.

    Returns:
        List[JudgementResponse]: List of created judgements.
    """
    rater_id = get_current_rater_id(request)
    service = JudgementService(db)
    created_judgements = []
    
    for judgement in batch.judgements:
        created = service.create_judgement(
            rater_id=rater_id,
            query=judgement.query,
            information_need=judgement.information_need,
            record_title=judgement.record_title,
            publication_year=judgement.publication_year,
            record_bibcode=judgement.record_bibcode,
            record_source=judgement.record_source,
            judgement_score=judgement.judgement_score,
            judgement_note=judgement.judgement_note,
        )
        created_judgements.append(created)
    
    return created_judgements


@router.get("/query/{query}", response_model=List[JudgementResponse])
async def get_judgements_by_query(
    query: str,
    record_bibcode: str | None = None,
    db: Session = Depends(get_db),
) -> List[JudgementResponse]:
    """Get all judgements for a specific query.

    Args:
        query: The search query to find judgements for.
        record_bibcode: Optional ADS bibcode to filter by.
        db: Database session.

    Returns:
        List[JudgementResponse]: List of matching judgements.
    """
    service = JudgementService(db)
    return service.get_judgements_by_query(query, record_bibcode)


@router.get("/stats/{query}", response_model=JudgementStats)
async def get_judgement_stats(
    query: str,
    db: Session = Depends(get_db),
) -> JudgementStats:
    """Get statistics about judgements for a query.

    Args:
        query: The search query to get stats for.
        db: Database session.

    Returns:
        JudgementStats: Statistics about the judgements.
    """
    service = JudgementService(db)
    return service.get_judgement_stats(query)


@router.get("/rater", response_model=List[JudgementResponse])
async def get_my_judgements(
    request: Request,
    db: Session = Depends(get_db),
) -> List[JudgementResponse]:
    """Get all judgements made by the current rater.

    Args:
        request: The FastAPI request object.
        db: Database session.

    Returns:
        List[JudgementResponse]: List of judgements made by the rater.
    """
    rater_id = get_current_rater_id(request)
    service = JudgementService(db)
    return service.get_judgements_by_rater(rater_id) 
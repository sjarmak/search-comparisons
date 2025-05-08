"""Pydantic schemas for judgement API endpoints."""

from datetime import datetime
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel, Field


class JudgementBase(BaseModel):
    """Base schema for judgement data."""

    query: str = Field(..., description="The search query that produced the result")
    information_need: str = Field(..., description="The information need being judged")
    record_title: str = Field(..., description="Title of the judged record")
    publication_year: Optional[int] = Field(None, description="Year of publication")
    record_bibcode: Optional[str] = Field(None, description="ADS bibcode if available")
    record_source: str = Field(..., description="Source of the record (e.g., ADS, Google Scholar)")
    judgement_score: float = Field(..., ge=0, le=1, description="Score given by the rater")
    judgement_note: Optional[str] = Field(None, description="Optional note from the rater")


class JudgementCreate(JudgementBase):
    """Schema for creating a new judgement."""

    pass


class JudgementResponse(JudgementBase):
    """Schema for judgement response."""

    id: UUID
    rater_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        """Pydantic model configuration."""

        from_attributes = True


class JudgementStats(BaseModel):
    """Schema for judgement statistics."""

    total_judgements: int
    average_score: Optional[float]
    unique_raters: int
    source_distribution: dict[str, int]


class JudgementBatchCreate(BaseModel):
    """Schema for creating multiple judgements in a batch."""

    judgements: List[JudgementCreate] = Field(..., description="List of judgements to create") 
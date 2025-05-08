"""Judgement model for SQLAlchemy."""

from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import Column, String, Float, Integer, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PGUUID

from app.core.database import Base


class Judgement(Base):
    """SQLAlchemy model for judgements."""

    __tablename__ = "judgements"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    rater_id = Column(PGUUID(as_uuid=True), nullable=False)
    query = Column(String, nullable=False)
    information_need = Column(String, nullable=False)
    record_title = Column(String, nullable=False)
    publication_year = Column(Integer, nullable=True)
    record_bibcode = Column(String, nullable=True)
    record_source = Column(String, nullable=False)
    judgement_score = Column(Float, nullable=False)
    judgement_note = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self) -> str:
        """Return a string representation of the judgement.

        Returns:
            str: String representation of the judgement.
        """
        return (
            f"<Judgement(id={self.id}, rater_id={self.rater_id}, "
            f"query='{self.query[:50]}...', score={self.judgement_score})>"
        ) 
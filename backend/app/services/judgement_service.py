"""Service for managing search result judgements."""

from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime

from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.models.judgement import Judgement


class JudgementService:
    """Service for managing search result judgements.

    This service handles the creation, retrieval, and analysis of judgements
    made by raters on search results.
    """

    def __init__(self, db: Session) -> None:
        """Initialize the judgement service.

        Args:
            db: SQLAlchemy database session.
        """
        self.db = db

    def get_all_judgements(self) -> List[Judgement]:
        """Get all judgements in the database.

        Returns:
            List[Judgement]: List of all judgements.
        """
        return self.db.query(Judgement).all()

    def create_judgement(
        self,
        rater_id: UUID,
        query: str,
        information_need: str,
        record_title: str,
        publication_year: Optional[int],
        record_bibcode: Optional[str],
        record_source: str,
        judgement_score: float,
        judgement_note: Optional[str] = None,
    ) -> Judgement:
        """Create a new judgement.

        Args:
            rater_id: Unique identifier for the rater.
            query: The search query that produced the result.
            information_need: The information need being judged.
            record_title: Title of the judged record.
            publication_year: Year of publication.
            record_bibcode: ADS bibcode if available.
            record_source: Source of the record (e.g., ADS, Google Scholar).
            judgement_score: Score given by the rater.
            judgement_note: Optional note from the rater.

        Returns:
            Judgement: The created judgement.
        """
        judgement = Judgement(
            rater_id=rater_id,
            query=query,
            information_need=information_need,
            record_title=record_title,
            publication_year=publication_year,
            record_bibcode=record_bibcode,
            record_source=record_source,
            judgement_score=judgement_score,
            judgement_note=judgement_note,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        self.db.add(judgement)
        self.db.commit()
        self.db.refresh(judgement)
        return judgement

    def get_judgements_by_query(
        self, query: str, record_bibcode: Optional[str] = None
    ) -> List[Judgement]:
        """Get all judgements for a specific query and optionally a specific record.

        Args:
            query: The search query to find judgements for.
            record_bibcode: Optional ADS bibcode to filter by.

        Returns:
            List[Judgement]: List of matching judgements.
        """
        filters = [Judgement.query == query]
        if record_bibcode:
            filters.append(Judgement.record_bibcode == record_bibcode)
        return self.db.query(Judgement).filter(*filters).all()

    def get_judgements_by_rater(self, rater_id: UUID) -> List[Judgement]:
        """Get all judgements made by a specific rater.

        Args:
            rater_id: The rater's unique identifier.

        Returns:
            List[Judgement]: List of judgements made by the rater.
        """
        return self.db.query(Judgement).filter(Judgement.rater_id == rater_id).all()

    def get_average_score(
        self, query: str, record_bibcode: Optional[str] = None
    ) -> Optional[float]:
        """Calculate the average judgement score for a query/record pair.

        Args:
            query: The search query.
            record_bibcode: Optional ADS bibcode to filter by.

        Returns:
            Optional[float]: The average score, or None if no judgements exist.
        """
        judgements = self.get_judgements_by_query(query, record_bibcode)
        if not judgements:
            return None
        return sum(j.judgement_score for j in judgements) / len(judgements)

    def get_judgement_stats(self, query: str) -> Dict[str, Any]:
        """Get statistics about judgements for a query.

        Args:
            query: The search query to get stats for.

        Returns:
            Dict[str, Any]: Dictionary containing judgement statistics.
        """
        judgements = self.get_judgements_by_query(query)
        if not judgements:
            return {
                "total_judgements": 0,
                "average_score": None,
                "unique_raters": 0,
                "source_distribution": {},
            }

        scores = [j.judgement_score for j in judgements]
        rater_ids = {j.rater_id for j in judgements}
        sources = {}
        for j in judgements:
            sources[j.record_source] = sources.get(j.record_source, 0) + 1

        return {
            "total_judgements": len(judgements),
            "average_score": sum(scores) / len(scores),
            "unique_raters": len(rater_ids),
            "source_distribution": sources,
        }

    def get_judgements_by_title(self, title: str) -> List[Judgement]:
        """Get all judgements for a specific record title.

        Args:
            title: The record title to find judgements for.

        Returns:
            List[Judgement]: List of matching judgements.
        """
        return self.db.query(Judgement).filter(Judgement.record_title == title).all()

    def get_judgements_for_enrichment(
        self, 
        titles: List[str], 
        bibcodes: Optional[List[str]] = None
    ) -> Dict[str, List[Judgement]]:
        """Get judgements for enriching search results.

        Args:
            titles: List of record titles to find judgements for.
            bibcodes: Optional list of ADS bibcodes to find judgements for.

        Returns:
            Dict[str, List[Judgement]]: Dictionary mapping record identifiers to their judgements.
        """
        # Build query filters
        filters = []
        if titles:
            filters.append(Judgement.record_title.in_(titles))
        if bibcodes:
            filters.append(Judgement.record_bibcode.in_(bibcodes))

        if not filters:
            return {}

        # Get all matching judgements
        judgements = self.db.query(Judgement).filter(or_(*filters)).all()

        # Group judgements by record identifier
        result = {}
        for judgement in judgements:
            # Use bibcode as primary identifier if available, otherwise use title
            key = judgement.record_bibcode or judgement.record_title
            if key not in result:
                result[key] = []
            result[key].append(judgement)

        return result

    def get_judgements_by_session(
        self, 
        rater_id: UUID,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[Judgement]:
        """Get all judgements made in a specific session.

        Args:
            rater_id: The rater's unique identifier.
            start_time: Optional start time of the session.
            end_time: Optional end time of the session.

        Returns:
            List[Judgement]: List of judgements made in the session.
        """
        query = self.db.query(Judgement).filter(Judgement.rater_id == rater_id)
        
        if start_time:
            query = query.filter(Judgement.created_at >= start_time)
        if end_time:
            query = query.filter(Judgement.created_at <= end_time)
            
        return query.order_by(Judgement.created_at).all() 
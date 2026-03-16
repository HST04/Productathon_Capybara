"""Signal Service for CRUD operations on Signal model."""

from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
import uuid

from app.models.signal import Signal


class SignalService:
    """Service for managing Signal database operations."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_signal(
        self,
        url: str,
        content: str,
        title: Optional[str] = None,
        source_id: Optional[uuid.UUID] = None,
        provenance: Optional[Dict[str, Any]] = None
    ) -> Signal:
        """
        Create a new signal in the database.
        
        Args:
            url: URL where the content was found
            content: Full text content of the signal
            title: Optional title of the content
            source_id: Optional ID of the source this signal came from
            provenance: Optional metadata about how the signal was obtained
        
        Returns:
            Created Signal object
        """
        signal = Signal(
            url=url,
            content=content,
            title=title,
            source_id=source_id,
            provenance=provenance,
            processed=False
        )
        
        self.db.add(signal)
        self.db.commit()
        self.db.refresh(signal)
        
        return signal
    
    def get_signal_by_id(self, signal_id: uuid.UUID) -> Optional[Signal]:
        """
        Get a signal by its ID.
        
        Args:
            signal_id: UUID of the signal
        
        Returns:
            Signal object if found, None otherwise
        """
        return self.db.query(Signal).filter(Signal.id == signal_id).first()
    
    def get_signal_by_url(self, url: str) -> Optional[Signal]:
        """
        Get a signal by its URL.
        
        Args:
            url: URL to search for
        
        Returns:
            Signal object if found, None otherwise
        """
        return self.db.query(Signal).filter(Signal.url == url).first()
    
    def list_signals(
        self,
        processed: Optional[bool] = None,
        source_id: Optional[uuid.UUID] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Signal]:
        """
        List signals with optional filters.
        
        Args:
            processed: Filter by processed status (None = all)
            source_id: Filter by source ID (None = all sources)
            limit: Maximum number of results
            offset: Number of results to skip
        
        Returns:
            List of Signal objects
        """
        query = self.db.query(Signal)
        
        if processed is not None:
            query = query.filter(Signal.processed == processed)
        
        if source_id is not None:
            query = query.filter(Signal.source_id == source_id)
        
        # Order by ingestion time (newest first)
        query = query.order_by(Signal.ingested_at.desc())
        
        return query.limit(limit).offset(offset).all()
    
    def get_unprocessed_signals(self, limit: int = 100) -> List[Signal]:
        """
        Get unprocessed signals for the background worker.
        
        Args:
            limit: Maximum number of signals to return
        
        Returns:
            List of unprocessed Signal objects
        """
        return (
            self.db.query(Signal)
            .filter(Signal.processed == False)
            .order_by(Signal.ingested_at.asc())  # Process oldest first
            .limit(limit)
            .all()
        )
    
    def mark_as_processed(self, signal_id: uuid.UUID) -> bool:
        """
        Mark a signal as processed.
        
        Args:
            signal_id: UUID of the signal
        
        Returns:
            True if updated, False if signal not found
        """
        signal = self.get_signal_by_id(signal_id)
        
        if signal:
            signal.processed = True
            signal.processed_at = datetime.utcnow()
            self.db.commit()
            return True
        
        return False
    
    def update_signal(
        self,
        signal_id: uuid.UUID,
        title: Optional[str] = None,
        content: Optional[str] = None,
        processed: Optional[bool] = None
    ) -> Optional[Signal]:
        """
        Update a signal's fields.
        
        Args:
            signal_id: UUID of the signal
            title: New title (if provided)
            content: New content (if provided)
            processed: New processed status (if provided)
        
        Returns:
            Updated Signal object if found, None otherwise
        """
        signal = self.get_signal_by_id(signal_id)
        
        if not signal:
            return None
        
        if title is not None:
            signal.title = title
        
        if content is not None:
            signal.content = content
        
        if processed is not None:
            signal.processed = processed
            if processed:
                signal.processed_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(signal)
        
        return signal
    
    def delete_signal(self, signal_id: uuid.UUID) -> bool:
        """
        Delete a signal from the database.
        
        Args:
            signal_id: UUID of the signal
        
        Returns:
            True if deleted, False if signal not found
        """
        signal = self.get_signal_by_id(signal_id)
        
        if signal:
            self.db.delete(signal)
            self.db.commit()
            return True
        
        return False
    
    def count_signals(
        self,
        processed: Optional[bool] = None,
        source_id: Optional[uuid.UUID] = None
    ) -> int:
        """
        Count signals with optional filters.
        
        Args:
            processed: Filter by processed status (None = all)
            source_id: Filter by source ID (None = all sources)
        
        Returns:
            Count of matching signals
        """
        query = self.db.query(Signal)
        
        if processed is not None:
            query = query.filter(Signal.processed == processed)
        
        if source_id is not None:
            query = query.filter(Signal.source_id == source_id)
        
        return query.count()
    
    def bulk_create_signals(self, signals_data: List[Dict[str, Any]]) -> List[Signal]:
        """
        Create multiple signals in a single transaction.
        
        Args:
            signals_data: List of dictionaries with signal data
                Each dict should have: url, content, and optionally title, source_id, provenance
        
        Returns:
            List of created Signal objects
        """
        signals = []
        
        for data in signals_data:
            signal = Signal(
                url=data['url'],
                content=data['content'],
                title=data.get('title'),
                source_id=data.get('source_id'),
                provenance=data.get('provenance'),
                processed=False
            )
            signals.append(signal)
        
        self.db.add_all(signals)
        self.db.commit()
        
        # Refresh all signals to get their IDs
        for signal in signals:
            self.db.refresh(signal)
        
        return signals
    
    def get_signals_by_source(
        self,
        source_id: uuid.UUID,
        limit: int = 100
    ) -> List[Signal]:
        """
        Get all signals from a specific source.
        
        Args:
            source_id: UUID of the source
            limit: Maximum number of results
        
        Returns:
            List of Signal objects
        """
        return (
            self.db.query(Signal)
            .filter(Signal.source_id == source_id)
            .order_by(Signal.ingested_at.desc())
            .limit(limit)
            .all()
        )
    
    def signal_exists(self, url: str) -> bool:
        """
        Check if a signal with the given URL already exists.
        
        Args:
            url: URL to check
        
        Returns:
            True if signal exists, False otherwise
        """
        return self.db.query(Signal).filter(Signal.url == url).count() > 0
    
    def get_recent_signals(
        self,
        hours: int = 24,
        processed: Optional[bool] = None
    ) -> List[Signal]:
        """
        Get signals ingested within the last N hours.
        
        Args:
            hours: Number of hours to look back
            processed: Filter by processed status (None = all)
        
        Returns:
            List of Signal objects
        """
        from datetime import timedelta
        
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        query = self.db.query(Signal).filter(Signal.ingested_at >= cutoff_time)
        
        if processed is not None:
            query = query.filter(Signal.processed == processed)
        
        return query.order_by(Signal.ingested_at.desc()).all()

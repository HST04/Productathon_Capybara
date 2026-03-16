"""Background worker for processing signals into leads."""

import time
import sys
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError, OperationalError
from requests.exceptions import RequestException, Timeout, ConnectionError
from google.api_core import exceptions as google_exceptions

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from app.utils.config import settings
from app.db.session import SessionLocal
from app.models.signal import Signal
from app.models.event import Event
from app.models.lead import Lead
from app.models.lead_product import LeadProduct
from app.services.signal_service import SignalService
from app.services.entity_extractor import EntityExtractor
from app.services.company_resolver import CompanyResolver
from app.services.event_classifier import EventClassifier
from app.services.product_inference import ProductInferenceEngine
from app.services.lead_scorer import LeadScorer
from app.services.event_service import EventService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class RetryableError(Exception):
    """Exception for errors that should be retried."""
    pass


class PermanentError(Exception):
    """Exception for errors that should not be retried."""
    pass


class BackgroundWorker:
    """
    Background worker that continuously processes signals through the AI pipeline.
    
    Pipeline stages:
    1. Poll PostgreSQL for unprocessed signals
    2. Extract entities (companies, locations, products, cues)
    3. Resolve company identity (semantic matching)
    4. Classify event and check lead-worthiness
    5. If lead-worthy: infer products, score lead, route to territory
    6. Generate Lead with product recommendations
    7. Mark signal as processed
    
    Error handling:
    - Individual signal failures don't stop the pipeline
    - Transient failures are retried with exponential backoff (max 3 attempts)
    - Permanent failures are logged for manual review
    - Database connection errors trigger reconnection
    """
    
    # Retry configuration
    MAX_RETRIES = 3
    INITIAL_BACKOFF = 1  # seconds
    MAX_BACKOFF = 60  # seconds
    BACKOFF_MULTIPLIER = 2
    
    def __init__(self):
        """Initialize the background worker with all required services."""
        self.entity_extractor = EntityExtractor()
        self.event_classifier = EventClassifier()
        self.product_inference_engine = ProductInferenceEngine()
        self.lead_scorer = LeadScorer()
        
        # Track failed signals for manual review
        self.failed_signals: Dict[str, Dict[str, Any]] = {}
        
        logger.info("Background worker initialized")
        logger.info(f"Poll interval: {settings.worker_poll_interval_seconds} seconds")
        logger.info(f"Processing timeout: {settings.signal_processing_timeout_minutes} minutes")
        logger.info(f"Max retries: {self.MAX_RETRIES} with exponential backoff")
    
    def _calculate_backoff(self, attempt: int) -> float:
        """
        Calculate exponential backoff delay.
        
        Args:
            attempt: Retry attempt number (0-indexed)
        
        Returns:
            Backoff delay in seconds
        """
        backoff = min(
            self.INITIAL_BACKOFF * (self.BACKOFF_MULTIPLIER ** attempt),
            self.MAX_BACKOFF
        )
        return backoff
    
    def _is_transient_error(self, error: Exception) -> bool:
        """
        Determine if an error is transient and should be retried.
        
        Args:
            error: Exception to check
        
        Returns:
            True if error is transient, False otherwise
        """
        # Network errors - retry
        if isinstance(error, (Timeout, ConnectionError, RequestException)):
            return True
        
        # Database connection errors - retry
        if isinstance(error, OperationalError):
            return True
        
        # Gemini API errors - some are transient
        if isinstance(error, (google_exceptions.DeadlineExceeded, google_exceptions.ResourceExhausted, google_exceptions.ServiceUnavailable)):
            return True
        
        # Generic API errors - check if it's a 5xx error
        if isinstance(error, APIError):
            if hasattr(error, 'status_code') and error.status_code >= 500:
                return True
        
        # All other errors are permanent
        return False
    
    def _log_failure_for_review(self, signal: Signal, error: Exception, attempts: int):
        """
        Log a failed signal for manual review.
        
        Args:
            signal: Failed signal
            error: Exception that caused failure
            attempts: Number of attempts made
        """
        failure_info = {
            'signal_id': str(signal.id),
            'url': signal.url,
            'error': str(error),
            'error_type': type(error).__name__,
            'attempts': attempts,
            'timestamp': datetime.utcnow().isoformat(),
            'title': signal.title
        }
        
        self.failed_signals[str(signal.id)] = failure_info
        
        logger.error(
            f"Signal {signal.id} failed permanently after {attempts} attempts. "
            f"Error: {error}. Queued for manual review."
        )
    
    def process_signals(self):
        """
        Process unprocessed signals through the AI pipeline.
        
        Polls database for unprocessed signals and processes them one by one.
        Handles database connection errors gracefully.
        """
        db = None
        
        try:
            db = SessionLocal()
            
            # Get unprocessed signals
            signal_service = SignalService(db)
            unprocessed_signals = signal_service.get_unprocessed_signals(limit=100)
            
            if not unprocessed_signals:
                logger.debug("No unprocessed signals found")
                return
            
            logger.info(f"Found {len(unprocessed_signals)} unprocessed signals")
            
            # Process each signal
            processed_count = 0
            failed_count = 0
            
            for signal in unprocessed_signals:
                try:
                    success = self.process_signal_with_retry(db, signal)
                    if success:
                        processed_count += 1
                    else:
                        failed_count += 1
                except Exception as e:
                    logger.error(
                        f"Unexpected error processing signal {signal.id}: {e}",
                        exc_info=True
                    )
                    failed_count += 1
                    # Continue processing other signals
                    continue
            
            logger.info(
                f"Batch complete: {processed_count} processed, {failed_count} failed"
            )
        
        except OperationalError as e:
            logger.error(f"Database connection error: {e}. Will retry on next poll.")
            # Don't crash - let the main loop retry
        
        except Exception as e:
            logger.error(f"Error in process_signals: {e}", exc_info=True)
        
        finally:
            if db:
                db.close()
    
    def process_signal_with_retry(self, db: Session, signal: Signal) -> bool:
        """
        Process a signal with retry logic for transient failures.
        
        Args:
            db: Database session
            signal: Signal to process
        
        Returns:
            True if processing succeeded, False otherwise
        """
        for attempt in range(self.MAX_RETRIES):
            try:
                success = self.process_signal(db, signal)
                
                if success:
                    return True
                else:
                    # Processing returned False - permanent failure
                    self._log_failure_for_review(signal, Exception("Processing returned False"), attempt + 1)
                    return False
            
            except Exception as e:
                is_transient = self._is_transient_error(e)
                is_last_attempt = (attempt == self.MAX_RETRIES - 1)
                
                if is_transient and not is_last_attempt:
                    # Retry with exponential backoff
                    backoff = self._calculate_backoff(attempt)
                    logger.warning(
                        f"[{signal.id}] Transient error on attempt {attempt + 1}/{self.MAX_RETRIES}: {e}. "
                        f"Retrying in {backoff:.1f}s..."
                    )
                    time.sleep(backoff)
                    
                    # Rollback and get fresh session for retry
                    db.rollback()
                    continue
                else:
                    # Permanent error or last attempt - log for review
                    error_type = "Permanent" if not is_transient else "Transient (max retries)"
                    logger.error(
                        f"[{signal.id}] {error_type} error after {attempt + 1} attempts: {e}",
                        exc_info=True
                    )
                    self._log_failure_for_review(signal, e, attempt + 1)
                    db.rollback()
                    return False
        
        return False
    
    def process_signal(self, db: Session, signal: Signal) -> bool:
        """
        Process a single signal through the complete pipeline.
        
        Args:
            db: Database session
            signal: Signal to process
        
        Returns:
            True if processing succeeded, False otherwise
        """
        start_time = datetime.utcnow()
        logger.info(f"Processing signal {signal.id} from {signal.url}")
        
        try:
            # Stage 1: Extract entities
            logger.debug(f"[{signal.id}] Stage 1: Extracting entities")
            entities = self.entity_extractor.extract_entities(
                text=signal.content,
                title=signal.title
            )
            
            if not entities.companies:
                logger.warning(
                    f"[{signal.id}] No companies extracted, marking as processed"
                )
                self._mark_processed(db, signal)
                return True
            
            # Stage 2: Resolve company identity
            logger.debug(f"[{signal.id}] Stage 2: Resolving company identity")
            company_resolver = CompanyResolver(db)
            
            # Use first company mention
            company_mention = entities.companies[0]
            company = company_resolver.resolve_company(
                company_name=company_mention.name,
                name_variants=company_mention.name_variants if hasattr(company_mention, 'name_variants') else None,
                cin=company_mention.cin,
                gst=company_mention.gst,
                website=company_mention.website,
                industry=company_mention.industry,
                address=company_mention.address,
                locations=company_mention.locations
            )
            
            logger.info(f"[{signal.id}] Resolved to company: {company.name}")
            
            # Stage 3: Classify event
            logger.debug(f"[{signal.id}] Stage 3: Classifying event")
            classification = self.event_classifier.classify_event(
                signal=signal,
                company_name=company.name
            )
            
            logger.info(
                f"[{signal.id}] Event classified: lead_worthy={classification.is_lead_worthy}, "
                f"intent={classification.intent_strength:.2f}"
            )
            
            # Create Event record
            event_service = EventService(db)
            event = event_service.create_event(
                signal_id=signal.id,
                company_id=company.id,
                event_type=classification.event_type,
                event_summary=classification.event_summary,
                location=classification.location or (entities.location.full_location if entities.location else None),
                capacity=classification.capacity or (entities.capacity.value if entities.capacity else None),
                deadline=classification.deadline,
                intent_strength=classification.intent_strength,
                is_lead_worthy=classification.is_lead_worthy
            )
            
            # Stage 4: Check if lead-worthy
            if not classification.is_lead_worthy:
                logger.info(f"[{signal.id}] Event not lead-worthy, skipping lead generation")
                self._mark_processed(db, signal)
                return True
            
            # Stage 5: Infer products
            logger.debug(f"[{signal.id}] Stage 4: Inferring products")
            product_matches = self.product_inference_engine.infer_products(
                text=signal.content,
                product_keywords=entities.product_keywords,
                operational_cues=entities.operational_cues,
                top_n=3
            )
            
            if not product_matches:
                logger.warning(f"[{signal.id}] No products inferred")
            else:
                logger.info(
                    f"[{signal.id}] Inferred {len(product_matches)} products: "
                    f"{[m.product_name for m in product_matches]}"
                )
            
            # Stage 6: Score and route lead
            logger.debug(f"[{signal.id}] Stage 5: Scoring and routing lead")
            
            # Get source trust score
            source_trust_score = 50.0  # Default neutral
            if signal.source:
                source_trust_score = signal.source.trust_score
            
            # Calculate score
            product_confidences = [m.confidence for m in product_matches]
            score, components = self.lead_scorer.calculate_score(
                intent_strength=classification.intent_strength,
                signal_date=signal.ingested_at,
                company_size_proxy=classification.capacity,
                product_confidences=product_confidences,
                source_trust_score=source_trust_score,
                location=classification.location
            )
            
            # Assign priority
            priority = self.lead_scorer.assign_priority(score)
            
            # Route to territory
            assigned_to, territory = self.lead_scorer.route_to_territory(
                db=db,
                location=classification.location
            )
            
            logger.info(
                f"[{signal.id}] Lead scored: score={score}, priority={priority}, "
                f"assigned_to={assigned_to}, territory={territory}"
            )
            
            # Stage 7: Create Lead
            logger.debug(f"[{signal.id}] Stage 6: Creating lead")
            lead = Lead(
                event_id=event.id,
                company_id=company.id,
                score=score,
                priority=priority,
                assigned_to=assigned_to,
                territory=territory,
                status='new'
            )
            db.add(lead)
            db.flush()  # Get lead ID
            
            # Create product recommendations
            for rank, match in enumerate(product_matches, start=1):
                lead_product = LeadProduct(
                    lead_id=lead.id,
                    product_name=match.product_name,
                    confidence_score=match.confidence,
                    reasoning=match.reasoning,
                    reason_code=match.reason_code,
                    rank=rank,
                    uncertainty_flag=match.uncertainty_flag
                )
                db.add(lead_product)
            
            # Mark signal as processed
            self._mark_processed(db, signal)
            
            # Commit all changes
            db.commit()
            
            # Calculate processing time
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            logger.info(
                f"[{signal.id}] Successfully processed in {processing_time:.2f}s - "
                f"Created lead {lead.id} with {len(product_matches)} products"
            )
            
            # Send WhatsApp notification if high priority
            if lead.priority == "high" and lead.assigned_to:
                try:
                    from app.services.whatsapp_notifier import WhatsAppNotifier
                    from app.models.sales_officer import SalesOfficer
                    
                    # Get the assigned officer by name
                    officer = db.query(SalesOfficer).filter(
                        SalesOfficer.name == lead.assigned_to
                    ).first()
                    
                    if officer:
                        notifier = WhatsAppNotifier()
                        success = notifier.send_lead_alert(db, lead, officer)
                        if success:
                            logger.info(f"WhatsApp notification sent to {officer.name}")
                    else:
                        logger.warning(f"Could not find officer '{lead.assigned_to}' for WhatsApp notification")
                except Exception as e:
                    # Don't fail the entire pipeline if WhatsApp fails
                    logger.error(f"Failed to send WhatsApp notification: {e}")
            
            return True
        
        except Exception as e:
            logger.error(
                f"[{signal.id}] Pipeline error: {e}",
                exc_info=True
            )
            # Rollback transaction
            db.rollback()
            return False
    
    def _mark_processed(self, db: Session, signal: Signal):
        """Mark a signal as processed."""
        signal.processed = True
        signal.processed_at = datetime.utcnow()
        db.commit()
    
    def run(self):
        """
        Main worker loop.
        
        Continuously polls for unprocessed signals and processes them.
        Handles graceful shutdown on KeyboardInterrupt.
        """
        logger.info("Starting background worker...")
        
        while True:
            try:
                self.process_signals()
                
                # Log failed signals summary if any
                if self.failed_signals:
                    logger.warning(
                        f"Total failed signals awaiting manual review: {len(self.failed_signals)}"
                    )
                
                time.sleep(settings.worker_poll_interval_seconds)
            
            except KeyboardInterrupt:
                logger.info("Received shutdown signal, stopping worker...")
                break
            
            except Exception as e:
                logger.error(f"Unexpected error in worker loop: {e}", exc_info=True)
                # Wait before retrying
                time.sleep(settings.worker_poll_interval_seconds)
        
        # Log final summary
        if self.failed_signals:
            logger.warning(
                f"Worker stopped with {len(self.failed_signals)} failed signals. "
                f"Review required for: {list(self.failed_signals.keys())}"
            )
        
        logger.info("Background worker stopped")
    
    def get_failed_signals(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all failed signals awaiting manual review.
        
        Returns:
            Dictionary of signal_id -> failure_info
        """
        return self.failed_signals.copy()
    
    def clear_failed_signals(self):
        """Clear the failed signals queue."""
        count = len(self.failed_signals)
        self.failed_signals.clear()
        logger.info(f"Cleared {count} failed signals from review queue")


def run_worker():
    """Entry point for running the background worker."""
    worker = BackgroundWorker()
    worker.run()


if __name__ == "__main__":
    run_worker()

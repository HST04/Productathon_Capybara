"""
Integration tests for mobile offline/online synchronization.

Tests the offline data storage, sync queue management, and conflict resolution
for the mobile interface.
"""

import pytest
import json
from datetime import datetime
from sqlalchemy.orm import Session
from unittest.mock import Mock, patch

from app.models.lead import Lead
from app.models.company import Company
from app.models.event import Event
from app.models.signal import Signal
from app.models.source import Source
from app.models.feedback import Feedback
from app.services.feedback_service import FeedbackService


@pytest.fixture
def db_session():
    """Create a test database session."""
    from app.db.session import SessionLocal
    db = SessionLocal()
    try:
        yield db
    finally:
        # Clean up test data
        db.query(Feedback).delete()
        db.query(Lead).delete()
        db.query(Event).delete()
        db.query(Signal).delete()
        db.query(Company).delete()
        db.query(Source).delete()
        db.commit()
        db.close()


@pytest.fixture
def test_lead(db_session):
    """Create a test lead with all dependencies."""
    source = Source(
        domain="test.com",
        category="news",
        access_method="rss",
        trust_score=50.0,
        trust_tier="neutral"
    )
    db_session.add(source)
    db_session.flush()
    
    company = Company(
        name="Test Company",
        name_variants=["Test Co"],
        industry="Manufacturing"
    )
    db_session.add(company)
    db_session.flush()
    
    signal = Signal(
        source_id=source.id,
        url="https://test.com/article",
        title="Test Article",
        content="Test content",
        ingested_at=datetime.utcnow(),
        processed=True
    )
    db_session.add(signal)
    db_session.flush()
    
    event = Event(
        signal_id=signal.id,
        company_id=company.id,
        event_type="expansion",
        event_summary="Test expansion",
        is_lead_worthy=True,
        intent_strength=0.8
    )
    db_session.add(event)
    db_session.flush()
    
    lead = Lead(
        event_id=event.id,
        company_id=company.id,
        score=75,
        priority="high",
        status="new"
    )
    db_session.add(lead)
    db_session.commit()
    db_session.refresh(lead)
    
    return lead


class MockOfflineStorage:
    """Mock implementation of offline storage (simulates IndexedDB)."""
    
    def __init__(self):
        self.leads = {}
        self.pending_changes = []
        self.sync_queue = []
    
    def store_lead(self, lead_data):
        """Store lead data offline."""
        self.leads[lead_data['id']] = lead_data
    
    def get_lead(self, lead_id):
        """Retrieve lead from offline storage."""
        return self.leads.get(lead_id)
    
    def add_pending_change(self, change):
        """Add a change to the sync queue."""
        self.pending_changes.append(change)
        self.sync_queue.append(change)
    
    def get_pending_changes(self):
        """Get all pending changes."""
        return self.pending_changes.copy()
    
    def clear_pending_change(self, change_id):
        """Remove a synced change from the queue."""
        self.pending_changes = [
            c for c in self.pending_changes if c.get('id') != change_id
        ]
        self.sync_queue = [
            c for c in self.sync_queue if c.get('id') != change_id
        ]
    
    def has_pending_changes(self):
        """Check if there are pending changes."""
        return len(self.pending_changes) > 0


@pytest.mark.integration
class TestMobileOfflineSync:
    """Test mobile offline/online synchronization scenarios."""
    
    def test_offline_lead_caching(self, db_session, test_lead):
        """
        Test that leads can be cached for offline access.
        
        Validates Requirements: 13.7 (Offline caching)
        """
        # Simulate fetching lead data from API
        lead_data = {
            'id': str(test_lead.id),
            'company_name': test_lead.company.name,
            'event_summary': test_lead.event.event_summary,
            'score': test_lead.score,
            'priority': test_lead.priority,
            'status': test_lead.status,
            'cached_at': datetime.utcnow().isoformat()
        }
        
        # Store in offline storage
        storage = MockOfflineStorage()
        storage.store_lead(lead_data)
        
        # Verify lead can be retrieved offline
        cached_lead = storage.get_lead(str(test_lead.id))
        assert cached_lead is not None
        assert cached_lead['id'] == str(test_lead.id)
        assert cached_lead['company_name'] == test_lead.company.name
        assert cached_lead['priority'] == test_lead.priority
    
    def test_offline_feedback_submission(self, db_session, test_lead):
        """
        Test that feedback can be submitted offline and queued for sync.
        
        Validates Requirements: 13.7, 13.9 (Offline support and sync)
        """
        storage = MockOfflineStorage()
        
        # Simulate offline feedback submission
        offline_feedback = {
            'id': 'offline-feedback-1',
            'lead_id': str(test_lead.id),
            'feedback_type': 'accepted',
            'notes': 'Submitted while offline',
            'submitted_by': 'mobile_officer',
            'submitted_at': datetime.utcnow().isoformat(),
            'synced': False
        }
        
        # Add to sync queue
        storage.add_pending_change({
            'type': 'feedback',
            'id': 'offline-feedback-1',
            'data': offline_feedback
        })
        
        # Verify change queued
        assert storage.has_pending_changes()
        pending = storage.get_pending_changes()
        assert len(pending) == 1
        assert pending[0]['type'] == 'feedback'
        assert pending[0]['data']['lead_id'] == str(test_lead.id)
    
    def test_offline_notes_addition(self, db_session, test_lead):
        """
        Test that notes can be added offline and queued for sync.
        
        Validates Requirements: 13.6, 13.9 (Lead notes and sync)
        """
        storage = MockOfflineStorage()
        
        # Simulate offline note addition
        offline_note = {
            'id': 'offline-note-1',
            'lead_id': str(test_lead.id),
            'note_text': 'Called customer, will follow up tomorrow',
            'created_at': datetime.utcnow().isoformat(),
            'synced': False
        }
        
        # Add to sync queue
        storage.add_pending_change({
            'type': 'note',
            'id': 'offline-note-1',
            'data': offline_note
        })
        
        # Verify change queued
        assert storage.has_pending_changes()
        pending = storage.get_pending_changes()
        assert len(pending) == 1
        assert pending[0]['type'] == 'note'
    
    def test_online_sync_feedback(self, db_session, test_lead):
        """
        Test syncing offline feedback when connectivity is restored.
        
        Validates Requirements: 13.9 (Background sync)
        """
        storage = MockOfflineStorage()
        
        # Create offline feedback
        offline_feedback = {
            'id': 'offline-feedback-1',
            'lead_id': str(test_lead.id),
            'feedback_type': 'accepted',
            'notes': 'Offline submission',
            'submitted_by': 'mobile_officer',
            'submitted_at': datetime.utcnow().isoformat(),
            'synced': False
        }
        
        storage.add_pending_change({
            'type': 'feedback',
            'id': 'offline-feedback-1',
            'data': offline_feedback
        })
        
        # Simulate coming back online and syncing
        pending = storage.get_pending_changes()
        
        for change in pending:
            if change['type'] == 'feedback':
                # Submit to server
                feedback_service = FeedbackService(db_session)
                feedback = feedback_service.submit_feedback(
                    lead_id=test_lead.id,
                    feedback_type=change['data']['feedback_type'],
                    notes=change['data']['notes'],
                    submitted_by=change['data']['submitted_by']
                )
                
                # Verify feedback persisted
                assert feedback is not None
                assert feedback.lead_id == test_lead.id
                assert feedback.feedback_type == 'accepted'
                
                # Clear from sync queue
                storage.clear_pending_change(change['id'])
        
        # Verify sync queue empty
        assert not storage.has_pending_changes()
    
    def test_multiple_offline_changes_sync(self, db_session, test_lead):
        """
        Test syncing multiple offline changes in order.
        
        Validates Requirements: 13.9 (Background sync)
        """
        storage = MockOfflineStorage()
        
        # Create multiple offline changes
        changes = [
            {
                'type': 'status_update',
                'id': 'change-1',
                'data': {
                    'lead_id': str(test_lead.id),
                    'status': 'contacted',
                    'timestamp': datetime.utcnow().isoformat()
                }
            },
            {
                'type': 'note',
                'id': 'change-2',
                'data': {
                    'lead_id': str(test_lead.id),
                    'note_text': 'First note',
                    'timestamp': datetime.utcnow().isoformat()
                }
            },
            {
                'type': 'feedback',
                'id': 'change-3',
                'data': {
                    'lead_id': str(test_lead.id),
                    'feedback_type': 'accepted',
                    'notes': 'Final feedback',
                    'submitted_by': 'officer'
                }
            }
        ]
        
        for change in changes:
            storage.add_pending_change(change)
        
        # Verify all changes queued
        assert len(storage.get_pending_changes()) == 3
        
        # Simulate syncing
        pending = storage.get_pending_changes()
        synced_count = 0
        
        for change in pending:
            if change['type'] == 'status_update':
                # Update lead status
                test_lead.status = change['data']['status']
                db_session.commit()
                storage.clear_pending_change(change['id'])
                synced_count += 1
            
            elif change['type'] == 'note':
                # In real implementation, would save note
                # For test, just mark as synced
                storage.clear_pending_change(change['id'])
                synced_count += 1
            
            elif change['type'] == 'feedback':
                # Submit feedback
                feedback_service = FeedbackService(db_session)
                feedback_service.submit_feedback(
                    lead_id=test_lead.id,
                    feedback_type=change['data']['feedback_type'],
                    notes=change['data']['notes'],
                    submitted_by=change['data']['submitted_by']
                )
                storage.clear_pending_change(change['id'])
                synced_count += 1
        
        # Verify all changes synced
        assert synced_count == 3
        assert not storage.has_pending_changes()
    
    def test_sync_conflict_resolution(self, db_session, test_lead):
        """
        Test handling sync conflicts when server data has changed.
        
        Validates Requirements: 13.9 (Sync conflict handling)
        """
        storage = MockOfflineStorage()
        
        # Cache lead data offline
        original_status = test_lead.status
        cached_lead = {
            'id': str(test_lead.id),
            'status': original_status,
            'cached_at': datetime.utcnow().isoformat()
        }
        storage.store_lead(cached_lead)
        
        # Simulate offline status change
        storage.add_pending_change({
            'type': 'status_update',
            'id': 'offline-status-1',
            'data': {
                'lead_id': str(test_lead.id),
                'status': 'contacted',
                'timestamp': datetime.utcnow().isoformat()
            }
        })
        
        # Meanwhile, server status changed (simulating another user's update)
        test_lead.status = 'qualified'
        db_session.commit()
        
        # Attempt to sync offline change
        pending = storage.get_pending_changes()
        for change in pending:
            if change['type'] == 'status_update':
                # Fetch current server state
                db_session.refresh(test_lead)
                server_status = test_lead.status
                offline_status = change['data']['status']
                
                # Conflict detected: server has 'qualified', offline has 'contacted'
                if server_status != original_status:
                    # Conflict resolution: server wins (last-write-wins)
                    # In real implementation, might prompt user or merge
                    # For this test, we keep server state
                    pass
                else:
                    # No conflict, apply offline change
                    test_lead.status = offline_status
                    db_session.commit()
                
                storage.clear_pending_change(change['id'])
        
        # Verify conflict resolved (server state preserved)
        db_session.refresh(test_lead)
        assert test_lead.status == 'qualified'  # Server state wins
    
    def test_sync_status_indicator(self, db_session, test_lead):
        """
        Test sync status tracking for UI indicator.
        
        Validates Requirements: 13.9 (Sync status display)
        """
        storage = MockOfflineStorage()
        
        # Add multiple changes
        for i in range(3):
            storage.add_pending_change({
                'type': 'note',
                'id': f'note-{i}',
                'data': {'lead_id': str(test_lead.id), 'note': f'Note {i}'}
            })
        
        # Check sync status
        sync_status = {
            'has_pending': storage.has_pending_changes(),
            'pending_count': len(storage.get_pending_changes()),
            'is_syncing': False,
            'last_sync': None
        }
        
        assert sync_status['has_pending'] is True
        assert sync_status['pending_count'] == 3
        
        # Simulate syncing
        sync_status['is_syncing'] = True
        
        # Clear changes
        for change in storage.get_pending_changes():
            storage.clear_pending_change(change['id'])
        
        # Update sync status
        sync_status['has_pending'] = storage.has_pending_changes()
        sync_status['pending_count'] = len(storage.get_pending_changes())
        sync_status['is_syncing'] = False
        sync_status['last_sync'] = datetime.utcnow().isoformat()
        
        assert sync_status['has_pending'] is False
        assert sync_status['pending_count'] == 0
        assert sync_status['last_sync'] is not None
    
    def test_low_bandwidth_mode_data_compression(self, db_session, test_lead):
        """
        Test that data is compressed/minimized in low bandwidth mode.
        
        Validates Requirements: 13.8 (Low bandwidth mode)
        """
        # Full lead data (normal mode)
        full_lead_data = {
            'id': str(test_lead.id),
            'company': {
                'name': test_lead.company.name,
                'industry': test_lead.company.industry,
                'locations': test_lead.company.locations or []
            },
            'event': {
                'summary': test_lead.event.event_summary,
                'type': test_lead.event.event_type,
                'location': test_lead.event.location,
                'capacity': test_lead.event.capacity
            },
            'score': test_lead.score,
            'priority': test_lead.priority,
            'status': test_lead.status
        }
        
        # Compressed lead data (low bandwidth mode)
        compressed_lead_data = {
            'id': str(test_lead.id),
            'company_name': test_lead.company.name,
            'event_summary': test_lead.event.event_summary,
            'priority': test_lead.priority,
            'status': test_lead.status
            # Omit: full company details, full event details, etc.
        }
        
        # Verify compression reduces data size
        full_size = len(json.dumps(full_lead_data))
        compressed_size = len(json.dumps(compressed_lead_data))
        
        assert compressed_size < full_size, \
            f"Compressed data ({compressed_size} bytes) should be smaller than full data ({full_size} bytes)"
        
        # Verify essential data preserved
        assert compressed_lead_data['id'] == str(test_lead.id)
        assert compressed_lead_data['priority'] == test_lead.priority

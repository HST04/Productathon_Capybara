"""Database reset script (development only)."""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from app.db.session import engine, Base
from app.models.source import Source
from app.models.signal import Signal
from app.models.company import Company
from app.models.event import Event
from app.models.lead import Lead
from app.models.lead_product import LeadProduct
from app.models.feedback import Feedback
from app.models.sales_officer import SalesOfficer
from app.models.whatsapp_notification import WhatsAppNotification


def reset_db():
    """Drop all tables and recreate them (DEVELOPMENT ONLY)."""
    print("WARNING: This will delete all data in the database!")
    response = input("Are you sure you want to continue? (yes/no): ")
    
    if response.lower() != "yes":
        print("Aborted.")
        return
    
    print("Dropping all tables...")
    Base.metadata.drop_all(bind=engine)
    
    print("Creating all tables...")
    Base.metadata.create_all(bind=engine)
    
    print("Database reset complete!")


if __name__ == "__main__":
    reset_db()

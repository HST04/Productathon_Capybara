"""Database initialization script.""""""[Use after deployment to cloud]"""

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


def init_db():
    """Initialize database by creating all tables."""
    print("Creating database tables...")
    
    # Import all models to ensure they're registered with Base
    # This is already done above
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    print("Database tables created successfully!")
    print("\nCreated tables:")
    for table in Base.metadata.sorted_tables:
        print(f"  - {table.name}")


if __name__ == "__main__":
    init_db()

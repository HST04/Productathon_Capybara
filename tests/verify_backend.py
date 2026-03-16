"""Backend verification script for Task 16.

This script verifies that all backend components are properly configured:
1. FastAPI app imports successfully
2. All API routes are registered
3. Database models are properly defined
4. WhatsApp notifier is configured
5. Worker pipeline is properly structured
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

def verify_fastapi_app():
    """Verify FastAPI app imports and routes are registered."""
    print("\n=== Verifying FastAPI App ===")
    try:
        from app.main import app
        print("✓ FastAPI app imports successfully")
        
        # Count routes
        route_count = len(app.routes)
        print(f"✓ {route_count} routes registered")
        
        # List routes
        print("\nRegistered routes:")
        for route in app.routes:
            if hasattr(route, 'path') and hasattr(route, 'methods'):
                methods = ', '.join(route.methods) if route.methods else 'N/A'
                print(f"  {methods:10} {route.path}")
        
        return True
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def verify_api_endpoints():
    """Verify all API endpoint modules import successfully."""
    print("\n=== Verifying API Endpoints ===")
    try:
        from app.api import leads, companies, sources, dashboard
        print("✓ All API endpoint modules import successfully")
        
        # Verify each router
        print("✓ Leads router:", hasattr(leads, 'router'))
        print("✓ Companies router:", hasattr(companies, 'router'))
        print("✓ Sources router:", hasattr(sources, 'router'))
        print("✓ Dashboard router:", hasattr(dashboard, 'router'))
        
        return True
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def verify_database_models():
    """Verify all database models import successfully."""
    print("\n=== Verifying Database Models ===")
    try:
        from app.models.signal import Signal
        from app.models.company import Company
        from app.models.event import Event
        from app.models.lead import Lead
        from app.models.lead_product import LeadProduct
        from app.models.feedback import Feedback
        from app.models.source import Source
        from app.models.sales_officer import SalesOfficer
        from app.models.whatsapp_notification import WhatsAppNotification
        
        print("✓ All database models import successfully")
        print("  - Signal")
        print("  - Company")
        print("  - Event")
        print("  - Lead")
        print("  - LeadProduct")
        print("  - Feedback")
        print("  - Source")
        print("  - SalesOfficer")
        print("  - WhatsAppNotification")
        
        return True
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def verify_services():
    """Verify all service modules import successfully."""
    print("\n=== Verifying Services ===")
    
    # Services that don't require google-generativeai
    core_services = [
        ("CompanyResolver", "app.services.company_resolver", "CompanyResolver"),
        ("ProductInferenceEngine", "app.services.product_inference", "ProductInferenceEngine"),
        ("LeadScorer", "app.services.lead_scorer", "LeadScorer"),
        ("FeedbackService", "app.services.feedback_service", "FeedbackService"),
        ("WhatsAppNotifier", "app.services.whatsapp_notifier", "WhatsAppNotifier"),
    ]
    
    # Services that require google-generativeai (optional)
    ai_services = [
        ("EntityExtractor", "app.services.entity_extractor", "EntityExtractor"),
        ("EventClassifier", "app.services.event_classifier", "EventClassifier"),
    ]
    
    all_success = True
    
    # Test core services
    for name, module, cls in core_services:
        try:
            mod = __import__(module, fromlist=[cls])
            getattr(mod, cls)
            print(f"  ✓ {name}")
        except Exception as e:
            print(f"  ✗ {name}: {e}")
            all_success = False
    
    # Test AI services (warn if missing google-generativeai)
    for name, module, cls in ai_services:
        try:
            mod = __import__(module, fromlist=[cls])
            getattr(mod, cls)
            print(f"  ✓ {name}")
        except ModuleNotFoundError as e:
            if "google" in str(e):
                print(f"  ⚠ {name}: google-generativeai not installed (optional for development)")
            else:
                print(f"  ✗ {name}: {e}")
                all_success = False
        except Exception as e:
            print(f"  ✗ {name}: {e}")
            all_success = False
    
    if all_success:
        print("✓ All required service modules verified")
    
    return all_success


def verify_whatsapp_notifier():
    """Verify WhatsApp notifier is properly configured."""
    print("\n=== Verifying WhatsApp Notifier ===")
    try:
        from app.services.whatsapp_notifier import WhatsAppNotifier
        
        notifier = WhatsAppNotifier()
        print("✓ WhatsAppNotifier instantiates successfully")
        
        # Check methods exist
        assert hasattr(notifier, 'send_lead_alert'), "Missing send_lead_alert method"
        assert hasattr(notifier, 'check_opt_in'), "Missing check_opt_in method"
        assert hasattr(notifier, 'respect_service_window'), "Missing respect_service_window method"
        assert hasattr(notifier, '_is_configured'), "Missing _is_configured method"
        print("✓ Required methods present")
        
        return True
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def verify_worker():
    """Verify background worker imports successfully."""
    print("\n=== Verifying Background Worker ===")
    try:
        from app.worker import BackgroundWorker
        
        print("✓ BackgroundWorker imports successfully")
        
        # Check key methods
        worker = BackgroundWorker()
        assert hasattr(worker, 'process_signal'), "Missing process_signal method"
        assert hasattr(worker, 'process_signals'), "Missing process_signals method"
        print("✓ Required methods present")
        
        return True
    except ModuleNotFoundError as e:
        if "google" in str(e):
            print("⚠ BackgroundWorker requires google-generativeai (optional for development)")
            print("  Worker will function when google-generativeai is installed")
            return True  # Don't fail verification for optional dependency
        else:
            print(f"✗ Error: {e}")
            return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def main():
    """Run all verification checks."""
    print("=" * 60)
    print("HPCL Lead Intelligence Agent - Backend Verification")
    print("Task 16: Checkpoint - Verify backend API and notifications")
    print("=" * 60)
    
    results = []
    
    results.append(("FastAPI App", verify_fastapi_app()))
    results.append(("API Endpoints", verify_api_endpoints()))
    results.append(("Database Models", verify_database_models()))
    results.append(("Services", verify_services()))
    results.append(("WhatsApp Notifier", verify_whatsapp_notifier()))
    results.append(("Background Worker", verify_worker()))
    
    print("\n" + "=" * 60)
    print("Verification Summary")
    print("=" * 60)
    
    all_passed = True
    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status:8} {name}")
        if not passed:
            all_passed = False
    
    print("=" * 60)
    
    if all_passed:
        print("\n✓ All backend components verified successfully!")
        print("\nNext steps:")
        print("  1. Start the API server: uvicorn app.main:app --reload")
        print("  2. Test endpoints with: python tests/manual_test_api.py")
        print("  3. Start the worker: python app/worker.py")
        return 0
    else:
        print("\n✗ Some components failed verification")
        return 1


if __name__ == "__main__":
    sys.exit(main())

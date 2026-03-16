"""Pytest configuration and fixtures."""

import sys
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Mock google modules before any imports
sys.modules['google'] = MagicMock()
sys.modules['google.generativeai'] = MagicMock()
sys.modules['google.api_core'] = MagicMock()
sys.modules['google.api_core.exceptions'] = MagicMock()

# Set up test environment variables before any imports
os.environ.setdefault('PINECONE_API_KEY', 'test-key')
os.environ.setdefault('PINECONE_ENVIRONMENT', 'test-env')
os.environ.setdefault('DATABASE_URL', 'postgresql://test:test@localhost:5432/test_db')
os.environ.setdefault('GEMINI_API_KEY', 'test-gemini-key')
os.environ.setdefault('WHATSAPP_API_URL', 'https://test-whatsapp-api.com')
os.environ.setdefault('WHATSAPP_ACCESS_TOKEN', 'test-token')
os.environ.setdefault('WHATSAPP_PHONE_NUMBER_ID', 'test-phone-id')
os.environ.setdefault('FRONTEND_URL', 'http://localhost:3000')

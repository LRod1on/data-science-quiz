"""Ensure the backend directory is on sys.path for all tests."""

import os
import sys
from pathlib import Path

# Add backend/ to path so imports like `from session_manager import ...` work
# regardless of where pytest is invoked from.
sys.path.insert(0, str(Path(__file__).parent.parent))

# Set required env vars before any module-level imports happen
os.environ.setdefault("GIGACHAT_AUTH_KEY", "test-key")
os.environ.setdefault("GIGACHAT_MODEL", "GigaChat")

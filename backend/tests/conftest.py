import sys
from pathlib import Path

# Add app/ to Python path so tests can import from services.*, models.*, etc.
sys.path.insert(0, str(Path(__file__).parent.parent / "app"))

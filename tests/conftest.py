import sys
from pathlib import Path

# Allow import of convert.py from repo root (no package install required for tests)
sys.path.insert(0, str(Path(__file__).parent.parent))

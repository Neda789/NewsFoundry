import os
import sys

os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key")
os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")
os.environ.setdefault("MISTRAL_API_KEY", "dummy-key-for-tests")
os.environ.setdefault("GEMINI_API_KEY", "dummy-key-for-tests")
os.environ.setdefault("CHAT_MODEL", "google:gemini-3.6-flash")

SRC = os.path.join(os.path.dirname(__file__), "..", "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)
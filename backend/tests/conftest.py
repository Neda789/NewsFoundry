import os
import sys

os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key")
os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")
os.environ.setdefault("MISTRAL_API_KEY", "dummy-key-for-tests")
os.environ.setdefault("GROQ_API_KEY", "dummy-key-for-tests")
os.environ.setdefault("CHAT_MODEL", "groq:openai/gpt-oss-120b")

SRC = os.path.join(os.path.dirname(__file__), "..", "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)
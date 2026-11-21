"""Check the Mistral API key from .env actually works (models.list + one chat call)."""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

from mistralai import Mistral

key = os.environ.get("MISTRAL_API_KEY", "")
if not key:
    print("FAIL: MISTRAL_API_KEY not set in .env")
    sys.exit(1)

c = Mistral(api_key=key)
models = [m.id for m in c.models.list().data]
print("PASS models.list —", len(models), "models; sample:", models[:5])

r = c.chat.complete(model=os.getenv("ROUTER_MODEL", "mistral-small-latest"),
                    messages=[{"role": "user", "content": "Reply with exactly: OK"}])
print("PASS chat.complete —", r.choices[0].message.content.strip())

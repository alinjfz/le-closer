"""Configuration — model names, thresholds, flags. See plan section 22 open items."""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY", "")

# Models
ROUTER_MODEL = os.getenv("ROUTER_MODEL", "mistral-small-latest")
HEAVY_MODEL = os.getenv("HEAVY_MODEL", "mistral-large-latest")  # Le Chonk
VOXTRAL_MODEL = os.getenv("VOXTRAL_MODEL", "voxtral-mini-transcribe-realtime-3")

# Voxtral realtime settings (D4)
VOXTRAL_TARGET_DELAY_MS = int(os.getenv("VOXTRAL_TARGET_DELAY_MS", "480"))
VOXTRAL_SAMPLE_RATE = 16000
CONTEXT_BIAS = [
    "Mistral Studio", "Le Chonk", "Voxtral", "Müller Logistik",
    "Dr. Anna Weber", "SAP S/4HANA", "Salesforce", "HubSpot",
    "Workday", "Slack", "Microsoft Teams", "GDPR", "Betriebsrat",
]

# Card rules (section 8.3)
CARD_CONFIDENCE_THRESHOLD = 0.7
MAX_ACTIVE_CARDS = 3

# Rolling context window for the router (chars)
ROLLING_CONTEXT_CHARS = 4000

# Demo mode
DEMO_MODE = os.getenv("DEMO_MODE", "false").lower() == "true"

# Pricing guardrails defaults (overridden by data/pricing.yaml)
DEFAULT_LIST_PRICE_PER_SEAT = 30.0  # EUR / month
DEFAULT_COST_PER_SEAT = 8.0
ABSOLUTE_DISCOUNT_FLOOR_PCT = 10.0

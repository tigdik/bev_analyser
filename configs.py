import os
import pathlib

CATEGORIES = [
    "Consumer signals & UGC",
    "Competitive intel & new SKUs",
    "Flavours",
    "Ingredients & functional actives",
    "Miscellaneous"
]

# Sources we’ll monitor.
# For BevNET and FoodDive we’ll scrape listing pages as a fallback.
# Output folders
DATA_DIR = pathlib.Path("data")
RAW_DIR = DATA_DIR / "raw"
OUT_DIR = pathlib.Path("out")
STATE_FILE = DATA_DIR / "state.json"
SUMMARY_DIR = OUT_DIR / "summaries"

# OpenAI model configuration
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")  # fast/cheap, good quality
OPENAI_MAX_CHARS = 12000  # keep prompts sensible

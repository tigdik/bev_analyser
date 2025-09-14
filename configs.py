import os
import pathlib

CATEGORIES = [
    "Consumer signals & UGC",
    "Competitive intel & new SKUs",
    "Flavours",
    "Ingredients & functional actives",
    "miscellaneous"
]

# Sources we’ll monitor.
# For BevNET and FoodDive we’ll scrape listing pages as a fallback.
SOURCES = {
    "foodbusinessnews": {
        "rss_feeds": [
            "https://www.foodbusinessnews.net/rss/2",  # FBN Best News
            "https://www.foodbusinessnews.net/rss/topic/515-non-alcoholic-beverages",
        ],
        "html_pages": []  # not needed because RSS is rich here
    },
    "just-drinks": {
        "rss_feeds": [
            "https://www.just-drinks.com/news/feed/feed"
        ],
        "html_pages": []
    },
    "bevnet": {
        "rss_feeds": [],  # unclear public site-wide feed
        "html_pages": [
            "https://www.bevnet.com/news/"
        ],
    },
    "fooddive": {
        "rss_feeds": [],  # use scraping
        "html_pages": [
            "https://www.fooddive.com/topic/beverages/",
            "https://www.fooddive.com/press-release/",
        ],
    },
}

# Output folders
DATA_DIR = pathlib.Path("data")
RAW_DIR = DATA_DIR / "raw"
OUT_DIR = pathlib.Path("out")
STATE_FILE = DATA_DIR / "state.json"
SUMMARY_DIR = OUT_DIR / "summaries"

# OpenAI model configuration
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")  # fast/cheap, good quality
OPENAI_MAX_CHARS = 12000  # keep prompts sensible

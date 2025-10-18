import logging
from openai import OpenAI
from typing import Dict, Optional, Tuple, List
import os
from configs import OPENAI_MAX_CHARS, OPENAI_MODEL, CATEGORIES
from prompts import *
from openai.types.responses.response import Response
import dotenv

dotenv.load_dotenv()
client: OpenAI = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ---- Logging ----
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
log = logging.getLogger("bev-monitor")

def get_global_summary(text: str) -> Optional[str]:
    log.info("generating global summary...")
    clipped = text[:OPENAI_MAX_CHARS]
    rsp:Response = client.responses.create(
        model=OPENAI_MODEL,
        input=[
            {"role": "system", "content": global_system_prompt},
            {"role": "user", "content": get_global_summary_prompt(clipped)},
        ],
        temperature=0.2,
    )
    article = getattr(rsp, "output_text", None)
    return article


def call_openai_summary(text: str, url: str, title: str) -> Optional[str]:
    log.info(f"generating summary for article {title}...")
    clipped = text[:OPENAI_MAX_CHARS]
    rsp:Response = client.responses.create(
        model=OPENAI_MODEL,
        input=[
            {"role": "system", "content": global_system_prompt},
            {"role": "user", "content": get_user_prompt(url, title, CATEGORIES, clipped)},
        ],
        temperature=0.2,
    )

    # Extract text; the SDK provides .output_text in recent versions
    article = getattr(rsp, "output_text", None)
    if not article or article.find("IRRELEVANT_CONTENT")>=0:
        return None
    else:
        return article
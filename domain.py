from pydantic import BaseModel
from typing import List, Dict, Optional, Tuple


class SummaryItem(BaseModel):
    source: str
    title: str
    url: str
    published: str
    categories: List[str]
    summary: str
    key_points: str
    risks: str
    opportunities: str
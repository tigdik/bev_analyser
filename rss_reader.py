from main import now_string
from rss_sources import *
import feedparser
from domain import *
from typing import Dict, List
import datetime


logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
log = logging.getLogger("bev-monitor")


def read_summaries_from_rss_sources(timestamp_dir_name:str) -> List[SummaryItem]:
    for src in SOURCES:
        for feed in src.rss_feeds:
            log.info(f"RSS: {src.name} <- {feed}")
            rss_entries: List[RssResponseItem] = fetch_rss_entries(feed)
            summary_entities = list(map(lambda item: SummaryItem.from_rss(src.name, item.title, item.link, item.published), rss_entries))
            return summary_entities


def fetch_rss_entries(feed_url: str) -> List[RssResponseItem]:
    d = feedparser.parse(feed_url)
    items = []
    for e in d.entries:
        if not e:
            continue
        items.append(RssResponseItem(
            title=e.get("title", ""),
            link=e.get("link", ""),
            published=e.get("published", ""),
            summary=e.get("summary", ""),
            fetched_at=datetime.datetime.utcnow().strftime("%Y-%m-%d_%H%M%S_UTC")
        ))
    return items
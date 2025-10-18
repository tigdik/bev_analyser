
from pydantic import BaseModel
from pathlib import Path
import configs
from llm.open_ai import call_openai_summary, get_global_summary
from typing import List, Optional, Dict
import scraping_utils
import logging

from prompts import get_global_summary_prompt

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
log = logging.getLogger("bev-monitor")

class RssSource(BaseModel):
    name: str
    rss_feeds: list[str]
    html_pages: list[str]

class RssResponseItem(BaseModel):
    title: str
    link: str
    published: str
    summary: str
    fetched_at: str

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

    @staticmethod
    def from_openai_response(title: str, url: str, published: str, source_name:str, article:str) -> 'SummaryItem':
        cats_list = match_categories(article)
        # Extract sections
        summary = section("Summary", article)
        key_points = section("Key Points", article)
        risks = section("Risks", article)
        opportunities = section("Opportunities", article)
        item = SummaryItem(
            source=source_name,
            title=title,
            url=url,
            published=published,
            categories=cats_list,
            summary=summary,
            key_points=key_points,
            risks=risks,
            opportunities=opportunities
        )
        return item

    @staticmethod
    def from_rss(source_name: str, title: str, url: str, published: str):

        text = scraping_utils.extract_text_from_url(url)

        log.info(f"summarising url: {url}, title: {title}")
        article:Optional[str] = call_openai_summary(text, url, title)
        if not article or article.find("IRRELEVANT_CONTENT")>=0:
            return None
        else:
            item:SummaryItem = SummaryItem.from_openai_response(title, url, published, source_name, article)
            return item

class GlobalSummaryReportItem(BaseModel):
    summary: str
    categories: List[str]
    sources: List[RssSource]
    key_points: str

    @staticmethod
    def from_items(items: List[SummaryItem]) -> 'GlobalSummaryReportItem':
        from rss_sources import SOURCES

        resp = get_global_summary(items)
        global_summary = section("Summary", resp)
        key_points = section("Key Points", resp)

        return GlobalSummaryReportItem(
            summary=global_summary,
            categories=configs.CATEGORIES,
            sources=SOURCES,
            key_points=key_points
        )


class ReportItem(BaseModel):
    summary: GlobalSummaryReportItem
    summary_items: List[SummaryItem]

    def save_json(self, path: str | Path) -> None:
        """Save the ReportItem instance to a JSON file."""
        Path(path).write_text(self.model_dump_json(indent=4))

    @staticmethod
    def from_items(items: List[SummaryItem]) -> 'ReportItem':
       trimmed_summary_items = list(filter(lambda it:it is not None, items))
       ri = ReportItem(
            summary=GlobalSummaryReportItem.from_items(trimmed_summary_items),
            summary_items=trimmed_summary_items
        )
       return ri


def section(section_name, article):
    try:
        return  article.split(f"### {section_name}:\n")[1].split("\n\n")[0]
    except IndexError:
        raise Exception(f"Could not find section {section_name}")

def match_categories(article) -> list[str]:
    section_name = "Selected Categories"
    cats_paragraph = section(section_name, article)
    cats = list(map(lambda cat: cat[2:].strip(), cats_paragraph.split('\n')))
    return cats
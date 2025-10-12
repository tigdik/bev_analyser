
from pydantic import BaseModel
from llm.open_ai import call_openai_summary
from typing import List, Optional
import scraping_utils
import logging

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

def section(section_name, article):
    try:
        return  article.split(f"### {section_name}:\n")[1].split("\n\n")[0]
    except IndexError:
        raise Exception(f"Could not find section {section_name}")

def match_categories(article) -> list[str]:
    section_name = "Selected Categories"
    cats_paragraph = section(section_name, article)
    if len(cats_paragraph)>56:
        cats = list(map(lambda cat: cat[2:].strip(), cats_paragraph.split('\n')))
    else:
        cats = []
    return cats
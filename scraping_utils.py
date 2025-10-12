import requests
from typing import List, Dict, Optional, Tuple
from bs4 import BeautifulSoup
import logging, pathlib, trafilatura
from pdfminer.high_level import extract_text as pdf_extract_text
import feedparser
import re

from configs import RAW_DIR

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
log = logging.getLogger("bev-monitor")


def get_html(url: str, timeout=30) -> Optional[str]:
    try:
        headers = {"User-Agent": "bev-monitor/1.0 (+https://example.com)"}
        r = requests.get(url, headers=headers, timeout=timeout)
        if r.status_code == 200:
            return r.text
    except Exception as e:
        log.warning(f"HTML fetch failed: {url} ({e})")
    return None

def extract_article(record,url,source_name,timestamp_dir_name):
    text = extract_text_from_url(url)
    record["text_len"] = len(text)
    raw_dir = RAW_DIR / source_name / timestamp_dir_name
    # Also seek PDFs linked from the page
    html = get_html(url)
    pdf_texts = []
    if html:
        for pdf_url in detect_pdf_links(html, url)[:3]:
            p = download_pdf(pdf_url, raw_dir)
            if p:
                t = extract_text_from_pdf(p)
                if t:
                    pdf_texts.append({"pdf_url": pdf_url, "chars": len(t)})
                    text += "\n\n" + t

def extract_text_from_url(url: str) -> str:
    # trafilatura will fetch if you pass URL; but we prefer to fetch HTML once and extract from string.
    html = get_html(url)
    if not html:
        return ""
    # Try trafilatura main extraction with fallback
    try:
        extracted = trafilatura.extract(html, url=url, include_tables=False, include_comments=False)
        if extracted and len(extracted) > 200:
            return extracted
    except Exception:
        pass
    # Fallback: minimal text from BeautifulSoup
    soup = BeautifulSoup(html, "html5lib")
    text = soup.get_text(separator="\n")
    return text


def absolute_url(base: str, href: str) -> Optional[str]:
    try:
        return requests.compat.urljoin(base, href)
    except Exception:
        return None

def guess_article_links(listing_url: str, html: str) -> List[str]:
    # Generic heuristic: collect <a> hrefs that look like article pages (contain /news/ or date-like slugs)
    soup = BeautifulSoup(html, "html5lib")
    links = set()
    for a in soup.find_all("a", href=True):
        href = a["href"]
        full = absolute_url(listing_url, href)
        if not full:
            continue
        if any(x in full for x in ["/news/", "/article/", "/202", "/20"]):  # flexible
            links.add(full.split("#")[0])
    return list(links)

def detect_pdf_links(html: str, base_url: str) -> List[str]:
    soup = BeautifulSoup(html, "html5lib")
    urls = set()
    for a in soup.find_all("a", href=True):
        href = a["href"]
        full = absolute_url(base_url, href)
        if full and full.lower().endswith(".pdf"):
            urls.add(full)
    return list(urls)

def extract_text_from_pdf(path: pathlib.Path) -> str:
    try:
        return pdf_extract_text(str(path))
    except Exception as e:
        log.warning(f"PDF extract failed {path}: {e}")
        return ""

def download_pdf(url: str, dest_dir: pathlib.Path) -> Optional[pathlib.Path]:
    try:
        headers = {"User-Agent": "bev-monitor/1.0"}
        r = requests.get(url, headers=headers, timeout=45)
        if r.status_code == 200 and "application/pdf" in r.headers.get("content-type", "") or url.lower().endswith(".pdf"):
            name = sanitize_filename(pathlib.Path(url).name)
            p = dest_dir / name
            p.write_bytes(r.content)
            return p
    except Exception as e:
        log.warning(f"PDF download failed {url}: {e}")
    return None

def sanitize_filename(s: str) -> str:
    return re.sub(r"[^a-zA-Z0-9._-]+", "_", s)[:100]
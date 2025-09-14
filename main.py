# monitor.py
# Bev Analyser - Market Monitor (RSS + PDF) for beverages
# Run:  python monitor.py --once
# Or:   python monitor.py --interval-min 120
from configs import *
from prompts import *
import os, re, json, time, hashlib, argparse, datetime, pathlib, logging, itertools
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field

import feedparser
import requests
from bs4 import BeautifulSoup
import trafilatura
from pdfminer.high_level import extract_text as pdf_extract_text
from pydantic import BaseModel
from tqdm import tqdm
import dotenv
# Optional: scheduler mode
from apscheduler.schedulers.background import BackgroundScheduler
import os
from openai import OpenAI
from rss_sources import SOURCES, RssSource

dotenv.load_dotenv()

# ---- Config (edit as needed) ----

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


# ---- Logging ----
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
log = logging.getLogger("bev-monitor")


# ---- Utilities ----

def ensure_dirs():
    for p in [DATA_DIR, RAW_DIR, OUT_DIR, SUMMARY_DIR]:
        p.mkdir(parents=True, exist_ok=True)

def load_state() -> Dict[str, bool]:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}

def save_state(state: Dict[str, bool]):
    STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")

def hash_str(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:16]

def now_string() -> str:
    return datetime.datetime.utcnow().strftime("%Y-%m-%d_%H%M%S_UTC")

def sanitize_filename(s: str) -> str:
    return re.sub(r"[^a-zA-Z0-9._-]+", "_", s)[:100]


# ---- Fetchers ----

def fetch_rss_entries(feed_url: str) -> List[Dict]:
    d = feedparser.parse(feed_url)
    items = []
    for e in d.entries:
        items.append({
            "title": e.get("title", ""),
            "link": e.get("link", ""),
            "published": e.get("published", ""),
            "summary": e.get("summary", ""),
            "source_feed": feed_url
        })
    return items

def get_html(url: str, timeout=30) -> Optional[str]:
    try:
        headers = {"User-Agent": "bev-monitor/1.0 (+https://example.com)"}
        r = requests.get(url, headers=headers, timeout=timeout)
        if r.status_code == 200:
            return r.text
    except Exception as e:
        log.warning(f"HTML fetch failed: {url} ({e})")
    return None

def absolute_url(base: str, href: str) -> Optional[str]:
    try:
        return requests.compat.urljoin(base, href)
    except Exception:
        return None

def match_categories(article) ->list[str]:
        cat_paragraph_title = "### Selected Categories:\n"

        if article.startswith(cat_paragraph_title):
            cats_prefixed = article.split("\n\n")[0].split("\n")[1:]
            cats = list(map(lambda cat: cat[2:].strip(), cats_prefixed))
        else:
            cats = []
        return cats

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


# ---- Extraction ----

def extract_text_from_pdf(path: pathlib.Path) -> str:
    try:
        return pdf_extract_text(str(path))
    except Exception as e:
        log.warning(f"PDF extract failed {path}: {e}")
        return ""

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


# ---- Summarization ----

class SummaryItem(BaseModel):
    source: str
    title: str
    url: str
    published: str
    categories: List[str]
    summary: str
    key_points: List[str]
    risks: List[str]
    opportunities: List[str]


def call_openai_summary(source:RssSource, text: str, url: str, title: str) -> Tuple[List[str], str, List[str], List[str]]:
    from openai import OpenAI

    log.info("call_openai_summary(...) started")
    # Clip text length for token safety
    clipped = text[:OPENAI_MAX_CHARS]




    # Using the OpenAI Responses API (official SDK).
    # See OpenAI Platform docs for the Python SDK & Responses API.
    rsp = client.responses.create(
        model=OPENAI_MODEL,
        input=[
            {"role": "system", "content": global_system_prompt},
            {"role": "user", "content": get_user_prompt(url, title, CATEGORIES,clipped)},
        ],
        temperature=0.2,
    )

    # Extract text; the SDK provides .output_text in recent versions
    full = getattr(rsp, "output_text", None)
    if not full:
        # fallback for older SDKs
        try:
            full = rsp.choices[0].message.content[0].text
        except Exception:
            full = ""
    cats_list = match_categories(full)
    # Parse with simple regex heuristics
    # if not cats_list:
    #     cats_list = ["Competitive intel & new SKUs"]  # sensible default

    # Extract sections
    def section(name):
        m = re.search(rf"{name}[:\n]\s*(.*)", full, flags=re.I | re.S)
        return (m.group(1).strip() if m else "")

    summary = section("Executive Summary") or section("Summary") or full[:600]
    bullets = re.findall(r"^\s*[-•]\s*(.+)$", full, flags=re.M)
    risks = re.findall(r"Risks?:\s*(.*)", full, flags=re.I)
    opps = re.findall(r"Opportunities?:\s*(.*)", full, flags=re.I)

    def split_inline_list(s):
        return [x.strip(" -•\n\r\t") for x in re.split(r"[;•\n-]", s) if len(x.strip()) > 0]

    risks_list = split_inline_list(risks[0]) if risks else []
    opps_list = split_inline_list(opps[0]) if opps else []
    if len(bullets) < 3:
        # try to synthesize from sentences
        bullets = [x.strip() for x in re.split(r"(?<=[.])\s+", summary) if len(x.strip()) > 0][:5]

    # Sanitize categories to list
    # cats_list = [c for c in cats_list if any(c.lower() in k.lower() for k in CATEGORIES)]
    # if not cats_list:
    #     cats_list = ["Competitive intel & new SKUs"]

    return cats_list, summary.strip(), bullets[:6], risks_list[:3] + opps_list[:3]


# ---- Pipeline ----

def process_item(source: RssSource, title: str, url: str, published: str, state: Dict[str, bool],timestamp_dir_name):
    key = hash_str(url)
    if state.get(key):
        return None
    raw_dir = RAW_DIR / source.name / timestamp_dir_name
    raw_dir.mkdir(parents=True, exist_ok=True)

    record = {
        "source": source.name,
        "title": title,
        "url": url,
        "published": published,
        "fetched_at": now_string(),
    }

    # Extract HTML text
    text = extract_text_from_url(url)
    record["text_len"] = len(text)

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

    # Summarize
    log.info(f"summarising url: {url}, title: {title}")
    cats, summary, bullets, risk_opp = call_openai_summary(source, text, url, title)

    item = SummaryItem(
        source=source.name, title=title, url=url, published=published,
        categories=cats, summary=summary, key_points=bullets,
        risks=risk_opp[:3], opportunities=risk_opp[3:]
    )

    # Persist raw item (JSONL per source)
    jl = raw_dir / f"{source.name}.jsonl"
    with jl.open("a", encoding="utf-8") as f:
        f.write(json.dumps(item.model_dump(), ensure_ascii=False) + "\n")

    state[key] = True
    return item


def crawl_once() -> List[SummaryItem]:
    ensure_dirs()
    state = load_state()
    results: List[SummaryItem] = []
    timestamp_dir_name = now_string()
    # RSS first
    for src in SOURCES:
        for feed in src.rss_feeds:
            log.info(f"RSS: {src.name} <- {feed}")
            entries = fetch_rss_entries(feed)
            for e in tqdm(entries, desc=f"{src.name} RSS"):
                it = process_item(src, e["title"], e["link"], e["published"], state, timestamp_dir_name)
                if it:
                    results.append(it)

    # Listing pages (scrape) for sources without reliable RSS
    for source in SOURCES:
        for url in source.html_pages:
            log.info(f"SCRAPE: {source.name} <- {url}")
            html = get_html(url)
            if not html:
                continue
            links = guess_article_links(url, html)
            for link in tqdm(links[:25], desc=f"{source.name} LIST"):
                title_guess = sanitize_filename(link.split("/")[-1]).replace("_", " ")
                it = process_item(source, title_guess, link, "", state, timestamp_dir_name)
                if it:
                    results.append(it)

    save_state(state)
    return results


def write_summary_report(items: List[SummaryItem]) -> pathlib.Path:
    if not items:
        log.info("No new items this run.")
        return SUMMARY_DIR / f"{now_string()}_empty.md"

    # Group by categories and by source
    by_cat: Dict[str, List[SummaryItem]] = {c: [] for c in CATEGORIES}
    for it in items:
        for c in it.categories:
            if c in by_cat:
                by_cat[c].append(it)
            else:
                by_cat.setdefault(c, []).append(it)

    ts = now_string()
    path = SUMMARY_DIR / f"{ts}_market-summary.md"
    lines = []
    lines.append(f"# Beverage Market Overview — {ts}\n")
    lines.append(f"_Sources: {', '.join(sorted(set(i.source for i in items)))}_")
    lines.append("")

    for cat, lst in by_cat.items():
        if not lst:
            continue
        lines.append(f"## {cat}")
        lines.append("<hr>")
        lines.append("")
        for i in lst:
            lines.append(f"### {i.title}")
            lines.append(f"- **Source:** {i.source} | **Published:** {i.published or 'n/a'}")
            lines.append(f"- **Link:** {i.url}")
            lines.append("")
            lines.append("### Summary:")
            lines.append(i.summary.strip())
            lines.append("<hr>")
            lines.append("")
            # if i.key_points:
            #     lines.append("**Key points:**")
            #     for b in i.key_points:
            #         lines.append(f"- {b}")
            # if i.risks:
            #     lines.append("**Risks:**")
            #     for r in i.risks:
            #         lines.append(f"- {r}")
            # if i.opportunities:
            #     lines.append("**Opportunities:**")
            #     for o in i.opportunities:
            #         lines.append(f"- {o}")
            # lines.append("")
        lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")
    log.info(f"Summary written -> {path}")
    return path


# ---- CLI / Runner ----

def run_once():
    items = crawl_once()
    write_summary_report(items)

def run_interval(minutes: int):
    scheduler = BackgroundScheduler(daemon=True)
    scheduler.add_job(run_once, "interval", minutes=minutes, next_run_time=datetime.datetime.utcnow())
    scheduler.start()
    try:
        while True:
            time.sleep(5)
    except KeyboardInterrupt:
        log.info("Shutting down scheduler.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Bev Analyser Market Monitor")
    parser.add_argument("--once", action="store_true", help="Run once and exit")
    parser.add_argument("--interval-min", type=int, default=0, help="Run every N minutes (APScheduler)")
    args = parser.parse_args()

    if args.once or args.interval_min <= 0:
        run_once()
    else:
        run_interval(args.interval_min)

import argparse
import datetime
import time
import dotenv
# Optional: scheduler mode
from apscheduler.schedulers.background import BackgroundScheduler
from openai import OpenAI
from tqdm import tqdm
from prompts import *
from report_manager import *
from rss_sources import SOURCES, RssSource
from scraping_utils import *
from state_manager import *

dotenv.load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


# ---- Logging ----
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
log = logging.getLogger("bev-monitor")


def ensure_dirs():
    for p in [DATA_DIR, RAW_DIR, OUT_DIR, SUMMARY_DIR]:
        p.mkdir(parents=True, exist_ok=True)

def now_string() -> str:
    return datetime.datetime.utcnow().strftime("%Y-%m-%d_%H%M%S_UTC")

def sanitize_filename(s: str) -> str:
    return re.sub(r"[^a-zA-Z0-9._-]+", "_", s)[:100]


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

def call_openai_summary(text: str, url: str, title: str) -> Tuple[List[str], str, List[str], List[str]]:
    log.info("call_openai_summary(...) started")
    clipped = text[:OPENAI_MAX_CHARS]
    rsp = client.responses.create(
        model=OPENAI_MODEL,
        input=[
            {"role": "system", "content": global_system_prompt},
            {"role": "user", "content": get_user_prompt(url, title, CATEGORIES, clipped)},
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
        return full.split(f"### {name}:")[1].split("\n\n")[0]

    summary = section("Summary")
    key_points = section("Key Points")
    risks = section("Risks")
    opportunities = section("Opportunities")


    return cats_list, summary.strip(), key_points.strip(), risks.strip(), opportunities.strip()


# ---- Pipeline ----

def process_item(source: RssSource, title: str, url: str, published: str, state: Dict[str, bool], timestamp_dir_name):
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
    cats, summary, key_points, risks, opps = call_openai_summary(text, url, title)

    item = SummaryItem(
        source=source.name, title=title, url=url, published=published,
        categories=cats, summary=summary, key_points=key_points,
        risks=risks, opportunities=opps
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
                title_guess = sanitize_filename(link.split("/")[-1]).replace("_", " ") #add llm call here to guess the article title correctly
                it = process_item(source, title_guess, link, "", state, timestamp_dir_name)
                if it:
                    results.append(it)

    save_state(state)
    return results, timestamp_dir_name

# ---- CLI / Runner ----

def run_once():
    items, timestamp_dir_name = crawl_once()
    write_summary_report(items, timestamp_dir_name)

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

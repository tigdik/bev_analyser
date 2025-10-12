import reports_dao
from report_manager import *
from rss_reader import *
from scraping_utils import *
from state_manager import *
import dotenv

dotenv.load_dotenv()

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

def get_summaries() -> List[SummaryItem]:
    ensure_dirs()
    state = load_state()
    timestamp_dir_name = now_string()
    results: List[SummaryItem] = []
    summaries = read_summaries_from_rss_sources(timestamp_dir_name)
    for summary in summaries:
        if not summary:
            continue
        reports_dao.save_report(summary, timestamp_dir_name, state)

    save_state(state)
    return results, timestamp_dir_name

def run():
    items, timestamp_dir_name = get_summaries()
    write_summary_report(items, timestamp_dir_name)


if __name__ == "__main__":
    run()

from domain import SummaryItem
from configs import *
import json, hashlib
from typing import Dict
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
log = logging.getLogger("bev-monitor")

def hash_str(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:16]

def save_report(report: SummaryItem, timestamp_dir_name:str, state: Dict[str, bool]):
    if not report:
        log.info(f"save_report, SummaryItem is None!")
        return
    else:
        key = hash_str(report.url)
        if state.get(key)==None:
            raw_dir = RAW_DIR / report.source / timestamp_dir_name
            raw_dir.mkdir(parents=True, exist_ok=True)
            jl = raw_dir / f"{report.source}.jsonl"
            with jl.open("a", encoding="utf-8") as f:
                f.write(json.dumps(report.model_dump(), ensure_ascii=False) + "\n")
            state[key] = True
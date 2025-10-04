from configs import *
from typing import List, Dict, Optional, Tuple
import os, re, json, hashlib

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
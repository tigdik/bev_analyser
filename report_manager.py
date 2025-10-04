from configs import *
import logging
from domain import *

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
log = logging.getLogger("bev-monitor")


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

def write_summary_report(items: List[SummaryItem], md_file_dt_prefix:str) -> pathlib.Path:
    if not items:
        log.info("No new items this run.")
        return SUMMARY_DIR / f"{md_file_dt_prefix}_empty.md"

    # Group by categories and by source
    by_cat: Dict[str, List[SummaryItem]] = {c: [] for c in CATEGORIES}
    for it in items:
        for c in it.categories:
            if c in by_cat:
                by_cat[c].append(it)
            else:
                by_cat.setdefault(c, []).append(it)
    path = SUMMARY_DIR / f"{md_file_dt_prefix}_market-summary.md"
    lines = []
    lines.append(f"# Beverage Market Overview. Updated at {md_file_dt_prefix}\n")
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
            lines.append(i.summary)
            if i.key_points:
                lines.append("### Key points:")
                lines.append(i.key_points)
            if i.risks:
                lines.append("### Risks:")
                lines.append(i.risks)
            if i.opportunities:
                lines.append("### Opportunities:")
                lines.append(i.opportunities)
            lines.append("")
            lines.append("<hr>")
            lines.append("")
        lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")
    log.info(f"Summary written -> {path}")
    return path
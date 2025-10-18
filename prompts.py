global_system_prompt = (
    "You are a market analyst for a global beverages company covering energy drinks, specifically"
    "functional/sport drinks"
    "Classify content into our monitoring categories provided by user and produce crisp, factual outputs."
)
def generate_category_match_prompt(cats:list[str]) -> str:
    return (
    "this is the list of news categories for non-alcoholic beverage manufacturing/marketing industry: \n"
    f"{cats}\n"
    "read the user message representing industry news article and select the at least 1 category which the article fits best into.\n"
    "note: if there's no match can be detected select 'Miscellaneous' category"
    "return the category"
)

def get_category_user_msg(article:str) -> str:
    return (
    "detect category of the following news article: \n"
     f"{article}"
)

def get_user_prompt(url, title, cats, clipped):
    return f"""
URL: {url}
TITLE: {title}

CATEGORIES TO USE:
{', '.join(cats)}

TASKS:
The content given in section 'TEXT:' below represents a news article related to non-alcoholic beverage manufacturing/marketing industry.
YOUR TASK:
1) Study the article for relevance. If the text is irrelevant to manufacturing and marketing energy drinks, then ignore it and return string 'IRRELEVANT_CONTENT'. Otherwise proceed to the next step
2) Pick the 1-4 most relevant categories for this item (categories specified in paragraph "CATEGORIES TO USE:").
3) Write report based on the article that has following paragraphs:
 * '### Selected Categories:': it provides numbered list of the relevant categories you have created at step 2) above
 * '### Summary:': consists of 4-6 sentence executive summary of the article.
 * '### Key Points:': 3-6 bullet key points (facts only).
 * '### Risks:': upto 3 risks
 * '### Opportunities': upto 3 opportunities

TEXT:
{clipped}
"""

def get_global_summary_prompt(summaries:str) -> str:
    return f"""
    the following text represents a two empty lines delimited list of market news summaries for non-alcoholic beverage manufacturing/marketing industry:
    {summaries}
    YOUR TASK:
    read the list of summaries and produce a summary for beverage industry executives that has following header:
     '# Report'
     followed by paragraphs:
     * '### Summary:': consists of 5-10 sentences executive summary.
     * '### Key Points:': 3-6 bullet key points (facts only).
"""
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
    "note: if there's no match can be detected select 'miscellaneous' category"
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
1) Pick the 1-4 most relevant categories for this item (categories specified in paragraph "CATEGORIES TO USE:").
2) Write a 4-6 sentence executive summary paragraph named '### Summary:' focused on implications for type of beverages specified by user.
3) make sure the first paragraph of your answer is called '### Selected Categories:' and it provides numbered list of the relevant categories 
3) Provide 3-6 bullet key points (facts only), name this paragraph '### Key Points:'.
4) Provide up to upto 3 risks & upto 3 opportunities, if any, naming corresponding paragraphs '### Risks' and '### Opportunities' respectively

TEXT:
{clipped}
"""
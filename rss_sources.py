from typing import Callable, List
import os
from pydantic import BaseModel
from openai import OpenAI
from configs import OPENAI_MODEL, CATEGORIES
from prompts import *
import dotenv

dotenv.load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def parse_fooddive_categories(article: str):
    cat_paragraph_title = "### Relevant Categories\n"
    cats_prefixed = article.split("\n\n")[0].split("\n")[1:]
    cats = list(map(lambda cat: cat[2:].strip(), cats_prefixed))
    return cats

def default_categories_parser(article:str):
    rsp = client.responses.create(
        model=OPENAI_MODEL,
        input=[
            {"role": "system", "content": generate_category_match_prompt(CATEGORIES)},
            {"role": "user", "content": get_category_user_msg(article)}
        ],
        temperature=0.2,
    )
    cat = getattr(rsp, "output_text", None)
    return cat

class RssSource(BaseModel):
    name: str
    rss_feeds: list[str]
    html_pages: list[str]
    get_categories_fn: Callable[[str], List[str]] = default_categories_parser

    def get_categories(self, article):
        return self.get_categories_fn(article)



SOURCES = [
            RssSource(
                      name="foodbusinessnews",
                      rss_feeds=["https://www.foodbusinessnews.net/rss/2", "https://www.foodbusinessnews.net/rss/topic/515-non-alcoholic-beverages"],
                      html_pages=[],
                      get_categories_fn=parse_fooddive_categories
                      ),
            RssSource(name="just-drinks", rss_feeds=["https://www.just-drinks.com/news/feed/feed"], html_pages=[]),
            RssSource(
                      name="fooddive",
                      rss_feeds=["https://www.fooddive.com/topic/beverages/"],
                      html_pages=["https://www.fooddive.com/press-release/"],
                      get_categories_fn=parse_fooddive_categories
            ),
            RssSource(name="bevnet",rss_feeds=[],html_pages=["https://www.bevnet.com/news/"])
          ]
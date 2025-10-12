from typing import Callable, List
import os
from pydantic import BaseModel
from openai import OpenAI
from configs import OPENAI_MODEL, CATEGORIES
from prompts import *
import dotenv
from domain import RssSource

dotenv.load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


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



SOURCES = [
            # RssSource(
            #           name="foodbusinessnews",
            #           rss_feeds=["https://www.foodbusinessnews.net/rss/2", "https://www.foodbusinessnews.net/rss/topic/515-non-alcoholic-beverages"],
            #           html_pages=[]
            #           ),
            # RssSource(name="just-drinks", rss_feeds=["https://www.just-drinks.com/news/feed/feed"], html_pages=[]),
            RssSource(
                      name="bevindustry.com",
                      rss_feeds=["https://www.bevindustry.com/rss/16"],
                      html_pages=[]
                      )#,
            # RssSource(name="just-drinks", rss_feeds=["https://www.just-drinks.com/news/feed/feed"], html_pages=[]),

            # RssSource(
            #           name="fooddive",
            #           rss_feeds=["https://www.fooddive.com/feeds/news/"],
            #           html_pages=[]
            #               # html_pages=["https://www.fooddive.com/press-release/"]
            # ),
            # RssSource(name="bevnet",rss_feeds=[],html_pages=["https://www.bevnet.com/news/"]) # for html pages, each RssSource needs custom html data scraper
          ]
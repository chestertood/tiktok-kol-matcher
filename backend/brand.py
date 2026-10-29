import json

from backend.common import ask_json, run_actor
from backend.facebook_client import get_page, get_posts

# Page fields worth sending to Claude; contact details (email/phone) are left out on purpose.
PAGE_KEYS = ("title", "categories", "intro", "info", "priceRange", "followers", "creation_date", "ad_status")


def _try(label, fn):
    try:  # scraping is flaky; one failed source should not kill the run
        return fn()
    except Exception as e:
        print(f"warn: {label} failed, continuing without it ({e})")


def _crawl(url):
    pages = run_actor(
        "apify/website-content-crawler",
        {"startUrls": [{"url": url}], "maxCrawlPages": 3, "maxRequestRetries": 1},  # fail fast on WAF 403
    )
    return "\n".join(p.get("text", "") for p in pages)[:6000]


def analyze_brand(facebook, website=None):
    page = get_page(facebook)  # required: without it there is nothing to analyze
    posts = _try("facebook posts", lambda: get_posts(facebook)) or []
    # website is opt-in: the page's own site is often behind a WAF and the posts already show the brand
    site_text = (_try("website crawl", lambda: _crawl(website)) if website else "") or ""

    return ask_json(f"""You are an influencer-marketing analyst for a Thai agency.
Analyze this brand from its Facebook page, recent posts and website.
Return JSON only, keys (text values in Thai):
brand, industry, summary (2-3 sentences), audience (who buys: age/interests),
tone, content_style, kol_strategy (object: nano|micro|mega -> one sentence on how
that tier should be used for this brand), tiktok_queries (8 Thai keywords/hashtags
to find fitting Thai TikTok creators; mix niche and broad).

FACEBOOK PAGE:
{json.dumps({k: page.get(k) for k in PAGE_KEYS}, ensure_ascii=False)}

RECENT POSTS (text, likes, comments, shares):
{json.dumps(posts[:15], ensure_ascii=False)[:6000]}

WEBSITE:
{site_text}""")

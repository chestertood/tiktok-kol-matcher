import json
import sys
from urllib.parse import parse_qs, urlparse

from backend.common import run_actor


def normalize_url(url):
    """Canonical page URL: drops web./m. host, tracking params and sub-paths."""
    u = urlparse(url.strip())
    if not u.netloc.endswith("facebook.com"):
        raise ValueError(f"not a Facebook URL: {url}")
    if u.path.rstrip("/").endswith("profile.php"):
        return f"https://www.facebook.com/profile.php?id={parse_qs(u.query)['id'][0]}"
    page = u.path.strip("/").split("/")[0]
    if not page:
        raise ValueError(f"no page name in URL: {url}")
    return f"https://www.facebook.com/{page}"


def get_page(url):
    """Public page info (name, category, about, followers, ...) from a Facebook page URL."""
    items = run_actor("apify/facebook-pages-scraper", {"startUrls": [{"url": normalize_url(url)}]})
    if not items:
        raise RuntimeError(f"no data returned for {url}")
    return items[0]


def get_posts(url, limit=20):
    """Recent public posts: text + like/comment/share counts. No commenter data (PDPA)."""
    items = run_actor(
        "apify/facebook-posts-scraper",
        {"startUrls": [{"url": normalize_url(url)}], "resultsLimit": limit},
    )
    return [
        {"text": p["text"], "likes": p.get("likes", 0), "comments": p.get("comments", 0),
         "shares": p.get("shares", 0), "time": p.get("time")}
        for p in items if p.get("text")
    ]


if __name__ == "__main__":
    assert normalize_url("https://web.facebook.com/CPUCore2Duo/?_rdc=1&_rdr#") == "https://www.facebook.com/CPUCore2Duo"
    assert normalize_url("facebook.com/x/posts/1".join(["https://", ""])) == "https://www.facebook.com/x"
    assert normalize_url("https://m.facebook.com/profile.php?id=123&ref=x") == "https://www.facebook.com/profile.php?id=123"
    if len(sys.argv) > 1:
        sys.stdout.reconfigure(encoding="utf-8")  # Windows console defaults to cp874
        fetch = get_posts if sys.argv[2:] == ["posts"] else get_page
        print(json.dumps(fetch(sys.argv[1]), ensure_ascii=False, indent=2))
    else:
        print("normalize_url ok; pass a URL to fetch")

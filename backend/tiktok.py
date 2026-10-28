import re
from collections import defaultdict
from statistics import mean

from backend.common import run_actor

# (name, min followers). Boundaries at 200K/600K follow Convert Cake's own KOL tiers;
# the 10K-200K gap on their site is filled by micro, 1K-10K is nano.
TIERS = (("nano", 1_000), ("micro", 10_000), ("mid", 200_000), ("mega", 600_000))
TIER_LABEL = {"nano": "Nano 1K-10K", "micro": "Micro 10K-200K", "mid": "Mid 200K-600K", "mega": "Mega 600K+"}
EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
THAI = re.compile(r"[฀-๿]")


def tier_of(followers):
    tier = None
    for name, low in TIERS:
        if followers >= low:
            tier = name
    return tier


def is_thai(captions):
    return bool(captions) and sum(bool(THAI.search(c)) for c in captions) * 2 >= len(captions)


def find_creators(queries, videos_per_query=40):
    videos = run_actor(
        "clockworks/tiktok-scraper",
        {"searchQueries": queries, "resultsPerPage": videos_per_query, "shouldDownloadVideos": False},
    )
    by_author = defaultdict(list)
    for v in videos:
        name = (v.get("authorMeta") or {}).get("name")
        if name:
            by_author[name].append(v)

    creators = []
    for name, vs in by_author.items():
        meta = vs[0]["authorMeta"]
        followers = meta.get("fans") or 0
        captions = [v.get("text") or "" for v in vs]  # scraper may return null fields
        tier = tier_of(followers)
        if not tier or not is_thai(captions):
            continue
        # ponytail: stats come only from videos the search returned (not the whole channel);
        # upgrade path: scrape each profile's latest N videos for unbiased averages.
        n = lambda v, k: v.get(k) or 0  # noqa: E731  null-safe counter
        views = mean(n(v, "playCount") for v in vs)
        rates = [  # skip videos with no view count; cap at 100% so one odd video can't dominate
            min((n(v, "diggCount") + n(v, "commentCount") + n(v, "shareCount")) / n(v, "playCount"), 1)
            for v in vs if n(v, "playCount")
        ]
        er = mean(rates) if rates else 0
        bio = meta.get("signature") or ""
        email = EMAIL.search(bio)
        creators.append({
            "handle": name,
            "url": f"https://www.tiktok.com/@{name}",
            "tier": tier,
            "followers": followers,
            "avg_views": int(views),
            "reach": views / max(followers, 1),  # avg views as a share of followers
            "engagement_rate": er,  # (likes+comments+shares)/views
            "bio": bio,
            "email": email.group() if email else None,
            "bio_link": meta.get("bioLink"),
            "captions": captions[:5],
        })
    return creators


if __name__ == "__main__":
    assert tier_of(500) is None and tier_of(5_000) == "nano" and tier_of(10_000) == "micro"
    assert tier_of(200_000) == "mid" and tier_of(2_000_000) == "mega"
    assert is_thai(["รีวิวกันแดด", "hello", "ผิวแพ้ง่าย"]) and not is_thai(["hello", "world"])
    assert EMAIL.search("งานโฆษณา ติดต่อ a.b@mail.co.th 🙏").group() == "a.b@mail.co.th"
    print("ok")

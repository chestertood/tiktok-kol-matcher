import re
from collections import defaultdict
from statistics import mean

from backend.common import run_actor

# (name, min followers, max followers). Exactly Convert Cake's KOL tiers
# (convertcake.com/service/kol-inflencer-marketing): Nano 1K-10K, Micro 201K-600K, Mega 601K+.
# Their page defines nothing for 10K-200K, so creators in that gap are skipped.
TIERS = (("nano", 1_000, 10_000), ("micro", 201_000, 600_999), ("mega", 601_000, float("inf")))
TIER_LABEL = {"nano": "Nano 1K-10K", "micro": "Micro 201K-600K", "mega": "Mega 601K+"}
EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
THAI = re.compile(r"[฀-๿]")


def tier_of(followers):
    return next((name for name, low, high in TIERS if low <= followers <= high), None)


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
    assert tier_of(500) is None and tier_of(5_000) == "nano" and tier_of(10_000) == "nano"
    assert tier_of(50_000) is None and tier_of(201_000) == "micro" and tier_of(600_999) == "micro"
    assert tier_of(601_000) == "mega" and tier_of(2_000_000) == "mega"
    assert is_thai(["รีวิวกันแดด", "hello", "ผิวแพ้ง่าย"]) and not is_thai(["hello", "world"])
    assert EMAIL.search("งานโฆษณา ติดต่อ a.b@mail.co.th 🙏").group() == "a.b@mail.co.th"
    print("ok")

import csv
import re

from backend.tiktok import TIER_LABEL

CSV_COLS = ("tier", "rank", "handle", "url", "followers", "avg_views", "engagement_rate",
            "relevance", "score", "reason", "email", "bio_link", "pitch")


def out_name(brand, ext):
    """'iHAVECPU (บริษัท ... จำกัด)' -> 'iHAVECPU_results.csv'; the part in brackets is dropped."""
    stem = re.sub(r"\W+", "_", brand["brand"].split("(")[0]).strip("_") or "brand"
    return f"{stem}_results.{ext}"


def write_csv(ranked, path):
    """One row per KOL. utf-8-sig so Excel opens Thai text correctly."""
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, CSV_COLS, extrasaction="ignore", restval="")
        w.writeheader()
        for tier in TIER_LABEL:
            for i, c in enumerate(ranked.get(tier, []), 1):
                w.writerow({**c, "tier": TIER_LABEL[tier], "rank": i,
                            "engagement_rate": round(c["engagement_rate"], 4), "score": round(c["score"], 3)})


def contact(c):
    return c["email"] or c["bio_link"] or f"DM @{c['handle']} บน TikTok"


def render(brand, ranked):
    out = [
        f"# KOL Report: {brand['brand']}", "",
        "## Brand analysis", "",
        brand["summary"], "",
        f"- **Industry:** {brand['industry']}",
        f"- **Audience:** {brand['audience']}",
        f"- **Tone:** {brand['tone']}",
        f"- **Content style:** {brand['content_style']}", "",
        "## Recommended TikTok KOLs", "",
    ]
    for tier in TIER_LABEL:
        cs = ranked.get(tier)
        if not cs:
            continue
        out += [
            f"### {TIER_LABEL[tier]}", "",
            f"_{brand.get('kol_strategy', {}).get(tier, '')}_", "",
            "| # | KOL | Followers | Avg views | ER | Relevance | Score | Why | Contact |",
            "|---|---|---|---|---|---|---|---|---|",
        ]
        for i, c in enumerate(cs, 1):
            out.append(
                f"| {i} | [@{c['handle']}]({c['url']}) | {c['followers']:,} | {c['avg_views']:,} "
                f"| {c['engagement_rate']:.1%} | {c['relevance']:g}/10 | {c['score']:.2f} | {c['reason']} | {contact(c)} |"
            )
        out.append("")
    drafts = [c for cs in ranked.values() for c in cs if c.get("pitch")]
    if drafts:
        out += ["## Outreach drafts (review before sending)", ""]
        out += [f"- **@{c['handle']}**: {c['pitch']}" for c in drafts]
    out += ["", "_ER = (likes+comments+shares)/views, from sampled videos. Audience demographics are not available from public data._"]
    return "\n".join(out)


if __name__ == "__main__":  # offline preview with fake data, no API credits
    brand = {"brand": "Demo", "summary": "ตัวอย่าง", "industry": "skincare", "audience": "หญิง 20-35",
             "tone": "เป็นกันเอง", "content_style": "รีวิว", "kol_strategy": {"micro": "รีวิวเชิงลึก"}}
    kol = {"handle": "demo.kol", "url": "https://www.tiktok.com/@demo.kol", "followers": 96000, "avg_views": 41000,
           "engagement_rate": 0.084, "relevance": 9, "score": 0.88, "reason": "เนื้อหาตรงกลุ่ม",
           "email": None, "bio_link": None, "pitch": "สวัสดีค่ะ ..."}
    assert out_name({"brand": "iHAVECPU (บริษัท ไอ แฮฟ ซีพียู จำกัด)"}, "csv") == "iHAVECPU_results.csv"
    assert out_name({"brand": "Dr. Pong's Shop"}, "md") == "Dr_Pong_s_Shop_results.md"
    text = render(brand, {"micro": [kol]})
    assert "@demo.kol" in text and "DM @demo.kol" in text and "Micro 10K-200K" in text
    write_csv({"micro": [kol]}, "sample.csv")
    rows = list(csv.DictReader(open("sample.csv", encoding="utf-8-sig", newline="")))
    assert rows[0]["handle"] == "demo.kol" and rows[0]["tier"] == "Micro 10K-200K" and rows[0]["pitch"] == "สวัสดีค่ะ ..."
    print(text)

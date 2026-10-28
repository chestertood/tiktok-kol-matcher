import json
from collections import defaultdict

from backend.common import ask_json

W_REL, W_ENG, W_REACH = 0.5, 0.3, 0.2
ER_CAP = 0.10  # engagement rate at/above 10% counts as full marks
MIN_REL = 5  # below this a creator is a poor fit however high the engagement


def combine(relevance, er, reach):
    return W_REL * relevance / 10 + W_ENG * min(er / ER_CAP, 1) + W_REACH * min(reach, 1)


def rank(brand, creators, per_tier=5, pool_per_tier=12):
    """-> {tier: [top creators]}; Claude scores fit, engagement/reach come from the data."""
    by_tier = defaultdict(list)
    for c in creators:
        by_tier[c["tier"]].append(c)
    pool = [c for cs in by_tier.values() for c in sorted(cs, key=lambda c: -c["engagement_rate"])[:pool_per_tier]]
    if not pool:
        return {}

    # ponytail: no audience demographics from public data; fit is judged from captions + bio.
    # Upgrade path: paid creator-analytics API for real audience splits.
    scored = ask_json(f"""Brand profile:
{json.dumps(brand, ensure_ascii=False)}

For each TikTok creator below return a JSON list of
{{"handle", "relevance" (0-10 fit with the brand's audience, tone, content style),
"kind" ("creator" for an individual/independent creator, "brand_channel" for the official
channel of any company, media outlet or the client itself),
"reason" (one short Thai sentence)}}.

Creators:
{json.dumps([{k: c[k] for k in ("handle", "followers", "bio", "captions")} for c in pool], ensure_ascii=False)}""")
    by_handle = {s["handle"]: s for s in scored if isinstance(s, dict) and "handle" in s}

    ranked = defaultdict(list)
    for c in pool:
        s = by_handle.get(c["handle"])
        if s and s.get("kind", "creator") == "creator":
            rel = float(s["relevance"])  # model may return "8" as a string
            if rel < MIN_REL:
                continue
            ranked[c["tier"]].append({
                **c, "relevance": rel, "reason": s.get("reason", ""),
                "score": combine(rel, c["engagement_rate"], c["reach"]),
            })
    return {t: sorted(cs, key=lambda x: -x["score"])[:per_tier] for t, cs in ranked.items()}


def add_pitches(brand, ranked):
    """Draft Thai outreach message per finalist. A human reviews and sends; never auto-sent."""
    finalists = [c for cs in ranked.values() for c in cs]
    if not finalists:
        return ranked
    pitches = ask_json(f"""Brand: {json.dumps(brand, ensure_ascii=False)}
Write a friendly 2-sentence Thai collaboration opener from the agency to each creator,
referring to their content. Return JSON list of {{"handle", "pitch"}}.
Creators: {json.dumps([{k: c[k] for k in ("handle", "bio", "captions")} for c in finalists], ensure_ascii=False)}""")
    by_handle = {p["handle"]: p.get("pitch", "") for p in pitches if isinstance(p, dict) and "handle" in p}
    for c in finalists:
        c["pitch"] = by_handle.get(c["handle"], "")
    return ranked


if __name__ == "__main__":
    assert combine(10, 0.10, 1.0) == 1.0
    assert combine(0, 0, 0) == 0
    assert combine(10, 0.5, 5) == 1.0  # ER and reach capped
    assert abs(combine(5, 0.05, 0.5) - 0.5) < 1e-9
    print("ok")

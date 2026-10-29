# TikTok KOL Matcher (Thailand)

Give it a client's **Facebook page URL**; it analyzes the brand with Claude, finds Thai TikTok creators, and returns a ranked shortlist per follower tier with engagement stats, contact channels and a draft outreach message. Built for Convert Cake's influencer team: it automates the "pick the KOLs" step, a human still contacts and negotiates.

```
Facebook page URL (+ optional website)
  -> facebook_client.py  page summary + recent posts            (Apify)
  -> brand.py            Claude: brand, audience, tone, content style, 8 Thai TikTok queries
  -> tiktok.py           TikTok search -> followers, avg views, ER, bio, email/link, tier  (Apify)
  -> rank.py             Claude: relevance + creator-vs-brand-channel; score; top N per tier; outreach drafts
  -> report.py           <brand>_results.md + .csv       pipeline.py -> results.json + runs/<page>.json
  -> app.py              Streamlit UI: charts, tier tabs, downloads
```

## Project structure

```
app.py               Streamlit UI
main.py              CLI entry point
backend/             pipeline: facebook_client, brand, tiktok, rank, report, pipeline, common
docs/                assessment brief, notes
examples/            sample_report.md, sample_results.csv, sample_results.json (output of a real run)
requirements.txt     dependencies
.env.example         copy to .env and fill in keys
```

Generated at runtime (git-ignored): `<brand>_results.md`, `<brand>_results.csv`, `results.json`, `runs/`, `.cache/`.

## Setup

Python 3.12, Windows/macOS/Linux.

```powershell
python -m venv .venv
.venv\Scripts\activate            # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and fill in (never commit it):

```
APIFY_TOKEN=...
ANTHROPIC_API_KEY=...
```

## Run

**Web app (recommended for demo)**

```powershell
streamlit run app.py              # opens http://localhost:8501
```

Enter the Facebook URL in the sidebar, press **Find KOLs**. Every run is saved per Facebook page in `runs/`. To switch client or reopen a past result without scraping or calling Claude, pick a file under **Saved results** (past runs and `examples/sample_results.json`) or upload a results `.json`, then press **Open results**.

**CLI**

```powershell
python main.py --facebook https://www.facebook.com/CPUCore2Duo --per-tier 5
python main.py --facebook <url> --website https://example.com    # optional extra source
```

Note: use `streamlit run app.py`, not `python app.py`.

## Outputs

| File | Written by | Use |
|---|---|---|
| `<brand>_results.md` | CLI | readable report: brand analysis, per-tier tables, contacts, outreach drafts |
| `<brand>_results.csv` | CLI and app | one row per KOL; open in Excel/Sheets (UTF-8 BOM so Thai displays correctly) |
| `results.json` | CLI and app | latest run |
| `runs/<page>.json` | CLI and app | one file per Facebook page; listed under *Saved results* in the app, or upload any of these |
| `.cache/` | every Apify call | raw scraper output keyed by (actor, input); reruns cost no Apify credits. Delete it or set `NO_CACHE=1` for fresh data |

## How ranking works

- **Tiers:** Nano 1K-10K, Micro 201K-600K, Mega 601K+ — exactly Convert Cake's [KOL tiers](https://convertcake.com/service/kol-inflencer-marketing/). Their page defines nothing for 10K-200K, so creators in that range are skipped.
- **Thai filter:** a creator counts as Thai when most of their captions contain Thai script.
- **Claude** sees the brand profile and each candidate's bio + captions, and returns `relevance` (0-10), `kind` (`creator` or `brand_channel`) and a one-line Thai reason. Brand/media channels (including the client's own) and relevance < 5 are dropped.
- **Score** = 0.5 x relevance/10 + 0.3 x min(ER / 10%, 1) + 0.2 x min(avg views / followers, 1).
  - ER = (likes + comments + shares) / views, per video, capped at 100%, averaged.
  - Reach = average views as a share of followers.
- Top N per tier (default 5); a tier may have fewer if nobody fits.
- **Contact:** email found in the creator's own bio, else bio link, else "DM on TikTok". Drafts are for a human to review; nothing is sent automatically.

## Checks (no credits used)

```powershell
python -m backend.tiktok            # tiers, Thai detection, email extraction
python -m backend.rank              # score formula
python -m backend.report            # sample report + CSV round trip
python -m backend.facebook_client   # URL normalization
python -m backend.facebook_client <url> [posts]   # live: one Facebook source (1 Apify call)
```

## Technical challenges and decisions

| Challenge | Decision |
|---|---|
| Some sites return 403 to scrapers (e.g. a client's own site behind a WAF) | The Facebook page + posts is the primary source; the website is opt-in and skipped on failure. No proxy tricks to bypass blocking. |
| TikTok search is slow and rate-limited (timeouts, retries; ~4-5 min per run) | Disk cache on every Apify call; app can reload the last run. |
| Search returns the client's own channels and unrelated high-engagement accounts | Claude labels `kind` and relevance; filter brand channels and relevance < 5. |
| Scraped fields can be null or missing | Null-safe counters, per-video ER cap, defensive parsing of Claude's JSON. |
| LLM output must be machine-readable | JSON-only prompts, thinking blocks skipped, error if the response hits `max_tokens`. |

## Known limits

- **No audience demographics** (age/gender/location of followers): not available from public TikTok data. Fit is judged from captions and bio. Upgrade path: a paid creator-analytics API, or asking creators for their analytics screenshots.
- **Creator stats come only from the videos the search returned**, not the full channel, so averages can be biased towards viral videos (small channels may show inflated views). Upgrade path: scrape each shortlisted profile's latest N videos.
- Apify actor output field names (`authorMeta`, `playCount`, posts `text`/`likes`) are tied to the current versions of those actors.
- Email in bio is found for only a minority of creators; the rest need a DM or the agency's existing creator network.
- Competitor collaborations are noted by Claude when visible in captions but not systematically verified.

## Ethics and privacy

- Public data only; no login, no private accounts, no bypassing of access controls.
- Contact details are only what creators publish in their own bio for business enquiries. Nothing is auto-sent; a human reviews every message.
- Facebook commenter names/IDs are not collected. The page's own email/phone are not sent to the model.
- Stored data: public handles and metrics, brand analysis. Follow platform terms and Thailand's PDPA; delete `.cache/` and `results.*` when a client engagement ends.
- Rankings are a decision aid, not a verdict: relevance is an LLM judgement from short text and can be wrong. Review before outreach.

## Business impact and next steps

- Replaces manual TikTok browsing for the shortlisting step; the team starts from a ranked, explained list per tier instead of a blank search.
- Next: per-profile deep scrape for unbiased stats; audience-demographics source; Facebook comments for richer audience signal; brand-safety check on recent videos; CRM/Sheets export with outreach status; Thai-language re-ranking evals against the team's past picks.

## Sources

- Apify: [TikTok Scraper](https://apify.com/clockworks/tiktok-scraper), [Facebook Pages Scraper](https://apify.com/apify/facebook-pages-scraper), [Facebook Posts Scraper](https://apify.com/apify/facebook-posts-scraper), [Website Content Crawler](https://apify.com/apify/website-content-crawler)
- Anthropic [Claude API](https://docs.anthropic.com)
- [Streamlit](https://streamlit.io)
- Convert Cake KOL tiers: https://convertcake.com/service/kol-inflencer-marketing/

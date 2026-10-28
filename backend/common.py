import hashlib
import json
import os
import re
from pathlib import Path

from anthropic import Anthropic
from apify_client import ApifyClient
from dotenv import load_dotenv

load_dotenv()

MODEL = "claude-sonnet-5-5"
CACHE = Path(__file__).resolve().parent.parent / ".cache"


def run_actor(actor, run_input):
    """Apify run, cached on disk by (actor, input) so reruns/debugging cost no credits.
    Delete .cache/ or set NO_CACHE=1 for fresh data."""
    key = hashlib.sha1(json.dumps([actor, run_input], sort_keys=True).encode()).hexdigest()
    path = CACHE / f"{key}.json"
    if path.exists() and not os.environ.get("NO_CACHE"):
        print(f"cache hit: {actor}")
        return json.loads(path.read_text(encoding="utf-8"))
    client = ApifyClient(os.environ["APIFY_TOKEN"])
    run = client.actor(actor).call(run_input=run_input)
    items = list(client.dataset(run.default_dataset_id).iterate_items())
    CACHE.mkdir(exist_ok=True)
    path.write_text(json.dumps(items, ensure_ascii=False, default=str), encoding="utf-8")
    return items


def ask_json(prompt):
    msg = Anthropic().messages.create(
        model=MODEL, max_tokens=16000, messages=[{"role": "user", "content": prompt}]
    )
    if msg.stop_reason == "max_tokens":  # thinking tokens count too; truncated JSON would not parse
        raise RuntimeError("Claude hit max_tokens; shrink the prompt or raise the limit")
    text = "".join(b.text for b in msg.content if b.type == "text")  # skip thinking blocks
    return json.loads(re.search(r"[\[{].*[\]}]", text, re.S).group())

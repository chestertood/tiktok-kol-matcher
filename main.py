import argparse
import sys

from backend.pipeline import run
from backend.report import out_name, render, write_csv

sys.stdout.reconfigure(encoding="utf-8")  # Windows console defaults to cp874

p = argparse.ArgumentParser(description="TikTok KOL matcher for the Thai market")
p.add_argument("--facebook", required=True, help="client's Facebook page URL")
p.add_argument("--website", help="optional extra source; skipped if omitted or blocked")
p.add_argument("--per-tier", type=int, default=5)
a = p.parse_args()

brand, ranked = run(a.facebook, a.website, a.per_tier)
report = render(brand, ranked)
open(out_name(brand, "md"), "w", encoding="utf-8").write(report)
write_csv(ranked, out_name(brand, "csv"))
print(report)

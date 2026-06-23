import requests
import json
import csv

CIK = "0000930236"
url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{CIK}.json"
headers = {"User-Agent": "mcdermott.d.r@gmail.com"}

response = requests.get(url, headers=headers)
response.raise_for_status()
data = response.json()

us_gaap_facts = data["facts"]["us-gaap"]
eps_concept_name = "EarningsPerShareDiluted"
eps = us_gaap_facts[eps_concept_name]
unit_name = "USD/shares"
records = eps["units"][unit_name]

# Step 1: same dedup-by-latest-filed logic as before, but keep ALL records
# (not just ones with a Q-frame) so we have access to annual (CY####) and
# 9-month YTD (CY####Q1-Q3 style "instant"/duration) figures too.
by_frame = {}
for record in records:
    frame = record.get("frame")
    if not frame:
        continue
    existing = by_frame.get(frame)
    if existing is None or record["filed"] > existing["filed"]:
        by_frame[frame] = record

# Step 2: pull out explicit quarterly frames (CY####Q#) — these are trustworthy as-is
quarterly_eps = {}
for frame, record in by_frame.items():
    if "Q" in frame and not frame.endswith("I"):  # exclude instant-type frames if present
        quarterly_eps[frame] = record["val"]

# Step 3: derive missing Q4s as Annual - (Q1+Q2+Q3), where all four pieces exist.
# SEC frame convention: full year = "CY####", nine-month YTD doesn't have its own
# single frame for EPS in most filings (each quarter is separately tagged), so we
# derive Q4 = Annual - Q1 - Q2 - Q3 instead of relying on a YTD frame that may not exist.
years_present = set(int(f[2:6]) for f in quarterly_eps)
derived_q4 = {}
for year in years_present:
    annual_frame = f"CY{year}"
    q1 = quarterly_eps.get(f"CY{year}Q1")
    q2 = quarterly_eps.get(f"CY{year}Q2")
    q3 = quarterly_eps.get(f"CY{year}Q3")
    q4_frame = f"CY{year}Q4"

    if q4_frame in quarterly_eps:
        continue  # already have it explicitly, no need to derive

    annual_record = by_frame.get(annual_frame)
    if annual_record and q1 is not None and q2 is not None and q3 is not None:
        derived_val = round(annual_record["val"] - q1 - q2 - q3, 2)
        derived_q4[q4_frame] = derived_val

# Merge explicit + derived, tag the source so you always know which is which
all_quarters = {}
for frame, val in quarterly_eps.items():
    all_quarters[frame] = {"quarter": frame, "eps": val, "source": "reported"}
for frame, val in derived_q4.items():
    all_quarters[frame] = {"quarter": frame, "eps": val, "source": "derived (Annual - Q1 - Q2 - Q3)"}

sorted_quarters = sorted(all_quarters.values(), key=lambda x: x["quarter"])

print(f"Found {len(sorted_quarters)} quarterly EPS data points ({len(quarterly_eps)} reported, {len(derived_q4)} derived):\n")
for item in sorted_quarters:
    flag = "  <- derived" if item["source"].startswith("derived") else ""
    print(f"{item['quarter']:10s} EPS: {item['eps']:>7.2f}{flag}")

with open("rwt_quarterly_eps_complete.csv", "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=["quarter", "eps", "source"])
    writer.writeheader()
    writer.writerows(sorted_quarters)

print("\nExported to rwt_quarterly_eps_complete.csv")
print(f"\nStill missing (no Q4 derivable — annual or one of Q1-Q3 not found): check years not in years_present output if count seems low.")

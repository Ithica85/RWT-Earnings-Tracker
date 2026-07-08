import requests  # the "requests" library lets Python make web requests (like a browser fetching a page)
import json      # the "json" library converts JSON text into Python objects we can work with
import csv       # the "csv" library lets Python write data to a CSV file

# Redwood Trust's unique identifier on SEC EDGAR
# You can verify this at: https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&company=redwood+trust&type=&dateb=&owner=include&count=40&search_text=
CIK = "0000930236"

# Build the URL for the SEC CompanyFacts API endpoint
# This endpoint returns all financial data the company has reported to the SEC in XBRL format
url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{CIK}.json"

# The SEC requires every API request to include a User-Agent header identifying who you are
# Without this, the SEC may block your request
headers = {
    "User-Agent": "mcdermott.d.r@gmail.com"
}

# Make a GET request to the SEC API (like clicking a link in a browser)
# The response is stored in the variable "response"
response = requests.get(url, headers=headers)

# Check if the request succeeded (HTTP status 200 means "OK")
# If something went wrong (e.g. 404 = not found, 403 = blocked), this line will raise an error
response.raise_for_status()

# Convert the raw JSON text from the response into a Python dictionary
data = response.json()

# Print the top-level keys so we can see the structure of the data
# A dictionary key is like a label for a section of data
print("Top-level keys in the response:")
print(list(data.keys()))

# Print the company name to confirm we got the right company
print("\nCompany name:", data["entityName"])

# Print a count of how many financial concepts are in the data
# "facts" holds all the reported numbers; "us-gaap" is the standard US accounting taxonomy
us_gaap_facts = data["facts"]["us-gaap"]
print("\nNumber of US-GAAP financial concepts reported:", len(us_gaap_facts))

# Print the first 5 concept names so we can see what kinds of data are available
print("\nFirst 5 US-GAAP concepts:")
for concept in list(us_gaap_facts.keys())[:5]:
    print(" -", concept)

# Search for concepts whose names contain any of the keywords (case-insensitive)
print("\nSearching for concepts containing keywords...\n")

keywords = ["earn", "share", "income", "net"]

for concept in us_gaap_facts.keys():
    concept_lower = concept.lower()  # lowercase so "Income" and "income" both match

    if any(keyword in concept_lower for keyword in keywords):
        print(concept)

eps_concept_name = "EarningsPerShareDiluted"
if eps_concept_name not in us_gaap_facts:  # check it exists before accessing it, to avoid a KeyError crash
    print(f"'{eps_concept_name}' not found. Available EPS-like concepts:")
    for concept in us_gaap_facts:
        if "EarningsPerShare" in concept:
            print(" -", concept)
    raise SystemExit("Pick the right concept name from the list above and update eps_concept_name.")

eps = us_gaap_facts[eps_concept_name]  # pull out just the EPS diluted concept as its own variable

print("\nEPS Data Structure:")
print(eps.keys())  # show what sections exist inside this concept

print("\nUnits:")
print(eps["units"].keys())  # show what unit types the EPS values are reported in (e.g. USD/shares)

unit_name = list(eps["units"].keys())[0]  # grab the first (and only) unit type as a string: "USD/shares"
records = eps["units"][unit_name]  # store the full list of EPS records in a variable

print("\nFirst 5 EPS Records:")
for record in records[:5]:  # loop through only the first 5 entries in the list
    print(record)

print("\nMost Recent 10 Records:")
for record in records[-10:]:  # [-10:] means "start from 10 from the end", giving us the last 10
    print(record)

# Dedup by latest-filed value per frame. We keep every framed record (quarterly
# AND annual), not just quarterly ones, because the annual ("CY####") figure is
# needed below to derive Q4, which the SEC never tags with its own frame.
by_frame = {}

for record in records:
    frame = record.get("frame")  # .get() returns None if "frame" doesn't exist, avoiding a KeyError
    if not frame:
        continue
    existing = by_frame.get(frame)
    if existing is None or record["filed"] > existing["filed"]:  # keep only the latest filed value per frame
        by_frame[frame] = record

# Reported quarters: SEC tags Q1-Q3 with their own "CY####Q#" frame directly
quarterly_eps = {}
for frame, record in by_frame.items():
    if "Q" in frame:
        quarterly_eps[frame] = {
            "quarter": frame,
            "eps": record["val"],
            "filed": record["filed"],
            "form": record.get("form"),
        }

# sort chronologically — "CY2024Q1" < "CY2024Q2" works because the string format is lexicographically ordered
sorted_quarters = sorted(quarterly_eps.values(), key=lambda x: x["quarter"])

print(f"\nFound {len(sorted_quarters)} quarterly EPS data points:\n")
for item in sorted_quarters:
    print(f"{item['quarter']:10s} EPS: {item['eps']:>7.2f}   (filed {item['filed']}, {item['form']})")

# quarter-over-quarter change — handle edge cases that produce misleading percentages
print("\nQuarter-over-quarter change:\n")
for i in range(1, len(sorted_quarters)):
    prev = sorted_quarters[i - 1]
    curr = sorted_quarters[i]
    prev_val = prev["eps"]
    curr_val = curr["eps"]

    if prev_val == 0:
        change_str = "N/A (prior quarter EPS was 0)"
    elif (prev_val < 0) != (curr_val < 0):  # True when signs differ (one positive, one negative)
        change_str = f"N/A (sign flip: {prev_val} -> {curr_val}, % change is misleading)"
    else:
        change = ((curr_val - prev_val) / abs(prev_val)) * 100
        change_str = f"{change:+.1f}%"

    print(f"{prev['quarter']} -> {curr['quarter']}: {prev_val:>6.2f} -> {curr_val:>6.2f}   {change_str}")

# export to CSV
with open("rwt_quarterly_eps.csv", "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=["quarter", "eps", "filed", "form"])
    writer.writeheader()
    writer.writerows(sorted_quarters)

print("\nExported to rwt_quarterly_eps.csv")

# Derive missing Q4 values as Annual - (Q1 + Q2 + Q3), for any year where the
# annual figure and all three reported quarters are available.
reported_eps = {frame: item["eps"] for frame, item in quarterly_eps.items()}
years_present = set(int(f[2:6]) for f in reported_eps)
derived_q4 = {}

for year in years_present:
    annual_frame = f"CY{year}"
    q1 = reported_eps.get(f"CY{year}Q1")
    q2 = reported_eps.get(f"CY{year}Q2")
    q3 = reported_eps.get(f"CY{year}Q3")
    q4_frame = f"CY{year}Q4"

    if q4_frame in reported_eps:
        continue  # already have it explicitly, no need to derive

    annual_record = by_frame.get(annual_frame)
    if annual_record and q1 is not None and q2 is not None and q3 is not None:
        derived_q4[q4_frame] = round(annual_record["val"] - q1 - q2 - q3, 2)

# Merge reported + derived, tag the source so you always know which is which
all_quarters = {}
for frame, item in quarterly_eps.items():
    all_quarters[frame] = {"quarter": frame, "eps": item["eps"], "source": "reported"}
for frame, val in derived_q4.items():
    all_quarters[frame] = {"quarter": frame, "eps": val, "source": "derived (Annual - Q1 - Q2 - Q3)"}

sorted_all_quarters = sorted(all_quarters.values(), key=lambda x: x["quarter"])

print(f"\nFound {len(sorted_all_quarters)} quarterly EPS data points including derived Q4 "
      f"({len(quarterly_eps)} reported, {len(derived_q4)} derived):\n")
for item in sorted_all_quarters:
    flag = "  <- derived" if item["source"].startswith("derived") else ""
    print(f"{item['quarter']:10s} EPS: {item['eps']:>7.2f}{flag}")

with open("rwt_quarterly_eps_complete.csv", "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=["quarter", "eps", "source"])
    writer.writeheader()
    writer.writerows(sorted_all_quarters)

print("\nExported to rwt_quarterly_eps_complete.csv")

# ---------------------------------------------------------------------------
# Book Value Per Share (BVPS)
# ---------------------------------------------------------------------------
# Unlike EPS (a duration measure only tagged for Q1-Q3), StockholdersEquity and
# CommonStockSharesOutstanding are balance-sheet ("instant") measures tagged at
# every quarter-end, including Q4 -- so no Q4-derivation step is needed here.
# Instant frames carry an "I" suffix, e.g. "CY2025Q4I", to distinguish them
# from EPS's duration frames like "CY2025Q4".
#
# BVPS is computed per *common* share: (StockholdersEquity - PreferredStockValue)
# / CommonStockSharesOutstanding. RWT carries preferred stock on its balance
# sheet, and preferred holders don't share in common book value, so it's
# subtracted out of the numerator.

equity_concept_name = "StockholdersEquity"
shares_concept_name = "CommonStockSharesOutstanding"
preferred_concept_name = "PreferredStockValue"

for concept_name in (equity_concept_name, shares_concept_name):
    if concept_name not in us_gaap_facts:
        raise SystemExit(f"'{concept_name}' not found in us-gaap facts. Check available concepts and update the name.")


def latest_instant_by_frame(concept_name):
    """Same dedup approach as the EPS section above: keep only the most
    recently filed value per frame. Restricted to instant ('I'-suffixed)
    frames since balance-sheet concepts are point-in-time, not a range."""
    concept = us_gaap_facts[concept_name]
    unit_name = list(concept["units"].keys())[0]
    records = concept["units"][unit_name]

    by_frame = {}
    for record in records:
        frame = record.get("frame")
        if not frame or not frame.endswith("I"):
            continue
        existing = by_frame.get(frame)
        if existing is None or record["filed"] > existing["filed"]:
            by_frame[frame] = record
    return by_frame


equity_by_frame = latest_instant_by_frame(equity_concept_name)
shares_by_frame = latest_instant_by_frame(shares_concept_name)

# Preferred stock is optional -- not every company has any outstanding
preferred_by_frame = latest_instant_by_frame(preferred_concept_name) if preferred_concept_name in us_gaap_facts else {}

# Only compute BVPS for quarters where we have both equity and shares data
common_frames = sorted(set(equity_by_frame) & set(shares_by_frame))

print(f"\nFound {len(common_frames)} quarterly Book Value Per Share data points:\n")

bvps_rows = []
for frame in common_frames:
    equity = equity_by_frame[frame]["val"]
    shares = shares_by_frame[frame]["val"]
    preferred = preferred_by_frame.get(frame, {}).get("val", 0)  # 0 if no preferred stock that quarter

    common_equity = equity - preferred
    bvps = common_equity / shares

    quarter = frame[:-1]  # strip the trailing "I" so labels match the EPS "CY2025Q4" style

    bvps_rows.append({
        "quarter": quarter,
        "book_value_per_share": round(bvps, 2),
        "stockholders_equity": equity,
        "preferred_stock_value": preferred,
        "shares_outstanding": shares,
        "filed": equity_by_frame[frame]["filed"],
        "form": equity_by_frame[frame].get("form"),
    })
    print(f"{quarter:10s} BVPS: {bvps:>7.2f}   (equity {equity:,}, preferred {preferred:,}, shares {shares:,})")

with open("rwt_quarterly_bvps.csv", "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=[
        "quarter", "book_value_per_share", "stockholders_equity",
        "preferred_stock_value", "shares_outstanding", "filed", "form",
    ])
    writer.writeheader()
    writer.writerows(bvps_rows)

print("\nExported to rwt_quarterly_bvps.csv")

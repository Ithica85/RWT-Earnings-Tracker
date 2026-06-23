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

print("\nFirst 5 EPS Records:")

for record in eps["units"][unit_name][:5]:  # loop through only the first 5 entries in the list
    print(record)

records = eps["units"][unit_name]  # store the full list of EPS records in a variable

print("\nMost Recent 10 Records:")

for record in records[-10:]:  # [-10:] means "start from 10 from the end", giving us the last 10
    print(record)

quarterly_eps = {}  # use a dict keyed by frame to deduplicate (same quarter can appear in multiple filings)

for record in records:
    frame = record.get("frame")  # .get() returns None if "frame" doesn't exist, avoiding a KeyError
    if frame and "Q" in frame:
        existing = quarterly_eps.get(frame)
        if existing is None or record["filed"] > existing["filed"]:  # keep only the latest filed value per quarter
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

"""
Pure computation over the SEC CompanyFacts API.

These functions were extracted from get_company_facts.py, which had grown into
a script that computed, printed and exported all at once - fine for one
company, unusable as a library. Nothing here prints or writes files; callers
decide what to do with the results.

Behaviour is deliberately identical to the original, down to the tie-breaking
rule and the rounding, because tests/fixtures/ holds twenty CSVs produced by
the original code and the refactor is only correct if it reproduces them
byte for byte.

Two shapes of XBRL fact matter, and they need different handling:

    duration  covers a span (a quarter, a year) - earnings, dividends,
              expenses. The SEC often stops tagging a standalone Q4 frame, so
              Q4 has to be derived as Annual - Q1 - Q2 - Q3.

    instant   a point in time - anything from the balance sheet. Tagged at
              every quarter-end including Q4, so no derivation is needed.
              Frames carry a trailing "I" (CY2026Q2I).
"""


def concept_records(us_gaap_facts, concept_name, successor_concepts=()):
    """All reported records for a concept, pooling any successor concepts.

    Filers sometimes retag the same measure under a new concept, leaving the
    original frozen at the changeover date - Redwood's InterestExpense stops
    at CY2024Q2 and InterestExpenseOperating carries on from CY2023Q2. Pooling
    the records lets the series continue across the rename.

    Only pool concepts you have checked agree on overlapping frames. If they
    disagree they are measuring different things, and splicing them invents a
    step in the data that never happened.
    """
    if concept_name not in us_gaap_facts:
        raise KeyError(f"{concept_name!r} not found in us-gaap facts")

    concept = us_gaap_facts[concept_name]
    # Pick the unit type off the data rather than hardcoding "USD" or
    # "USD/shares", so the same code serves per-share and dollar measures.
    unit_name = list(concept["units"].keys())[0]
    records = list(concept["units"][unit_name])

    for successor in successor_concepts:
        if successor not in us_gaap_facts:
            raise KeyError(f"Successor concept {successor!r} not found in us-gaap facts")
        records += us_gaap_facts[successor]["units"][unit_name]

    return records, unit_name


def dedupe_by_frame(records, instants_only=False):
    """Keep the most recently filed value for each frame.

    The SEC stores every version of a figure ever reported, so restatements
    and corrections sit alongside the originals. Latest filing wins.

    Annual frames are kept alongside quarterly ones because the annual figure
    is what Q4 gets derived from. Records with no frame at all are skipped -
    they are company-specific periods the SEC could not map to a calendar
    quarter, and mixing them in would double-count.
    """
    by_frame = {}
    for record in records:
        frame = record.get("frame")
        if not frame:
            continue
        if instants_only and not frame.endswith("I"):
            continue
        existing = by_frame.get(frame)
        if existing is None or record["filed"] > existing["filed"]:
            by_frame[frame] = record
    return by_frame


def quarterly_from_frames(by_frame, value_key):
    """Pull just the quarterly frames out, as export-ready rows."""
    quarterly = {}
    for frame, record in by_frame.items():
        if "Q" in frame:
            quarterly[frame] = {
                "quarter": frame,
                value_key: record["val"],
                "filed": record["filed"],
                "form": record.get("form"),
            }
    return quarterly


def derive_q4(by_frame, quarterly, value_key):
    """Back Q4 out of the annual figure where the SEC never tagged one.

    Returns {frame: value} for every year with an annual figure and all three
    of Q1-Q3 present, and no Q4 already reported.
    """
    reported = {frame: item[value_key] for frame, item in quarterly.items()}
    derived = {}

    for year in {int(frame[2:6]) for frame in reported}:
        q4_frame = f"CY{year}Q4"
        if q4_frame in reported:
            continue  # already reported explicitly

        annual = by_frame.get(f"CY{year}")
        q1 = reported.get(f"CY{year}Q1")
        q2 = reported.get(f"CY{year}Q2")
        q3 = reported.get(f"CY{year}Q3")

        if annual and q1 is not None and q2 is not None and q3 is not None:
            derived[q4_frame] = round(annual["val"] - q1 - q2 - q3, 2)

    return derived


def merge_reported_and_derived(quarterly, derived, value_key):
    """Combine both into one series, tagging where each value came from.

    A derived figure is an inference, not a disclosure. Tagging the source is
    what stops the two being confused downstream.
    """
    merged = {}
    for frame, item in quarterly.items():
        merged[frame] = {"quarter": frame, value_key: item[value_key], "source": "reported"}
    for frame, value in derived.items():
        merged[frame] = {
            "quarter": frame,
            value_key: value,
            "source": "derived (Annual - Q1 - Q2 - Q3)",
        }
    return merged


def latest_instant_by_frame(us_gaap_facts, concept_name):
    """Balance-sheet concepts, deduped, restricted to instant frames."""
    records, _ = concept_records(us_gaap_facts, concept_name)
    return dedupe_by_frame(records, instants_only=True)

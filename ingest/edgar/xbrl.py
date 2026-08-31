"""
Parsing XBRL instance documents.

The CompanyFacts API only serves consolidated, standard-taxonomy figures.
Anything dimensional (per segment) or filed under a company's own custom tags
is absent from it and exists only inside each filing's instance document -
which is why segment results and Redwood's PortfolioManagementCosts had to be
read from the raw XML.

A note on the vocabulary, because XBRL names things badly:

    context   who the number is about, over what period, sliced which ways.
              A context with no explicitMember is the company as a whole; one
              carrying a segment member is a slice of it. Mixing the two
              double-counts, so they are kept strictly apart here.

    duration  a span (start and end dates); instant is a single date.

Namespace URIs for us-gaap change every year (.../us-gaap/2025, /2026), so
nothing here matches on them - only on local names, which are stable.
"""

import re
from datetime import date

from lxml import etree

NS_XBRLI = "http://www.xbrl.org/2003/instance"
NS_XBRLDI = "http://xbrl.org/2006/xbrldi"

SEGMENT_AXIS = "StatementBusinessSegmentsAxis"
CONSOLIDATION_AXIS = "ConsolidationItemsAxis"


def parse(path):
    """Load an instance document."""
    return etree.parse(path).getroot()


def period_to_frame(start, end, instant):
    """Turn a context's dates into a calendar frame label.

    Durations become CY2026Q2 (one quarter) or CY2025 (a full year); instants
    become CY2026Q2I. Six- and nine-month year-to-date spans return None -
    they overlap the discrete quarters and would double-count if included.
    """
    if instant is not None:
        return f"CY{instant.year}Q{(instant.month - 1) // 3 + 1}I"

    span = (end - start).days
    if 80 <= span <= 100:
        return f"CY{end.year}Q{(end.month - 1) // 3 + 1}"
    if 350 <= span <= 380:
        return f"CY{end.year}"
    return None


def _period(ctx):
    """(start, end, instant) for a context, as dates."""
    def read(tag):
        element = ctx.find(f"{{{NS_XBRLI}}}period/{{{NS_XBRLI}}}{tag}")
        return date.fromisoformat(element.text.strip()) if element is not None else None

    return read("startDate"), read("endDate"), read("instant")


def _members(ctx):
    """{axis_local_name: member_local_name} for a context."""
    members = {}
    for member in ctx.iter(f"{{{NS_XBRLDI}}}explicitMember"):
        axis = member.get("dimension", "").split(":")[-1]
        members[axis] = (member.text or "").strip().split(":")[-1]
    return members


def segment_contexts(root, corporate_label="Corporate"):
    """context id -> (segment name, frame), for segment-sliced contexts only.

    Contexts carrying any dimension beyond the segment and consolidation axes
    are rejected. Those are sub-breakdowns - by range, by counterparty, by
    instrument - and adding them to a segment total would double-count.

    The corporate bucket is a special case: it has no segment member, and is
    identified by CorporateNonSegmentMember on the consolidation axis.
    """
    contexts = {}
    for ctx in root.iter(f"{{{NS_XBRLI}}}context"):
        members = _members(ctx)
        if not members:
            continue

        if SEGMENT_AXIS in members:
            segment = members[SEGMENT_AXIS].replace("Member", "").replace("Segment", "")
        elif members.get(CONSOLIDATION_AXIS) == "CorporateNonSegmentMember":
            segment = corporate_label
        else:
            continue

        if set(members) - {SEGMENT_AXIS, CONSOLIDATION_AXIS}:
            continue

        frame = period_to_frame(*_period(ctx))
        if frame:
            contexts[ctx.get("id")] = (segment, frame)

    return contexts


def consolidated_contexts(root):
    """context id -> (start, end) for undimensioned duration contexts.

    No explicitMember means the figure is about the whole company. Used where
    a total has to be rebuilt from component tags, as with operating expenses
    after the filings stopped tagging a total.
    """
    contexts = {}
    for ctx in root.iter(f"{{{NS_XBRLI}}}context"):
        if list(ctx.iter(f"{{{NS_XBRLDI}}}explicitMember")):
            continue
        start, end, _ = _period(ctx)
        if start is not None and end is not None:
            contexts[ctx.get("id")] = (start, end)
    return contexts


def facts_for_contexts(root, contexts, wanted):
    """Yield (context_id, local_name, value) for tagged numeric facts.

    `wanted` is a set of concept local names; `contexts` limits which slices
    count. Values that will not parse as numbers are skipped - XBRL carries
    plenty of text facts under the same shape.
    """
    for element in root.iter():
        context_ref = element.get("contextRef")
        if context_ref is None or context_ref not in contexts:
            continue

        name = etree.QName(element).localname
        if name not in wanted:
            continue

        text = (element.text or "").strip()
        if not text:
            continue
        try:
            value = float(text)
        except ValueError:
            continue

        # Some filers tag an expense positive and flip it for presentation.
        if element.get("sign") == "-":
            value = -value

        yield context_ref, name, value


def quarter_sort_key(frame):
    """Sort CY2026Q2 and CY2026Q2I chronologically; annual frames last."""
    match = re.match(r"CY(\d{4})Q(\d)", frame)
    if match:
        return (int(match.group(1)), int(match.group(2)))
    return (int(frame[2:6]), 9)

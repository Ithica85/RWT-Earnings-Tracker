/**
 * The plain-English health checks, and the company-condition band above them.
 *
 * Every colour on the page comes from a rule in this file, and every card
 * prints its own rule, so a reader can disagree with a threshold rather than
 * having to trust a black box.
 *
 * Two things this deliberately does not do:
 *
 * - It never tells a reader to stay at or leave a job. The condition band
 *   describes the company's finances; whether to leave depends on things no
 *   filing can see (the reader's team, role, pay, options). A verdict on a
 *   named employer is the layoff prediction CLAUDE.md rules out, reworded.
 * - It never colours a figure nobody has checked. On a generic-tier company
 *   the leverage card stays grey: the uncorrected reading of Redwood's
 *   leverage was wrong by about six times, so a green there would be worse
 *   than no card at all.
 */

import type { Company, Kpi, Point, Segments } from "./data";

export type Rag = "red" | "amber" | "green" | "grey";

export const RAG_WORD: Record<Rag, string> = {
  red: "Warning",
  amber: "Watch",
  green: "OK",
  grey: "Not checked",
};

export type Card = {
  key: string;
  question: string;
  status: Rag;
  /** One or two plain sentences answering the question, with the figures. */
  answer: string;
  /** What the answer means for someone who works there. */
  meaning: string;
  /** How the colour was decided, in words. */
  rule: string;
  /** The one piece of jargon the card cannot avoid, explained. */
  jargon?: { term: string; plain: string };
  /** Short phrase for the condition summary, e.g. "losing money". */
  short?: string;
  /** What to look for in the next filing. */
  watchFor?: string;
  asOf?: string;
};

export type Condition = {
  status: Rag;
  title: string;
  summary: string;
  assessed: number;
  total: number;
  watchFor: string[];
};

// ---------- formatting for readers who don't read filings ----------

const MONTHS = ["Jan–Mar", "Apr–Jun", "Jul–Sep", "Oct–Dec"];

/** "CY2026Q2" → "Apr–Jun 2026". */
export function quarterName(quarter: string): string {
  const year = quarter.slice(2, 6);
  const q = Number(quarter.slice(-1));
  return `${MONTHS[q - 1]} ${year}`;
}

/** Per-share amounts under a dollar read better as cents: "7¢", not "$0.07". */
function perShare(value: number): string {
  const abs = Math.abs(value);
  const sign = value < 0 ? "−" : "";
  return abs < 1 ? `${sign}${Math.round(abs * 100)}¢` : `${sign}$${abs.toFixed(2)}`;
}

export function dollars(value: number): string {
  const abs = Math.abs(value);
  const sign = value < 0 ? "−" : "";
  if (abs >= 1e9) return `${sign}$${(abs / 1e9).toFixed(2)}B`;
  return `${sign}$${(abs / 1e6).toFixed(1)}M`;
}

function pct(change: number): string {
  const rounded = Number(change.toFixed(1));
  if (rounded === 0) return "0%";
  return `${rounded > 0 ? "+" : "−"}${Math.abs(rounded).toFixed(1)}%`;
}

function list(items: string[]): string {
  if (items.length <= 1) return items.join("");
  return `${items.slice(0, -1).join(", ")} and ${items[items.length - 1]}`;
}

// ---------- series helpers ----------

/** The label `n` quarters before `quarter`: ("CY2026Q2", 4) → "CY2025Q2". */
function quarterBack(quarter: string, n: number): string {
  let year = Number(quarter.slice(2, 6));
  let q = Number(quarter.slice(-1)) - n;
  while (q < 1) {
    q += 4;
    year -= 1;
  }
  return `CY${year}Q${q}`;
}

/**
 * Value at a quarter label, not a position. Series can have gaps (a dropped
 * sign-error quarter, a disclosure change), so "four points back" is not
 * reliably "a year ago".
 */
function at(series: Point[], quarter: string): number | undefined {
  return series.find((p) => p.quarter === quarter)?.value;
}

function usable(kpi: Kpi | undefined): kpi is Kpi & { series: Point[] } {
  return Boolean(kpi?.available && kpi.series && kpi.series.length >= 2);
}

function notChecked(
  key: string,
  question: string,
  answer: string,
  meaning: string,
  rule: string,
): Card {
  return { key, question, status: "grey", answer, meaning, rule };
}

// ---------- the five checks ----------

function profitCard(company: Company): Card {
  const key = "profit";
  const question = "Is it making money?";
  const rule =
    "Warning if it lost money over the last four quarters added together. Watch if the year was profitable but the latest quarter, or two or more of the four, were losses. OK otherwise.";
  const eps = company.kpis.eps;
  if (!usable(eps)) {
    return notChecked(key, question, "This company's profit per share isn't in the data.", "", rule);
  }

  const latest = eps.series[eps.series.length - 1];
  const year = [3, 2, 1, 0].map((n) => quarterBack(latest.quarter, n));
  const values = year.map((q) => at(eps.series, q));
  if (values.some((v) => v === undefined)) {
    return notChecked(key, question, "There aren't four straight quarters of results to judge a year by.", "", rule);
  }

  const four = values as number[];
  const total = four.reduce((a, b) => a + b, 0);
  const losses = four.filter((v) => v < 0).length;
  const previous = four[2];

  const status: Rag =
    total < 0 ? "red" : latest.value < 0 || losses >= 2 ? "amber" : "green";

  const yearText =
    total < 0
      ? `Not over the last year. From ${quarterName(year[0])} to ${quarterName(year[3])} it lost ${perShare(-total)} a share in total, and lost money in ${losses} of those 4 quarters.`
      : `Yes, over the last year. From ${quarterName(year[0])} to ${quarterName(year[3])} it made ${perShare(total)} a share in total${losses ? `, though ${losses} of those 4 quarters were losses` : ""}.`;

  let latestText = "";
  if (latest.value < 0 && previous < 0) {
    latestText =
      Math.abs(latest.value) < Math.abs(previous)
        ? ` The latest quarter was a smaller loss (${perShare(latest.value)}) than the one before (${perShare(previous)}).`
        : ` The latest quarter was a bigger loss (${perShare(latest.value)}) than the one before (${perShare(previous)}).`;
  } else if (latest.value < 0) {
    latestText = ` The latest quarter was a loss of ${perShare(latest.value)} a share.`;
  }

  return {
    key,
    question,
    status,
    answer: yearText + latestText,
    meaning:
      status === "green"
        ? "A profitable company has room to keep its people and hire more."
        : "A company that keeps losing money eventually has to cut costs, and staff are usually its biggest cost. One bad year isn't a crisis, but this is the most important trend to watch.",
    rule,
    jargon: {
      term: "Earnings per share",
      plain: "The company's profit or loss divided by its number of shares. Negative means a loss.",
    },
    short: status === "green" ? "making money" : "losing money",
    watchFor: "a return to profit",
    asOf: latest.quarter,
  };
}

function cushionCard(company: Company): Card {
  const key = "cushion";
  const question = "Is its safety cushion shrinking?";
  const rule =
    "Compares book value per share with a year earlier. Warning if it fell more than 5%. Watch if it fell at all. OK if flat or rising.";
  const bvps = company.kpis.book_value_per_share;
  if (!usable(bvps)) {
    return notChecked(
      key,
      question,
      "Not worked out for this company yet. Book value per share has to be calculated from the filings, and nobody has done it here.",
      "",
      rule,
    );
  }

  const latest = bvps.series[bvps.series.length - 1];
  const yearAgo = at(bvps.series, quarterBack(latest.quarter, 4));
  const twoYearsAgo = at(bvps.series, quarterBack(latest.quarter, 8));
  if (yearAgo === undefined) {
    return notChecked(key, question, "There's no figure from a year earlier to compare with.", "", rule);
  }

  const change = ((latest.value - yearAgo) / yearAgo) * 100;
  const status: Rag = change <= -5 ? "red" : change < 0 ? "amber" : "green";
  const verb = change < 0 ? "fell" : "rose";

  return {
    key,
    question,
    status,
    answer:
      `${change < 0 ? "Yes" : "No"}. Book value per share ${verb} from $${yearAgo.toFixed(2)} to $${latest.value.toFixed(2)} over the last year (${pct(change)})` +
      (twoYearsAgo !== undefined ? `. Two years ago it was $${twoYearsAgo.toFixed(2)}.` : "."),
    meaning:
      "This is the company's safety cushion: roughly what would be left for its owners if it sold everything and paid every debt. A shrinking cushion means less room to absorb bad quarters.",
    rule,
    jargon: {
      term: "Book value per share",
      plain: "What the company owns minus what it owes, divided by the number of shares.",
    },
    short: change < 0 ? "a shrinking cushion" : "a growing cushion",
    watchFor: "book value per share to stop falling",
    asOf: latest.quarter,
  };
}

function borrowingCard(company: Company): Card {
  const key = "borrowing";
  const question = "Is it borrowing too much?";
  const rule =
    "Counts only debt the company itself has to repay. Warning if that rose more than 25% against its cushion in a year. Watch if it rose more than 10%. OK otherwise. There's no checked peer comparison yet, so this judges the direction, not the level.";
  const recourse = company.kpis.recourse_leverage;

  if (company.tier !== "curated" || !usable(recourse)) {
    return notChecked(
      key,
      question,
      "Not checked. The only borrowing figure for this company is the raw one, which counts debt it may not be liable for. On the one company we have checked, that raw figure was about six times too high, so giving it a colour would mislead.",
      "",
      rule,
    );
  }

  const latest = recourse.series[recourse.series.length - 1];
  const first = recourse.series[0];
  const yearAgo = at(recourse.series, quarterBack(latest.quarter, 4));
  if (yearAgo === undefined) {
    return notChecked(key, question, "There's no figure from a year earlier to compare with.", "", rule);
  }

  const change = ((latest.value - yearAgo) / yearAgo) * 100;
  const status: Rag = change > 25 ? "red" : change > 10 ? "amber" : "green";
  const gross = company.kpis.debt_to_equity;

  const trend =
    change > 10
      ? "Borrowing has risen fast compared with its cushion."
      : change < -10
        ? "Borrowing has fallen compared with its cushion."
        : "Borrowing has been roughly steady compared with its cushion.";

  return {
    key,
    question,
    status,
    answer: `${trend} For every $1 of its own money, it owes $${latest.value.toFixed(2)} that it is on the hook for, ${latest.value >= yearAgo ? "up" : "down"} from $${yearAgo.toFixed(2)} a year ago (${pct(change)})${first.quarter !== quarterBack(latest.quarter, 4) ? ` and $${first.value.toFixed(2)} in ${quarterName(first.quarter)}` : ""}.`,
    meaning:
      "More borrowing per dollar of cushion means less room for error if markets turn against it. Part of this rise comes from the cushion shrinking, not only from borrowing more." +
      (gross?.latest_value !== undefined
        ? ` You may see a much scarier figure (${gross.latest_value.toFixed(2)}×) quoted elsewhere. That one counts debt held in separate vehicles whose lenders can't come after the company, so it overstates the risk.`
        : ""),
    rule,
    jargon: {
      term: "Recourse leverage",
      plain: "Debt the company itself must repay, divided by its equity (its own money).",
    },
    short: change > 10 ? "borrowing more against that cushion" : "steady borrowing",
    watchFor: "borrowing to level off",
    asOf: latest.quarter,
  };
}

function payoutCard(company: Company): Card {
  const key = "payout";
  const question = "Is it still paying its shareholders?";
  const rule =
    "Warning if the dividend was cut from the quarter before, or from a year earlier. OK if it was held or raised.";
  const dps = company.kpis.dividends_per_share;
  if (!usable(dps)) {
    return notChecked(key, question, "This company's dividend isn't in the data yet.", "", rule);
  }

  const latest = dps.series[dps.series.length - 1];
  const previous = dps.series[dps.series.length - 2].value;
  const yearAgo = at(dps.series, quarterBack(latest.quarter, 4));
  const cut = latest.value < previous || (yearAgo !== undefined && latest.value < yearAgo);
  const status: Rag = cut ? "red" : "green";

  const comparison =
    yearAgo === undefined
      ? ""
      : latest.value === yearAgo
        ? ", the same as a year earlier"
        : latest.value > yearAgo
          ? `, up from ${perShare(yearAgo)} a year earlier`
          : `, down from ${perShare(yearAgo)} a year earlier`;

  return {
    key,
    question,
    status,
    answer: `${cut ? "Less than before" : "Yes"}. It paid ${perShare(latest.value)} a share in ${quarterName(latest.quarter)}${comparison}.`,
    meaning: cut
      ? "Companies hate cutting dividends, because it tells everyone money is tight. A cut is one of the clearest warnings a company can give."
      : "Companies hate cutting dividends, because it tells everyone money is tight. Keeping it steady suggests management thinks it can afford to. A cut would be a serious warning.",
    rule,
    jargon: {
      term: "Dividend",
      plain: "Cash the company pays its shareholders each quarter, out of its earnings.",
    },
    short: cut ? "a cut dividend" : "a steady dividend",
    watchFor: "the dividend being held",
    asOf: latest.quarter,
  };
}

function restructuringCard(company: Company): Card {
  const filed = company.signals.filter((s) => s.item === "2.05");
  const status: Rag = filed.length > 0 ? "red" : "green";
  return {
    key: "restructuring",
    question: "Has it announced a restructuring?",
    status,
    answer:
      filed.length > 0
        ? `Yes. It filed ${filed.length === 1 ? "a formal restructuring notice" : `${filed.length} formal restructuring notices`}, most recently on ${filed[0].date}.`
        : "No. It hasn't filed a formal restructuring notice since 2024.",
    meaning:
      "A company has to file this notice when it commits to a significant restructuring, such as closing a business or a major cost-cutting plan. Its absence doesn't rule out smaller, targeted job cuts, which don't have to be announced.",
    rule: "Warning if the company has filed one since 2024 (SEC form 8-K, item 2.05). OK if not.",
    short: filed.length > 0 ? "a restructuring announced" : "no restructuring announced",
    watchFor: "a restructuring notice",
  };
}

export function healthCards(company: Company): Card[] {
  return [
    profitCard(company),
    cushionCard(company),
    borrowingCard(company),
    payoutCard(company),
    restructuringCard(company),
  ];
}

/**
 * One band summarising the cards, describing the company, not the reader's
 * job.
 *
 * "In trouble" is reserved for things a company only does when money is
 * tight: cutting its dividend or filing a restructuring. Trends alone (losses,
 * a shrinking cushion, rising borrowing) can only reach "under pressure"
 * unless every check is red. That keeps the worst band tied to the company's
 * own actions rather than to thresholds someone picked.
 */
export function condition(cards: Card[]): Condition {
  const assessed = cards.filter((c) => c.status !== "grey");
  const reds = assessed.filter((c) => c.status === "red");
  const ambers = assessed.filter((c) => c.status === "amber");
  const greens = assessed.filter((c) => c.status === "green");
  const total = cards.length;

  const watchFor = [...reds, ...ambers]
    .map((c) => c.watchFor)
    .filter((w): w is string => Boolean(w));

  if (assessed.length < 4) {
    return {
      status: "grey",
      title: "Not enough checked to say",
      summary: `Only ${assessed.length} of the ${total} checks below could be run, because nobody has read this company's filings yet. Treat what's here as a partial view.`,
      assessed: assessed.length,
      total,
      watchFor,
    };
  }

  const distress = cards.filter(
    (c) => (c.key === "payout" || c.key === "restructuring") && c.status === "red",
  );
  const against = [...reds, ...ambers].map((c) => c.short).filter(Boolean) as string[];
  const inFavour = greens.map((c) => c.short).filter(Boolean) as string[];
  const summary = [
    against.length ? `Against it: ${list(against)}.` : "",
    inFavour.length ? `In its favour: ${list(inFavour)}.` : "",
  ]
    .filter(Boolean)
    .join(" ");

  if (distress.length > 0 || reds.length === assessed.length) {
    return {
      status: "red",
      title: "In trouble",
      summary:
        (distress.length
          ? `The company has done something companies usually only do when money is tight: ${list(distress.map((c) => c.short as string))}. `
          : "") + summary,
      assessed: assessed.length,
      total,
      watchFor,
    };
  }

  if (reds.length > 0 || ambers.length >= 2) {
    return {
      status: "amber",
      title: "Under pressure — worth watching closely",
      summary,
      assessed: assessed.length,
      total,
      watchFor,
    };
  }

  return {
    status: "green",
    title: "Steady",
    summary,
    assessed: assessed.length,
    total,
    watchFor,
  };
}

// ---------- segments ----------

export type SegmentRow = {
  key: string;
  label: string;
  plain?: string;
  rated: boolean;
  status: Rag;
  verdict: string;
  now: number;
  before: number;
};

export type SegmentView = {
  periodNow: string;
  periodBefore: string;
  rows: SegmentRow[];
  totalNow: number;
  totalBefore: number;
};

/**
 * Compare each part of the business this year with the same months last year.
 *
 * Uses the quarters of the latest year that also exist a year earlier for
 * every segment, so the comparison is always like-for-like. A quarter filed
 * under an older segment structure is absent from the data on purpose, and
 * simply drops out of the comparison rather than being filled in.
 */
export function segmentView(segments: Segments | null | undefined): SegmentView | null {
  if (!segments || segments.segments.length === 0) return null;

  const quarters = new Set(segments.segments.flatMap((s) => s.series.map((p) => p.quarter)));
  const latest = [...quarters].sort().pop();
  if (!latest) return null;
  const year = latest.slice(2, 6);

  const paired = [1, 2, 3, 4]
    .map((q) => `CY${year}Q${q}`)
    .filter((q) => q <= latest)
    .filter((q) =>
      segments.segments.every(
        (s) => at(s.series, q) !== undefined && at(s.series, quarterBack(q, 4)) !== undefined,
      ),
    );
  if (paired.length === 0) return null;

  const span = (qs: string[]) => {
    const first = quarterName(qs[0]).split(" ")[0].split("–")[0];
    const last = quarterName(qs[qs.length - 1]);
    return `${first}–${last.split("–")[1]}`;
  };
  const before = paired.map((q) => quarterBack(q, 4));

  const rows = segments.segments.map((s) => {
    const now = paired.reduce((sum, q) => sum + (at(s.series, q) ?? 0), 0);
    const prior = before.reduce((sum, q) => sum + (at(s.series, q) ?? 0), 0);

    let status: Rag = "grey";
    let verdict = s.key === "Corporate" ? "A cost, not a business" : "Being wound down on purpose";
    if (s.rated) {
      if (now > 0 && now >= prior) {
        status = "green";
        verdict = "Making money, more than a year ago";
      } else if (now > 0) {
        status = "amber";
        verdict = "Making money, but less than a year ago";
      } else if (now > prior) {
        status = "amber";
        verdict = "Losing money, but less than a year ago";
      } else {
        status = "red";
        verdict = prior > 0 ? "Was making money, now losing it" : "Losing money, and more than a year ago";
      }
    }

    return { key: s.key, label: s.label, plain: s.plain, rated: s.rated, status, verdict, now, before: prior };
  });

  return {
    periodNow: span(paired),
    periodBefore: span(before),
    rows,
    totalNow: rows.reduce((sum, r) => sum + r.now, 0),
    totalBefore: rows.reduce((sum, r) => sum + r.before, 0),
  };
}


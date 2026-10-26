import Link from "next/link";
import { LeverageChart, Sparkline } from "@/lib/charts";
import {
  formatValue,
  getCompany,
  getTickers,
  KPI_PLAIN,
  quarterChange,
  type Company,
  type Kpi,
} from "@/lib/data";
import {
  condition,
  dollars,
  healthCards,
  quarterName,
  RAG_WORD,
  segmentView,
  type Card,
  type Rag,
} from "@/lib/health";

export function generateStaticParams() {
  return getTickers().map((ticker) => ({ ticker }));
}

/**
 * Quarter-on-quarter change, or an em dash where a percentage would mislead.
 *
 * A flat quarter must read "0.0%", not "−0.0%" — signing zero implies a
 * direction that did not happen. Rounding is done before the comparison so a
 * change of 0.04% shows as 0.0% with no sign rather than "+0.0%".
 */
function formatChange(change: number | null): string {
  if (change === null) return "—";
  const rounded = Number(change.toFixed(1));
  if (rounded === 0) return "0.0%";
  return `${rounded > 0 ? "+" : "−"}${Math.abs(rounded).toFixed(1)}%`;
}

/**
 * The word that makes a percentage on a negative base readable.
 *
 * A loss narrowing from −$0.07 to −$0.03 is a +57.1% change, which sitting in
 * grey beside a red negative figure looks like it contradicts it. Both are
 * correct; only the direction needs saying.
 */
function changeQualifier(kpi: Kpi): string | null {
  const series = kpi.series;
  if (!series || series.length < 2) return null;
  const previous = series[series.length - 2].value;
  const current = series[series.length - 1].value;
  if (previous >= 0 || current >= 0) return null;
  return Math.abs(current) < Math.abs(previous) ? "narrower loss" : "wider loss";
}

/** True when a series sits on both sides of zero, so its chart needs a baseline. */
function crossesZero(kpi: Kpi): boolean {
  const series = kpi.series ?? [];
  return series.some((p) => p.value < 0) && series.some((p) => p.value > 0);
}

/**
 * KPI order, with each companion moved to sit directly beneath the figure it
 * corrects. Recourse leverage means nothing on its own — it is only legible
 * next to the gross number it is correcting.
 */
function orderedKpis(company: Company): [string, Kpi][] {
  const principalOf = new Map<string, string>();
  for (const caveat of company.caveats) {
    if (caveat.companion) principalOf.set(caveat.companion, caveat.kpi);
  }

  const companions = new Map<string, [string, Kpi]>();
  const rest: [string, Kpi][] = [];
  for (const entry of Object.entries(company.kpis)) {
    const principal = principalOf.get(entry[0]);
    if (principal && company.kpis[principal]) companions.set(principal, entry);
    else rest.push(entry);
  }

  const ordered: [string, Kpi][] = [];
  for (const entry of rest) {
    ordered.push(entry);
    const companion = companions.get(entry[0]);
    if (companion) ordered.push(companion);
  }
  return ordered;
}

function Pill({ status, word }: { status: Rag; word?: string }) {
  return <span className={`pill rag-${status}`}>{word ?? RAG_WORD[status]}</span>;
}

function CheckCard({ card }: { card: Card }) {
  return (
    <article className={`check rag-${card.status}`}>
      <div className="top">
        <h3>{card.question}</h3>
        <Pill status={card.status} />
      </div>
      <p className="answer">{card.answer}</p>
      {card.meaning && (
        <p className="meaning">
          <strong>What this means: </strong>
          {card.meaning}
        </p>
      )}
      {card.jargon && (
        <p className="jargon">
          <strong>{card.jargon.term}: </strong>
          {card.jargon.plain}
        </p>
      )}
      <p className="rule">
        <span className="k">How we decide · </span>
        {card.rule}
        {card.asOf && <span className="asof"> · as of {quarterName(card.asOf)}</span>}
      </p>
    </article>
  );
}

function KpiRow({
  kpiKey,
  kpi,
  isCompanion,
}: {
  kpiKey: string;
  kpi: Kpi;
  isCompanion: boolean;
}) {
  if (!kpi.available) {
    return (
      <tr>
        <td className="kpi-name">{kpi.label}</td>
        <td className="num muted" colSpan={4}>
          not reported by this filer
        </td>
      </tr>
    );
  }

  const negative = (kpi.latest_value ?? 0) < 0;
  const qualifier = changeQualifier(kpi);
  const flagged = (kpi.caveats?.length ?? 0) > 0;

  return (
    <tr>
      <td className="kpi-name">
        {kpi.label}
        {flagged && <span className="row-flag">see note</span>}
        {isCompanion && <span className="row-flag corrected">corrected</span>}
        {KPI_PLAIN[kpiKey] && <span className="kpi-plain">{KPI_PLAIN[kpiKey]}</span>}
      </td>
      <td className="trend">
        {kpi.series && (
          <Sparkline
            series={kpi.series}
            stroke={isCompanion ? "var(--green)" : negative ? "var(--red)" : "var(--ink-2)"}
            zero={crossesZero(kpi)}
          />
        )}
      </td>
      <td className={`num now ${negative ? "neg" : ""}`}>
        {formatValue(kpi.latest_value, kpi.unit)}
      </td>
      <td className="num muted">
        {formatChange(quarterChange(kpi))}
        {qualifier && <span className="qual">{qualifier}</span>}
      </td>
      <td className="num muted">
        {kpi.quarters}q from {kpi.first}
      </td>
    </tr>
  );
}

export default async function CompanyPage({
  params,
}: {
  params: Promise<{ ticker: string }>;
}) {
  const { ticker } = await params;
  const company = getCompany(ticker);

  const kpis = orderedKpis(company);
  const companionKeys = new Set(
    company.caveats.map((c) => c.companion).filter((c): c is string => Boolean(c)),
  );

  const restructuring = company.signals.filter((s) => s.item === "2.05");

  const leverage = company.kpis.debt_to_equity;
  const recourse = company.kpis.recourse_leverage;

  const cards = healthCards(company);
  const overall = condition(cards);
  const asOf = company.kpis.total_assets?.latest;
  const segments = segmentView(company.segments);

  /*
   * Every caveat is rendered here. attachCaveats() binds them to their KPI as
   * the data loads so one cannot be silently dropped; this band is the single
   * place they surface, above the figures they correct rather than beneath.
   */
  const corrections = company.caveats
    .map((caveat) => ({
      caveat,
      principal: company.kpis[caveat.kpi],
      companion: caveat.companion ? company.kpis[caveat.companion] : undefined,
    }))
    .filter((c) => c.principal);

  return (
    <main className="wrap">
      <header className="masthead">
        <div className="eyebrow">
          <Link href="/">← All companies</Link> · CIK {company.cik} ·{" "}
          {company.kpis.total_assets?.latest ?? ""}
        </div>
        <h1>{company.name}</h1>
        <p className="standfirst">
          Is this company in good financial shape? Five plain-English checks, read from
          its own filings with the SEC, the US regulator every listed company reports to.
        </p>
      </header>

      <section className={`condition rag-${overall.status}`} aria-label="Overall condition">
        <span className="label">
          Overall condition{asOf ? ` · latest results ${quarterName(asOf)}` : ""}
        </span>
        <h2 className="title">{overall.title}</h2>
        <p className="summary">{overall.summary}</p>
        {overall.status !== "grey" && overall.watchFor.length > 0 && (
          <p className="watch">
            <strong>What would improve this:</strong> in the next quarterly results, look
            for {overall.watchFor.slice(0, -1).join(", ")}
            {overall.watchFor.length > 1 ? " and " : ""}
            {overall.watchFor[overall.watchFor.length - 1]}.
            {overall.status === "amber" &&
              " A dividend cut or a restructuring notice would move this to \u201cIn trouble\u201d."}
          </p>
        )}
        <p className="fine">
          This describes the company&rsquo;s finances, not whether you should stay in a
          job there. That depends on things no filing can show &mdash; see{" "}
          <a href="#yourself">deciding for yourself</a>.
        </p>
      </section>

      <div className={`tier-banner ${company.tier === "generic" ? "generic" : ""}`}>
        <span className="lede">{company.tier === "curated" ? "Curated" : "Uncorrected"}</span>
        <p className="body">
          {company.tier === "curated"
            ? `Someone read the filings. Concept choices are checked against the source, series crossing a renaming or a restatement are verified on overlapping periods, and ${corrections.length === 1 ? "one figure below would mislead" : `${corrections.length} figures below would mislead`} without the correction attached.`
            : "The obvious concepts, pulled automatically, with nobody having read the filings. A starting point, not an answer. On the one company that has been curated, the automatic reading of leverage was wrong by roughly six times."}
        </p>
      </div>


      <section>
        <div className="sec-head">
          <h2>The five checks</h2>
          <span className="note">
            {overall.assessed} of {overall.total} checked
          </span>
        </div>
        <p className="how-to">
          Each check asks one question and answers it from the filings. The colour is
          decided by a fixed rule, printed at the bottom of each card: green is{" "}
          <strong>OK</strong>, amber is <strong>Watch</strong>, red is{" "}
          <strong>Warning</strong>, and grey means nobody has checked the figure well
          enough to colour it.
        </p>
        <div className="check-grid">
          {cards.map((card) => (
            <CheckCard key={card.key} card={card} />
          ))}
        </div>
      </section>

      {segments && (
        <section>
          <div className="sec-head">
            <h2>How each part of the business is doing</h2>
            <span className="note">
              {segments.periodNow} vs {segments.periodBefore}
            </span>
          </div>
          <p className="how-to">
            The company reports its profit or loss for each part of the business
            separately. If you work in one of them, this tells you more about your corner
            than the company total does. Each figure is the profit or loss for{" "}
            {segments.periodNow}, compared with the same months a year earlier.
          </p>
          <div className="seg-list">
            {segments.rows.map((row) => (
              <div className={`seg rag-${row.status}`} key={row.key}>
                <span className="name">
                  {row.label}
                  {row.plain && <span className="plain">{row.plain}</span>}
                </span>
                <span className={`figs ${row.now < 0 ? "neg" : ""}`}>
                  {dollars(row.now)}
                  <span className="was">a year earlier {dollars(row.before)}</span>
                </span>
                <Pill status={row.status} word={row.rated ? undefined : "Not rated"} />
                <span className="verdict">{row.verdict}</span>
              </div>
            ))}
            <div className="seg total rag-grey">
              <span className="name">
                Whole company
                <span className="plain">All of the above added together.</span>
              </span>
              <span className={`figs ${segments.totalNow < 0 ? "neg" : ""}`}>
                {dollars(segments.totalNow)}
                <span className="was">a year earlier {dollars(segments.totalBefore)}</span>
              </span>
              <span />
            </div>
          </div>
          <p className="how-to" style={{ marginTop: 14, fontSize: 14 }}>
            Why only a year: the company has redrawn how it splits up its business three
            times in four years, so like-for-like comparisons only go back to{" "}
            {quarterName(company.segments!.earliest_comparable)}.
          </p>
        </section>
      )}

      <section id="yourself">
        <div className="sec-head">
          <h2>Deciding for yourself</h2>
          <span className="note">what the filings can&rsquo;t see</span>
        </div>
        <p className="how-to">
          Whether to stay in a job is your call, and it depends on more than the
          company&rsquo;s finances. These are the questions the filings can&rsquo;t
          answer for you:
        </p>
        <ol className="yourself">
          <li>
            <strong>Which part of the business do you work in?</strong>
            <span>
              {segments
                ? "Find it in the list above. A part that is growing is safer than the company total suggests; one that is shrinking is riskier."
                : "Companies report some figures per business line. When this company's are checked they will appear here."}
            </span>
          </li>
          <li>
            <strong>Is your team being asked to do more with fewer people?</strong>
            <span>
              Roles left unfilled when people leave, and hiring freezes, often come before
              formal cuts. None of it shows up in a filing.
            </span>
          </li>
          <li>
            <strong>How much of your pay is in company shares that haven&rsquo;t vested?</strong>
            <span>
              If the share price falls, that pay is worth less, and it ties more of your
              money to the company&rsquo;s fortunes.
            </span>
          </li>
          <li>
            <strong>What would you be paid elsewhere?</strong>
            <span>
              The market for your skills matters as much as this company&rsquo;s health.
              A weak employer is less of a risk if you could move easily.
            </span>
          </li>
          <li>
            <strong>Is leadership changing?</strong>
            <span>
              Senior departures are filed with the SEC, but the same filing type covers a
              routine board appointment, so they are listed in the detail below without
              a colour.
            </span>
          </li>
        </ol>
      </section>

      <div className="sec-head" style={{ marginBottom: -30, borderBottom: "2px solid var(--ink)" }}>
        <h2>The detail</h2>
        <span className="note">for anyone who wants the figures</span>
      </div>

      {corrections.length > 0 && (
        <section>
          <div className="sec-head">
            <h2>What the headline figures get wrong</h2>
            <span className="note">
              {corrections.length} correction{corrections.length === 1 ? "" : "s"}
            </span>
          </div>
          <div className="correct-grid">
            {corrections.map(({ caveat, principal, companion }) => (
              <div className="correct" key={caveat.headline}>
                <span className="kpi">{principal.label}</span>
                <div className="pair">
                  <span className="filed">
                    {formatValue(principal.latest_value, principal.unit)}
                  </span>
                  <span className="arrow">→</span>
                  {companion?.available ? (
                    <span className="true">
                      {formatValue(companion.latest_value, companion.unit)}
                    </span>
                  ) : (
                    <span className="true qualitative">{caveat.headline}</span>
                  )}
                </div>
                <p className="why">{caveat.detail}</p>
              </div>
            ))}
          </div>
        </section>
      )}

      {leverage?.series && recourse?.series && (
        <section>
          <div className="sec-head">
            <h2>Leverage, gross against recourse</h2>
            <span className="note">
              {leverage.quarters} quarters · {leverage.first} – {leverage.latest}
            </span>
          </div>
          <LeverageChart
            gross={leverage.series}
            recourse={recourse.series}
            grossLabel={`${formatValue(leverage.latest_value, leverage.unit)} gross`}
            recourseLabel={`${formatValue(recourse.latest_value, recourse.unit)} recourse`}
          />
          <p className="standfirst" style={{ fontSize: 15, marginTop: 14 }}>
            The shaded band is debt sitting on the balance sheet that its creditors cannot
            pursue the parent for. That gap is why the gross line is not the answer — and
            why the green line is the one to watch.
          </p>
        </section>
      )}

      <section>
        <div className="sec-head">
          <h2>Financial position</h2>
          <span className="note">latest reported quarter</span>
        </div>
        <div className="scroller">
          <table>
            <thead>
              <tr>
                <th className="left">Metric</th>
                <th className="left">Trend</th>
                <th>Latest</th>
                <th>QoQ</th>
                <th>Coverage</th>
              </tr>
            </thead>
            <tbody>
              {kpis.map(([key, kpi]) => (
                <KpiRow key={key} kpiKey={key} kpi={kpi} isCompanion={companionKeys.has(key)} />
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section>
        <div className="sec-head">
          <h2>Restructuring signals</h2>
          <span className="note">
            {restructuring.length === 0 ? "none filed" : `${restructuring.length} filed`}
          </span>
        </div>

        {restructuring.length === 0 && (
          <div className="quiet">
            <strong>No item 2.05 since 2024.</strong> A company files one when it commits to
            an exit or disposal plan — a restructuring, in the SEC&rsquo;s language. Its
            absence means no such plan has been disclosed. It does not mean no job cuts have
            happened: targeted severance expensed through normal operations does not trigger
            the requirement.
            {company.signals.length > 0 && (
              <>
                {" "}
                The {company.signals.length} filing
                {company.signals.length === 1 ? "" : "s"} below{" "}
                {company.signals.length === 1 ? "is" : "are"} item 5.02, which covers a
                senior officer resigning and a routine board election alike — the code
                cannot separate them, so none is treated as a warning.
              </>
            )}
          </div>
        )}

        {company.signals.length > 0 && (
          <div className="sig-strip" style={{ marginTop: 14 }}>
            {company.signals.map((signal) => (
              <a
                className="sig-chip"
                key={`${signal.accession}-${signal.item}`}
                href={signal.url}
                target="_blank"
                rel="noopener noreferrer"
              >
                <span className="d">{signal.date}</span>
                {signal.item} ↗
              </a>
            ))}
          </div>
        )}
      </section>

      <footer>
        Sourced from SEC EDGAR — CompanyFacts, filing instance documents, and 8-K item
        codes. Independent analysis, not affiliated with or endorsed by {company.name}. Not
        investment, career or financial advice: the checks describe the company&rsquo;s
        finances from its own filings and say nothing about any individual&rsquo;s job.
        Figures are as reported and may be restated in later filings.
      </footer>
    </main>
  );
}

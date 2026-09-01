import Link from "next/link";
import { LeverageChart, Sparkline } from "@/lib/charts";
import {
  formatValue,
  getCompany,
  getTickers,
  quarterChange,
  type Company,
  type Kpi,
} from "@/lib/data";

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

function KpiRow({
  kpi,
  isCompanion,
}: {
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
  const headline = recourse ?? leverage;

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
        <div className="lede-figs">
          {headline && (
            <div className="lede-fig">
              <span className="v">{formatValue(headline.latest_value, headline.unit)}</span>
              <span className="k">{recourse ? "Recourse leverage" : "Leverage (gross)"}</span>
            </div>
          )}
          {company.kpis.stockholders_equity?.available && (
            <div className="lede-fig">
              <span className="v">
                {formatValue(
                  company.kpis.stockholders_equity.latest_value,
                  company.kpis.stockholders_equity.unit,
                )}
              </span>
              <span className="k">Equity</span>
            </div>
          )}
          {company.kpis.eps?.available && (
            <div className="lede-fig">
              <span className="v">
                {formatValue(company.kpis.eps.latest_value, company.kpis.eps.unit)}
              </span>
              <span className="k">Diluted EPS</span>
            </div>
          )}
          <div className="lede-fig">
            <span className="v">{restructuring.length}</span>
            <span className="k">Restructuring filings</span>
          </div>
        </div>
      </header>

      <div className={`tier-banner ${company.tier === "generic" ? "generic" : ""}`}>
        <span className="lede">{company.tier === "curated" ? "Curated" : "Uncorrected"}</span>
        <p className="body">
          {company.tier === "curated"
            ? `Someone read the filings. Concept choices are checked against the source, series crossing a renaming or a restatement are verified on overlapping periods, and ${corrections.length === 1 ? "one figure below would mislead" : `${corrections.length} figures below would mislead`} without the correction attached.`
            : "The obvious concepts, pulled automatically, with nobody having read the filings. A starting point, not an answer. On the one company that has been curated, the automatic reading of leverage was wrong by roughly six times."}
        </p>
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
                <KpiRow key={key} kpi={kpi} isCompanion={companionKeys.has(key)} />
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
        investment advice. Figures are as reported and may be restated in later filings.
      </footer>
    </main>
  );
}

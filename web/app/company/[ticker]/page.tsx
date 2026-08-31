import Link from "next/link";
import {
  formatValue,
  getCompany,
  getTickers,
  quarterChange,
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
 * One metric, always rendered with any caveat bound to it.
 *
 * The pairing is enforced in lib/data.ts rather than here: caveats are
 * attached to their KPI as the data loads, so a figure that misleads on its
 * own cannot appear without its correction even if a future page forgets.
 */
function KpiRow({ kpi }: { kpi: Kpi }) {
  if (!kpi.available) {
    return (
      <tr>
        <td className="kpi-name">{kpi.label}</td>
        <td className="num muted" colSpan={3}>
          not reported by this filer
        </td>
      </tr>
    );
  }

  const change = quarterChange(kpi);
  const negative = (kpi.latest_value ?? 0) < 0;

  return (
    <>
      <tr>
        <td className="kpi-name">{kpi.label}</td>
        <td className={`num now ${negative ? "neg" : ""}`}>
          {formatValue(kpi.latest_value, kpi.unit)}
        </td>
        <td className="num muted">{formatChange(change)}</td>
        <td className="num muted">
          {kpi.quarters}q from {kpi.first}
        </td>
      </tr>
      {kpi.caveats?.map((caveat) => (
        <tr key={caveat.headline}>
          <td colSpan={4} style={{ paddingTop: 0 }}>
            <div className="caveat">
              <strong>{caveat.headline}</strong>
              {caveat.detail}
            </div>
          </td>
        </tr>
      ))}
    </>
  );
}

export default async function CompanyPage({
  params,
}: {
  params: Promise<{ ticker: string }>;
}) {
  const { ticker } = await params;
  const company = getCompany(ticker);

  const kpis = Object.entries(company.kpis);
  const high = company.signals.filter((s) => s.severity === "high");
  const restructuring = company.signals.filter((s) => s.item === "2.05");

  return (
    <main className="wrap">
      <header className="masthead">
        <div className="eyebrow">
          <Link href="/">← All companies</Link> · CIK {company.cik}
        </div>
        <h1>{company.name}</h1>
        <p className="standfirst">
          <span className={`tier tier-${company.tier}`}>{company.tier}</span>{" "}
          {company.tier === "curated"
            ? "Concept choices checked against the filings; series crossing a renaming or restatement verified against overlapping periods."
            : "Pulled automatically using the most common concepts. Nobody has verified these against the filings — treat as a starting point, not an answer."}
        </p>
      </header>

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
                <th>Latest</th>
                <th>QoQ</th>
                <th>Coverage</th>
              </tr>
            </thead>
            <tbody>
              {kpis.map(([key, kpi]) => (
                <KpiRow key={key} kpi={kpi} />
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section>
        <div className="sec-head">
          <h2>Restructuring signals</h2>
          <span className="note">8-K disclosures since 2024</span>
        </div>

        {restructuring.length === 0 && (
          <div className="quiet">
            <strong>No item 2.05 filed.</strong> A company must file one when it
            commits to an exit or disposal plan — a restructuring, in the
            SEC&rsquo;s language. Its absence means no such plan has been
            disclosed. It does not mean no job cuts have happened: targeted
            severance expensed through normal operations does not trigger the
            requirement.
          </div>
        )}

        {company.signals.length > 0 ? (
          <div style={{ marginTop: 18 }}>
            {company.signals.map((signal) => (
              <div className="signal" key={`${signal.accession}-${signal.item}`}>
                <span className="signal-date">{signal.date}</span>
                <span className={`signal-item sev-${signal.severity}`}>
                  {signal.item}
                </span>
                <span style={{ flex: 1, minWidth: "18ch" }}>
                  {signal.meaning}
                </span>
                <a
                  className="signal-date"
                  href={signal.url}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  filing ↗
                </a>
              </div>
            ))}
          </div>
        ) : (
          <p className="standfirst" style={{ marginTop: 16 }}>
            No notable 8-K items since 2024.
          </p>
        )}

        {high.length === 0 && company.signals.length > 0 && (
          <p className="standfirst" style={{ marginTop: 16 }}>
            All {company.signals.length} are medium severity. Item 5.02 covers
            both a senior officer resigning and a routine board election — the
            code alone cannot separate them, so none is treated as a warning.
          </p>
        )}
      </section>

      <footer>
        Sourced from SEC EDGAR — CompanyFacts, filing instance documents, and
        8-K item codes. Independent analysis, not affiliated with or endorsed by{" "}
        {company.name}. Not investment advice. Figures are as reported and may
        be restated in later filings.
      </footer>
    </main>
  );
}

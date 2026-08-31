import Link from "next/link";
import { getIndex } from "@/lib/data";

export default function Home() {
  const companies = getIndex();
  const curated = companies.filter((c) => c.tier === "curated").length;

  return (
    <main className="wrap">
      <header className="masthead">
        <div className="eyebrow">Independent analysis · Public SEC filings</div>
        <h1>Can this employer afford you?</h1>
        <p className="standfirst">
          Glassdoor tells you what people say about working somewhere. This
          reads the company&rsquo;s own filings and tells you whether it can pay
          for them — including the figures that are misleading until someone
          reads the footnotes.
        </p>
      </header>

      <section>
        <div className="sec-head">
          <h2>Companies</h2>
          <span className="note">
            {curated} curated · {companies.length - curated} generic
          </span>
        </div>

        <div className="company-grid">
          {companies.map((company) => (
            <Link
              key={company.ticker}
              href={`/company/${company.ticker.toLowerCase()}`}
              className="company-card"
            >
              <span className="ticker">{company.ticker}</span>
              <span className="name">{company.name}</span>
              <span className={`tier tier-${company.tier}`}>
                {company.tier}
              </span>
              <span className="meta">
                {company.kpi_count} metrics · {company.signal_count} signals
                {company.caveat_count > 0
                  ? ` · ${company.caveat_count} caveats`
                  : ""}
                <br />
                through {company.latest_quarter ?? "—"}
              </span>
            </Link>
          ))}
        </div>
      </section>

      <section>
        <div className="sec-head">
          <h2>What the two tiers mean</h2>
        </div>
        <p className="standfirst" style={{ marginBottom: "1em" }}>
          <span className="tier tier-curated">curated</span> — someone read the
          filings. Concept choices are checked, series that cross a renaming or
          a restatement are verified against overlapping periods, and the
          figures that mislead carry a correction.
        </p>
        <p className="standfirst">
          <span className="tier tier-generic">generic</span> — the obvious
          concepts, pulled automatically, with nobody having looked. Useful as a
          starting point and not as an answer. On the one company that has been
          curated, the generic reading of leverage was wrong by roughly six
          times.
        </p>
      </section>

      <footer>
        Built from SEC EDGAR: the CompanyFacts API, filing instance documents,
        and 8-K item codes. Independent analysis, not affiliated with or
        endorsed by any company covered. Not investment advice. Figures are as
        reported and may be restated in later filings.
      </footer>
    </main>
  );
}

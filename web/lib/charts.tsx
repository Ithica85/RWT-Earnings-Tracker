/**
 * Charts as server-rendered inline SVG.
 *
 * Deliberately no charting library. Every series the app draws is already in
 * the JSON, and a line is a handful of arithmetic — a library would add tens of
 * kilobytes and a client bundle to a site that is otherwise static HTML with no
 * JavaScript at all. These render at build time and ship as markup.
 *
 * Colours are CSS custom properties rather than literals so the charts follow
 * the light/dark tokens in globals.css without a second palette to keep in sync.
 */

import type { Point } from "./data";

/** A round-numbered axis step near `target` — 1, 2, 5 or 10 times a power of ten. */
function niceStep(target: number): number {
  const magnitude = Math.pow(10, Math.floor(Math.log10(Math.max(target, 1e-9))));
  const normalised = target / magnitude;
  const step = normalised <= 1 ? 1 : normalised <= 2 ? 2 : normalised <= 5 ? 5 : 10;
  return step * magnitude;
}

export function Sparkline({
  series,
  stroke = "var(--ink-2)",
  width = 132,
  height = 30,
  /** Pin the scale to include zero, and mark it, for series that cross it. */
  zero = false,
}: {
  series: Point[];
  stroke?: string;
  width?: number;
  height?: number;
  zero?: boolean;
}) {
  if (!series || series.length < 2) return null;

  const pad = 3;
  const values = series.map((p) => p.value);
  let lo = Math.min(...values);
  let hi = Math.max(...values);
  if (zero) {
    lo = Math.min(lo, 0);
    hi = Math.max(hi, 0);
  }
  const range = hi - lo || 1;

  const x = (i: number) => pad + ((width - 2 * pad) * i) / (series.length - 1);
  const y = (v: number) => height - pad - ((height - 2 * pad) * (v - lo)) / range;

  const points = values.map((v, i) => `${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(" ");
  const crossesZero = zero && lo < 0 && hi > 0;

  return (
    <svg
      className="spark"
      viewBox={`0 0 ${width} ${height}`}
      width={width}
      height={height}
      preserveAspectRatio="none"
      aria-hidden="true"
    >
      {crossesZero && (
        <line
          x1={pad}
          y1={y(0)}
          x2={width - pad}
          y2={y(0)}
          stroke="var(--rule-strong)"
          strokeWidth={1}
          strokeDasharray="2 2"
        />
      )}
      <polyline
        points={points}
        fill="none"
        stroke={stroke}
        strokeWidth={1.4}
        strokeLinejoin="round"
        strokeLinecap="round"
      />
      <circle cx={x(series.length - 1)} cy={y(values[values.length - 1])} r={2.1} fill={stroke} />
    </svg>
  );
}

/**
 * Two leverage series on one axis, with the gap between them shaded.
 *
 * Sharing an axis is correct here rather than the usual dual-axis mistake:
 * both are dimensionless multiples of the same equity, so they are directly
 * comparable, and the size of the gap is the entire point — it is consolidated
 * debt whose creditors have no claim on the parent.
 */
export function LeverageChart({
  gross,
  recourse,
  grossLabel,
  recourseLabel,
  width = 1000,
  height = 280,
}: {
  gross: Point[];
  recourse: Point[];
  grossLabel: string;
  recourseLabel: string;
  width?: number;
  height?: number;
}) {
  if (!gross || gross.length < 2) return null;

  const left = 46;
  const right = 88;
  const top = 18;
  const bottom = 30;

  const index = new Map(gross.map((p, i) => [p.quarter, i]));
  const peak = Math.max(...gross.map((p) => p.value), ...recourse.map((p) => p.value));
  const hi = peak * 1.08;
  const step = niceStep(hi / 3);

  const x = (i: number) => left + ((width - left - right) * i) / (gross.length - 1);
  const y = (v: number) => height - bottom - ((height - bottom - top) * v) / hi;

  // Recourse covers only recent quarters, so align it to the gross x-positions
  // by quarter label rather than by position.
  const paired = recourse
    .map((p) => ({ i: index.get(p.quarter), value: p.value }))
    .filter((p): p is { i: number; value: number } => p.i !== undefined);

  const line = (pts: { i: number; value: number }[]) =>
    pts.map((p) => `${x(p.i).toFixed(1)},${y(p.value).toFixed(1)}`).join(" ");

  const grossPts = gross.map((p, i) => ({ i, value: p.value }));
  const band =
    paired.length > 1
      ? [
          ...paired.map((p) => `${x(p.i).toFixed(1)},${y(gross[p.i].value).toFixed(1)}`),
          ...[...paired].reverse().map((p) => `${x(p.i).toFixed(1)},${y(p.value).toFixed(1)}`),
        ].join(" ")
      : null;

  const gridlines: number[] = [];
  for (let v = 0; v <= hi; v += step) gridlines.push(v);

  const ticks = [0, Math.floor(gross.length / 3), Math.floor((2 * gross.length) / 3), gross.length - 1];
  const lastGross = grossPts[grossPts.length - 1];
  const lastRecourse = paired[paired.length - 1];

  return (
    <svg
      viewBox={`0 0 ${width} ${height}`}
      width="100%"
      height={height}
      className="chart"
      role="img"
      aria-label={`Gross leverage against recourse leverage, ${gross[0].quarter} to ${gross[gross.length - 1].quarter}`}
    >
      {gridlines.map((v) => (
        <g key={v}>
          <line x1={left} y1={y(v)} x2={width - right} y2={y(v)} stroke="var(--rule)" strokeWidth={1} />
          <text x={left - 8} y={y(v) + 3.5} className="ax" textAnchor="end">
            {v}×
          </text>
        </g>
      ))}

      {band && <polygon points={band} fill="var(--rule)" opacity={0.55} />}

      <polyline points={line(grossPts)} fill="none" stroke="var(--red)" strokeWidth={1.8} strokeLinejoin="round" />
      {paired.length > 1 && (
        <polyline points={line(paired)} fill="none" stroke="var(--green)" strokeWidth={2.2} strokeLinejoin="round" />
      )}

      {lastGross && (
        <text x={x(lastGross.i) + 8} y={y(lastGross.value) + 4} className="lbl" fill="var(--red)">
          {grossLabel}
        </text>
      )}
      {lastRecourse && (
        <text x={x(lastRecourse.i) + 8} y={y(lastRecourse.value) + 4} className="lbl" fill="var(--green)">
          {recourseLabel}
        </text>
      )}

      {ticks.map((i) => (
        <text key={i} x={x(i)} y={height - 10} className="ax" textAnchor="middle">
          {gross[i].quarter.replace("CY", "")}
        </text>
      ))}
    </svg>
  );
}

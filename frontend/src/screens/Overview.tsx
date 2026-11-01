import { Bar, BarChart, CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Stat, Totals, Year, fmt, pct, useApi } from "../api";

interface Data {
  totals: Totals;
  monthly: { year: number; month: number; events: number; strong: number; max_mag: number }[];
  by_year: { year: number; events: number; strong: number; share: number }[];
  mag_classes: Stat[];
}
const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
const ORDER = ["Minor", "Light", "Moderate", "Strong", "Major"];

export default function Overview({ year }: { year: Year }) {
  const { data, error, loading } = useApi<Data>("overview", { year }, [year]);
  if (error) return <p className="err">{error}</p>;
  if (loading || !data) return <p className="muted">Loading…</p>;

  const lines = MONTHS.map((m, i) => {
    const row: Record<string, number | string> = { month: m };
    data.monthly.filter((r) => r.month === i + 1).forEach((r) => (row[String(r.year)] = r.events));
    return row;
  });
  const years = [...new Set(data.monthly.map((r) => String(r.year)))];
  const classes = [...data.mag_classes].sort((a, b) => ORDER.indexOf(String(a.key)) - ORDER.indexOf(String(b.key)));
  const colors: Record<string, string> = { "2024": "#4da3ff", "2025": "#ff7a45" };

  return (
    <div className="grid">
      <div className="grid g4">
        <div className="card kpi"><div className="v">{fmt(data.totals.events)}</div><div className="l">Earthquakes (M2.5+)</div></div>
        <div className="card kpi"><div className="v">{fmt(data.totals.strong)}</div><div className="l">Strong events (M ≥ 5.0)</div></div>
        <div className="card kpi"><div className="v">{pct(data.totals.share)}</div><div className="l">Strong share</div></div>
        <div className="card kpi"><div className="v">M{data.totals.max_mag?.toFixed(1)}</div><div className="l">Largest event</div></div>
      </div>
      <div className="grid g2">
        <div className="card">
          <h2>Monthly event count</h2>
          <ResponsiveContainer width="100%" height={280}>
            <LineChart data={lines}>
              <CartesianGrid stroke="#26304a" /><XAxis dataKey="month" stroke="#8c97b2" /><YAxis stroke="#8c97b2" />
              <Tooltip contentStyle={{ background: "#171e2e", border: "1px solid #26304a" }} /><Legend />
              {years.map((y) => <Line key={y} type="monotone" dataKey={y} stroke={colors[y]} strokeWidth={2} dot={false} isAnimationActive={false} />)}
            </LineChart>
          </ResponsiveContainer>
        </div>
        <div className="card">
          <h2>Events by magnitude class</h2>
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={classes.map((c) => ({ name: c.key, events: c.events }))}>
              <CartesianGrid stroke="#26304a" /><XAxis dataKey="name" stroke="#8c97b2" /><YAxis stroke="#8c97b2" scale="log" domain={[1, 100000]} ticks={[1, 10, 100, 1000, 10000, 100000]} />
              <Tooltip contentStyle={{ background: "#171e2e", border: "1px solid #26304a" }} />
              <Bar dataKey="events" fill="#ff7a45" isAnimationActive={false} />
            </BarChart>
          </ResponsiveContainer>
          <p className="note">Log scale: each step up in magnitude class is roughly ten times rarer (Gutenberg–Richter).</p>
        </div>
      </div>
      <div className="card">
        <h2>Year summary</h2>
        <table>
          <thead><tr><th>Year</th><th className="n">Events</th><th className="n">Strong (M ≥ 5)</th><th className="n">Strong share</th></tr></thead>
          <tbody>{data.by_year.map((r) => <tr key={r.year}><td>{r.year}</td><td className="n">{fmt(r.events)}</td><td className="n">{fmt(r.strong)}</td><td className="n">{pct(r.share)}</td></tr>)}</tbody>
        </table>
        <p className="note">Mean depth {data.totals.mean_depth} km · mean magnitude {data.totals.mean_mag}. Counts are catalogue events, not a measure of seismic energy.</p>
      </div>
    </div>
  );
}

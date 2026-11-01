import { Bar, BarChart, CartesianGrid, Cell, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Stat, Totals, Year, fmt, pct, useApi } from "../api";

interface Cond { depth_class: Stat[]; mag_type: Stat[]; status: Stat[]; network: Stat[]; baseline: Totals }
interface Temporal { hours: Stat[]; weekdays: Stat[] }
interface Combos { groups: (Stat & { share_ratio: number | null; odds_ratio: number | null })[]; min_count: number }
interface Regions { regions: (Stat & { max_mag: number; mean_depth: number })[] }

const tip = { contentStyle: { background: "#171e2e", border: "1px solid #26304a" } };

function ShareBars({ title, rows, base }: { title: string; rows: Stat[]; base: number | null }) {
  return (
    <div className="card">
      <h2>{title}</h2>
      <ResponsiveContainer width="100%" height={240}>
        <BarChart data={rows.map((r) => ({ name: String(r.label ?? r.key), share: r.share, events: r.events }))}>
          <CartesianGrid stroke="#26304a" /><XAxis dataKey="name" stroke="#8c97b2" interval={0} /><YAxis stroke="#8c97b2" unit="%" />
          <Tooltip {...tip} formatter={(v: number, _n, p) => [`${v}% of ${fmt(p.payload.events)} events`, "Strong share"]} />
          {base != null && <ReferenceLine y={base} stroke="#ffc145" strokeDasharray="4 4" />}
          <Bar dataKey="share" isAnimationActive={false}>{rows.map((_, i) => <Cell key={i} fill="#ff7a45" />)}</Bar>
        </BarChart>
      </ResponsiveContainer>
      <p className="note">Dashed line = baseline strong share ({pct(base)}). Each bar uses its own event count as the denominator.</p>
    </div>
  );
}

export default function Patterns({ year }: { year: Year }) {
  const cond = useApi<Cond>("conditions", { year }, [year]).data;
  const temp = useApi<Temporal>("temporal", { year }, [year]).data;
  const combos = useApi<Combos>("combinations", { year, min_count: 100 }, [year]).data;
  const regs = useApi<Regions>("regions", { year, limit: 12 }, [year]).data;
  if (!cond || !temp || !combos || !regs) return <p className="muted">Loading…</p>;
  const base = cond.baseline.share;

  return (
    <div className="grid">
      <div className="grid g2">
        <ShareBars title="Strong share by depth class" rows={cond.depth_class} base={base} />
        <ShareBars title="Strong share by magnitude type" rows={cond.mag_type.filter((r) => r.events >= 100)} base={base} />
      </div>
      <div className="grid g2">
        <div className="card">
          <h2>Events by hour (UTC)</h2>
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={temp.hours.map((h) => ({ hour: h.key, events: h.events }))}>
              <CartesianGrid stroke="#26304a" /><XAxis dataKey="hour" stroke="#8c97b2" interval={0} /><YAxis stroke="#8c97b2" /><Tooltip {...tip} />
              <Bar dataKey="events" fill="#4da3ff" isAnimationActive={false} />
            </BarChart>
          </ResponsiveContainer>
          <p className="note">Earthquakes follow no daily clock; flat hourly counts are expected, unlike human-driven events such as road collisions.</p>
        </div>
        <ShareBars title="Strong share by weekday" rows={temp.weekdays} base={base} />
      </div>
      <div className="grid g2">
        <div className="card">
          <h2>Depth class × magnitude type (≥ {combos.min_count} events)</h2>
          <table>
            <thead><tr><th>Group</th><th className="n">Events</th><th className="n">Share</th><th className="n">Ratio</th><th className="n">Odds</th></tr></thead>
            <tbody>{combos.groups.slice(0, 10).map((g) => <tr key={String(g.key)}><td>{g.key}</td><td className="n">{fmt(g.events)}</td><td className="n">{pct(g.share)}</td><td className="n">{g.share_ratio}</td><td className="n">{g.odds_ratio}</td></tr>)}</tbody>
          </table>
        </div>
        <div className="card">
          <h2>Most active regions</h2>
          <table>
            <thead><tr><th>Region</th><th className="n">Events</th><th className="n">Strong share</th><th className="n">Max M</th></tr></thead>
            <tbody>{regs.regions.map((r) => <tr key={String(r.key)}><td>{r.key}</td><td className="n">{fmt(r.events)}</td><td className="n">{pct(r.share)}</td><td className="n">{r.max_mag}</td></tr>)}</tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

import { useState } from "react";
import { Year, fmt, pct, useApi, Totals } from "../api";

interface Options { depth_classes: string[]; mag_types: string[]; statuses: string[]; networks: string[]; regions: string[] }
interface Cmp { baseline: Totals; scenario: Totals; share_ratio: number | null; odds_ratio: number | null }
interface Sc { depth_class: string; mag_type: string; region: string; network: string }

const A: Sc = { depth_class: "Shallow", mag_type: "mb", region: "any", network: "any" };
const B: Sc = { depth_class: "Deep", mag_type: "mb", region: "any", network: "any" };

function Picker({ sc, set, o }: { sc: Sc; set: (s: Sc) => void; o: Options }) {
  const sel = (k: keyof Sc, label: string, vals: string[]) => (
    <label>{label}
      <select value={sc[k]} onChange={(e) => set({ ...sc, [k]: e.target.value })}>
        <option value="any">Any</option>{vals.map((v) => <option key={v}>{v}</option>)}
      </select>
    </label>
  );
  return <div className="row">{sel("depth_class", "Depth class", o.depth_classes)}{sel("mag_type", "Magnitude type", o.mag_types)}{sel("region", "Region", o.regions)}{sel("network", "Network", o.networks)}</div>;
}

function Result({ title, sc, year }: { title: string; sc: Sc; year: Year }) {
  const { data } = useApi<Cmp>("compare", { year, ...sc }, [year, sc.depth_class, sc.mag_type, sc.region, sc.network]);
  return (
    <div>
      <h2>{title}</h2>
      {data ? (
        <>
          <div className="big">{pct(data.scenario.share)}</div>
          <p className="muted">{fmt(data.scenario.strong)} strong of {fmt(data.scenario.events)} events</p>
          <p>Share ratio vs baseline: <b>{data.share_ratio ?? "—"}</b> · Odds ratio: <b>{data.odds_ratio ?? "—"}</b></p>
        </>
      ) : <p className="muted">Loading…</p>}
    </div>
  );
}

export default function Scenario({ year }: { year: Year }) {
  const [a, setA] = useState<Sc>(A);
  const [b, setB] = useState<Sc>(B);
  const o = useApi<Options>("options", {}, []).data;
  const ca = useApi<Cmp>("compare", { year, ...a }, [year, a]).data;
  const cb = useApi<Cmp>("compare", { year, ...b }, [year, b]).data;
  const ratio = ca?.scenario.share && cb?.scenario.share ? (cb.scenario.share / ca.scenario.share).toFixed(2) : null;
  if (!o) return <p className="muted">Loading…</p>;

  return (
    <div className="grid">
      <div className="grid g2">
        <div className="card"><Picker sc={a} set={setA} o={o} /><Result title="Scenario A" sc={a} year={year} /></div>
        <div className="card"><Picker sc={b} set={setB} o={o} /><Result title="Scenario B" sc={b} year={year} /></div>
      </div>
      <div className="card">
        <h2>Comparison</h2>
        <p>Scenario B's strong share is <b>{ratio ?? "—"}×</b> that of Scenario A. Baseline for the selected year(s): {pct(ca?.baseline.share)} of {fmt(ca?.baseline.events)} events.</p>
        <p className="note">Ratios compare proportions among catalogued events. Differences in strong share largely reflect detection thresholds (regional networks log small events that global ones miss), so this is descriptive, not a hazard estimate.</p>
      </div>
    </div>
  );
}

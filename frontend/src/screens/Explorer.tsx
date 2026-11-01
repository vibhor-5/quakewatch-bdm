import { useEffect, useState } from "react";
import { Year, fmt, get, useApi } from "../api";

interface Ev { id: string; place: string; mag: number; mag_type: string; depth_km: number; time: string; region: string; mag_class: string; status: string }
interface List { total: number; page: number; pages: number; events: Ev[] }
interface Detail { event: Record<string, unknown>; nearby: { id: string; mag: number; place: string; time: string; depth_km: number }[] }

export default function Explorer({ year }: { year: Year }) {
  const [q, setQ] = useState("");
  const [query, setQuery] = useState("");
  const [strong, setStrong] = useState(false);
  const [page, setPage] = useState(1);
  const [open, setOpen] = useState<Detail | null>(null);
  const [tab, setTab] = useState<"summary" | "json">("summary");
  const { data, error } = useApi<List>("events", { year, q: query, strong: strong ? 1 : undefined, page }, [year, query, strong, page]);
  useEffect(() => setPage(1), [year, query, strong]);

  const show = (id: string) => get<Detail>(`events/${id}`).then((d) => { setOpen(d); setTab("summary"); });
  const e = open?.event as Record<string, any> | undefined;

  return (
    <div className="card">
      <form className="row" onSubmit={(ev) => { ev.preventDefault(); setQuery(q.trim()); }}>
        <label>Search place or event id<input value={q} onChange={(x) => setQ(x.target.value)} placeholder="e.g. Kamchatka or us6000..." style={{ width: 280 }} /></label>
        <label><span>Filter</span><select value={strong ? "1" : "0"} onChange={(x) => setStrong(x.target.value === "1")}><option value="0">All events</option><option value="1">Strong only (M ≥ 5)</option></select></label>
        <button className="btn" type="submit">Search</button>
        <span className="muted">{data ? `${fmt(data.total)} matching events` : ""}</span>
      </form>
      {error && <p className="err">{error}</p>}
      <table>
        <thead><tr><th>Time (UTC)</th><th className="n">Mag</th><th>Type</th><th className="n">Depth km</th><th>Place</th><th>Status</th></tr></thead>
        <tbody>{data?.events.map((r) => (
          <tr key={r.id} className="click" onClick={() => show(r.id)}>
            <td>{r.time.replace("T", " ").slice(0, 16)}</td><td className="n">{r.mag.toFixed(1)}</td><td>{r.mag_type}</td>
            <td className="n">{r.depth_km.toFixed(1)}</td><td>{r.place}</td><td>{r.status}</td>
          </tr>))}</tbody>
      </table>
      <div className="row" style={{ marginTop: 12 }}>
        <button className="btn" disabled={page <= 1} onClick={() => setPage(page - 1)}>Previous</button>
        <span className="muted">Page {data?.page ?? 1} of {data?.pages ?? 1}</span>
        <button className="btn" disabled={!data || page >= data.pages} onClick={() => setPage(page + 1)}>Next</button>
      </div>

      {open && e && (
        <div className="modal-bg" onClick={() => setOpen(null)}>
          <div className="modal" onClick={(x) => x.stopPropagation()}>
            <div className="row"><h2 style={{ margin: 0 }}>Event {e.id}</h2>
              <button className="btn" onClick={() => setTab("summary")}>Summary</button>
              <button className="btn" onClick={() => setTab("json")}>JSON document</button>
              <button className="btn" onClick={() => setOpen(null)}>Close</button></div>
            {tab === "json" ? <pre>{JSON.stringify(open.event, null, 2)}</pre> : (
              <>
                <table><tbody>
                  <tr><td>Place</td><td>{e.place}</td></tr>
                  <tr><td>Magnitude</td><td>M{e.mag} ({e.mag_type}) · {e.mag_class}</td></tr>
                  <tr><td>Depth</td><td>{e.depth_km} km · {e.depth_class}</td></tr>
                  <tr><td>Time</td><td>{e.time}</td></tr>
                  <tr><td>Location</td><td>{e.latitude}, {e.longitude} · grid {e.grid_id}</td></tr>
                  <tr><td>Network / status</td><td>{e.net} / {e.status}</td></tr>
                </tbody></table>
                <h2 style={{ marginTop: 16 }}>Within 150 km and ±1 day ({open.nearby.length})</h2>
                {open.nearby.length ? (
                  <table><thead><tr><th>Time</th><th className="n">Mag</th><th className="n">Depth</th><th>Place</th></tr></thead>
                    <tbody>{open.nearby.slice(0, 12).map((n) => <tr key={n.id}><td>{n.time.replace("T", " ").slice(0, 16)}</td><td className="n">{n.mag.toFixed(1)}</td><td className="n">{n.depth_km.toFixed(1)}</td><td>{n.place}</td></tr>)}</tbody></table>
                ) : <p className="muted">No other catalogued events nearby in this window.</p>}
                <p className="note">Found with a MongoDB $geoWithin / $centerSphere query on the 2dsphere index plus a time range. Proximity alone does not prove events are causally related.</p>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

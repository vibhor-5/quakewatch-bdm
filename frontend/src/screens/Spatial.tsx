import L from "leaflet";
import { useEffect, useRef, useState } from "react";
import { Year, fmt, pct, useApi } from "../api";

interface Cell { key: string; events: number; strong: number; share: number; lat: number; lon: number; max_mag: number; mean_depth: number }
interface Data { cells: Cell[]; distinct_cells: number; limit: number; min_count: number }

const VIEWS: Record<string, [number, number, number]> = {
  World: [20, 10, 2], "Pacific Ring": [20, 160, 3], Japan: [37, 138, 5], Americas: [10, -80, 3], "S.E. Asia": [-2, 118, 4], Alaska: [62, -150, 4],
};
const colour = (s: number) => (s > 30 ? "#ff3d3d" : s > 15 ? "#ff7a45" : s > 5 ? "#ffc145" : "#4da3ff");

export default function Spatial({ year }: { year: Year }) {
  const [minCount, setMinCount] = useState(25);
  const [sel, setSel] = useState<Cell | null>(null);
  const { data, error } = useApi<Data>("hotspots", { year, min_count: minCount, limit: 400 }, [year, minCount]);
  const el = useRef<HTMLDivElement>(null);
  const map = useRef<L.Map | null>(null);
  const layer = useRef<L.LayerGroup | null>(null);

  useEffect(() => {
    if (!el.current || map.current) return;
    map.current = L.map(el.current, { worldCopyJump: true }).setView([20, 10], 2);
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", { attribution: "© OpenStreetMap contributors", maxZoom: 9 }).addTo(map.current);
    layer.current = L.layerGroup().addTo(map.current);
  }, []);

  useEffect(() => {
    if (!layer.current || !data) return;
    layer.current.clearLayers();
    data.cells.forEach((c) => {
      L.circleMarker([c.lat, c.lon], { radius: Math.max(4, Math.sqrt(c.events) * 0.9), color: colour(c.share), fillColor: colour(c.share), fillOpacity: 0.55, weight: 1 })
        .on("click", () => setSel(c)).bindTooltip(`${c.events} events`).addTo(layer.current!);
    });
  }, [data]);

  return (
    <div className="grid">
      <div className="card">
        <div className="row">
          <label>Min events per 2° cell<input type="number" min={1} value={minCount} onChange={(e) => setMinCount(Math.max(1, Number(e.target.value) || 1))} style={{ width: 120 }} /></label>
          {Object.entries(VIEWS).map(([name, v]) => <button key={name} className="btn" onClick={() => map.current?.setView([v[0], v[1]], v[2])}>{name}</button>)}
          <span className="muted">{data ? `${data.cells.length} cells shown of ${fmt(data.distinct_cells)} distinct (cap ${data.limit})` : ""}</span>
        </div>
        {error && <p className="err">{error}</p>}
        <div className="grid" style={{ gridTemplateColumns: "3fr 1fr" }}>
          <div ref={el} className="map" />
          <div>
            <h2>Cell inspector</h2>
            {sel ? (
              <table><tbody>
                <tr><td>Centre</td><td className="n">{sel.lat}°, {sel.lon}°</td></tr>
                <tr><td>Events</td><td className="n">{fmt(sel.events)}</td></tr>
                <tr><td>Strong (M ≥ 5)</td><td className="n">{fmt(sel.strong)}</td></tr>
                <tr><td>Strong share</td><td className="n">{pct(sel.share)}</td></tr>
                <tr><td>Largest</td><td className="n">M{sel.max_mag}</td></tr>
                <tr><td>Mean depth</td><td className="n">{sel.mean_depth} km</td></tr>
              </tbody></table>
            ) : <p className="muted">Click a marker.</p>}
            <p className="note">Marker size = event count; colour = strong share (blue &lt;5%, yellow, orange, red &gt;30%).</p>
          </div>
        </div>
        <p className="note">Cells are 2°×2° angular bins, not equal-area. High counts can reflect dense seismic networks (e.g. the US, which reports from M2.5) as well as high seismicity.</p>
      </div>
    </div>
  );
}

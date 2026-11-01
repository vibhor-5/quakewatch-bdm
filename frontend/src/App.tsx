import { useState } from "react";
import { Year, useApi } from "./api";
import Overview from "./screens/Overview";
import Spatial from "./screens/Spatial";
import Scenario from "./screens/Scenario";
import Patterns from "./screens/Patterns";
import Explorer from "./screens/Explorer";

const SCREENS = ["Overview", "Spatial Concentrations", "Scenario Comparator", "Pattern Analysis", "Record Explorer"] as const;
type Screen = (typeof SCREENS)[number];

export default function App() {
  const [screen, setScreen] = useState<Screen>("Overview");
  const [year, setYear] = useState<Year>("all");
  const health = useApi<{ status: string; collections: Record<string, number> }>("health", {}, []);

  return (
    <div className="app">
      <header className="top">
        <div>
          <h1>QuakeWatch</h1>
          <p className="muted">Global earthquakes, USGS ComCat · M2.5+ · 2024–2025</p>
        </div>
        <div className="controls">
          <label>
            Year
            <select value={year} onChange={(e) => setYear(e.target.value as Year)}>
              <option value="all">2024–2025</option>
              <option value="2024">2024</option>
              <option value="2025">2025</option>
            </select>
          </label>
          <span className={`pill ${health.error ? "bad" : "ok"}`}>
            {health.error ? "API offline" : health.data ? `MongoDB · ${Object.values(health.data.collections).reduce((a, b) => a + b, 0).toLocaleString("en-GB")} docs` : "connecting…"}
          </span>
        </div>
      </header>
      <nav className="tabs">
        {SCREENS.map((s) => (
          <button key={s} className={s === screen ? "active" : ""} onClick={() => setScreen(s)}>{s}</button>
        ))}
      </nav>
      <main>
        {screen === "Overview" && <Overview year={year} />}
        {screen === "Spatial Concentrations" && <Spatial year={year} />}
        {screen === "Scenario Comparator" && <Scenario year={year} />}
        {screen === "Pattern Analysis" && <Patterns year={year} />}
        {screen === "Record Explorer" && <Explorer year={year} />}
      </main>
    </div>
  );
}

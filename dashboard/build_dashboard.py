"""Build dashboard/index.html: a standalone BI dashboard from the exported CSV tables.

It mirrors the three Power BI pages (Overview, Time & Place, Conditions). The same CSVs in
data/exports can be imported into Power BI Desktop; see powerbi/README.md.
"""
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
from plotly.subplots import make_subplots

ROOT = Path(__file__).resolve().parents[1]
EXP = ROOT / "data" / "exports"
BG, PANEL, TXT, GRID = "#0f1420", "#171e2e", "#e6ebf5", "#26304a"
C24, C25, ACC = "#4da3ff", "#ff7a45", "#ffc145"

fact = pd.read_csv(EXP / "fact_earthquakes.csv")
hot = pd.read_csv(EXP / "agg_hotspots_grid.csv")
cond = pd.read_csv(EXP / "agg_conditions.csv")
regions = pd.read_csv(EXP / "agg_regions.csv")
matrix = pd.read_csv(EXP / "agg_depth_mag_matrix.csv")

N, S = len(fact), int(fact.is_strong.sum())
base = 100 * S / N


def style(fig, h=380):
    fig.update_layout(height=h, paper_bgcolor=PANEL, plot_bgcolor=PANEL, font=dict(color=TXT),
                      margin=dict(l=50, r=20, t=50, b=40), legend=dict(orientation="h", y=1.12))
    fig.update_xaxes(gridcolor=GRID)
    fig.update_yaxes(gridcolor=GRID)
    return fig


def html(fig):
    return pio.to_html(fig, include_plotlyjs=False, full_html=False, config={"displaylogo": False})


# --- Page 1: overview ---
monthly = fact.groupby(["year", "month"]).agg(events=("mag", "size"), strong=("is_strong", "sum")).reset_index()
f1 = go.Figure()
for y, c in ((2024, C24), (2025, C25)):
    m = monthly[monthly.year == y]
    f1.add_scatter(x=m.month, y=m.events, name=str(y), line=dict(color=c, width=3), mode="lines+markers")
f1.update_layout(title="Monthly earthquakes (M2.5+)", xaxis=dict(tickmode="array", tickvals=list(range(1, 13)),
                 ticktext=["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]))
style(f1)

mc = fact.mag_class.value_counts().reindex(["Minor", "Light", "Moderate", "Strong", "Major"])
f2 = go.Figure(go.Bar(x=mc.index, y=mc.values, marker_color=C25, text=mc.values, textposition="outside"))
f2.update_layout(title="Events by magnitude class (log scale)", yaxis_type="log")
style(f2)

# --- Page 2: time and place ---
hours = fact.groupby("hour").size()
wd = fact.groupby("weekday").agg(events=("mag", "size"), share=("is_strong", "mean"))
names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
f3 = make_subplots(rows=1, cols=2, subplot_titles=("Events by hour (UTC)", "Strong share by weekday (%)"))
f3.add_bar(x=hours.index, y=hours.values, marker_color=C24, row=1, col=1)
f3.add_bar(x=names, y=(wd.share * 100).round(2), marker_color=C25, row=1, col=2)
f3.add_hline(y=base, line_dash="dash", line_color=ACC, row=1, col=2)
f3.update_layout(showlegend=False)
style(f3)

g = hot.groupby(["grid_id", "grid_lat", "grid_lon"]).agg(events=("events", "sum"), strong=("strong", "sum")).reset_index()
g["share"] = (100 * g.strong / g.events).round(2)
f4 = go.Figure(go.Scattergeo(lat=g.grid_lat, lon=g.grid_lon, mode="markers",
    marker=dict(size=(g.events ** 0.5).clip(upper=40) * 0.9 + 3, color=g.share, colorscale="YlOrRd",
                cmin=0, cmax=40, colorbar=dict(title="Strong %"), line=dict(width=0.3, color="#000"), opacity=0.8),
    text=g.apply(lambda r: f"cell {r.grid_lat},{r.grid_lon}<br>{int(r.events)} events, {r.share}% strong", axis=1),
    hoverinfo="text"))
f4.update_layout(title="2°×2° cells (≥5 events in a year): size = events, colour = strong share",
                 geo=dict(projection_type="natural earth", bgcolor=PANEL, landcolor="#232d45", oceancolor="#0f1420",
                          showocean=True, showland=True, coastlinecolor="#3a4766"))
style(f4, 520)

top = regions.groupby("region").agg(events=("events", "sum"), strong=("strong", "sum")).nlargest(12, "events").iloc[::-1]
f5 = go.Figure(go.Bar(y=top.index, x=top.events, orientation="h", marker_color=C24,
                      text=[f"{100*s/e:.1f}% strong" for s, e in zip(top.strong, top.events)]))
f5.update_layout(title="Most active regions")
style(f5, 420)

# --- Page 3: conditions ---
def share_bar(ctype, title, min_events=100):
    c = cond[cond.condition_type == ctype].groupby("value").agg(events=("events", "sum"), strong=("strong", "sum")).reset_index()
    c = c[c.events >= min_events]
    c["share"] = 100 * c.strong / c.events
    c = c.sort_values("share", ascending=False)
    fig = go.Figure(go.Bar(x=c.value, y=c.share.round(2), marker_color=C25,
                           customdata=c.events, hovertemplate="%{x}: %{y}% of %{customdata} events<extra></extra>"))
    fig.add_hline(y=base, line_dash="dash", line_color=ACC, annotation_text=f"baseline {base:.2f}%")
    fig.update_layout(title=title, yaxis_title="% strong")
    return style(fig, 340)

pivot = matrix.groupby(["depth_class", "mag_class"]).events.sum().unstack().reindex(
    index=["Shallow", "Intermediate", "Deep"], columns=["Minor", "Light", "Moderate", "Strong", "Major"]).fillna(0)
f8 = go.Figure(go.Heatmap(z=pivot.values, x=pivot.columns, y=pivot.index, colorscale="YlOrRd", text=pivot.values.astype(int),
                          texttemplate="%{text}", zmin=0, zmax=15000))
f8.update_layout(title="Depth class × magnitude class (events)")
style(f8, 320)

KPIS = [(f"{N:,}", "Earthquakes (M2.5+)"), (f"{S:,}", "Strong events (M ≥ 5.0)"), (f"{base:.2f}%", "Strong share"),
        (f"M{fact.mag.max():.1f}", "Largest event"), (f"{fact.event_id.nunique():,}", "Unique event IDs")]
kpi_html = "".join(f'<div class="kpi"><div class="v">{v}</div><div class="l">{l}</div></div>' for v, l in KPIS)

page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><title>QuakeWatch BI Dashboard</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
<style>
body{{margin:0;background:{BG};color:{TXT};font:14px -apple-system,Segoe UI,Roboto,sans-serif}}
.wrap{{max-width:1240px;margin:0 auto;padding:20px}} h1{{margin:0}} h1::before{{content:"◉ ";color:{C25}}}
.sub{{color:#8c97b2;margin:2px 0 14px}} .tabs button{{background:none;border:none;color:#8c97b2;padding:10px 16px;font-size:15px;cursor:pointer;border-bottom:2px solid transparent}}
.tabs button.on{{color:{TXT};border-bottom-color:{C25}}} .tabs{{border-bottom:1px solid {GRID};margin-bottom:16px}}
.page{{display:none}} .page.on{{display:block}}
.kpis{{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:12px;margin-bottom:14px}}
.kpi{{background:{PANEL};border:1px solid {GRID};border-radius:10px;padding:14px}} .kpi .v{{font-size:28px;font-weight:700}}
.kpi .l{{color:#8c97b2;font-size:12px;text-transform:uppercase;letter-spacing:.6px}}
.g2{{display:grid;grid-template-columns:repeat(auto-fit,minmax(480px,1fr));gap:14px}} .g2>div,.one>div{{border-radius:10px;overflow:hidden;margin-bottom:14px}}
.note{{color:#8c97b2;font-size:12px}}
</style></head><body><div class="wrap">
<h1>QuakeWatch BI Dashboard</h1><p class="sub">USGS ComCat · tectonic earthquakes M2.5+ · 2024–2025 · built from data/exports/*.csv</p>
<div class="tabs"><button class="on" onclick="show(0,this)">Overview</button><button onclick="show(1,this)">Time &amp; Place</button><button onclick="show(2,this)">Conditions</button></div>
<div class="page on"><div class="kpis">{kpi_html}</div><div class="g2"><div>{html(f1)}</div><div>{html(f2)}</div></div>
<p class="note">Strong share = events with M ≥ 5.0 divided by all catalogued events. Counts reflect catalogue completeness as well as seismicity.</p></div>
<div class="page"><div class="one"><div>{html(f3)}</div><div>{html(f4)}</div><div>{html(f5)}</div></div></div>
<div class="page"><div class="g2"><div>{html(share_bar("depth_class", "Strong share by depth class"))}</div>
<div>{html(share_bar("mag_type", "Strong share by magnitude type"))}</div>
<div>{html(share_bar("network", "Strong share by contributing network"))}</div><div>{html(f8)}</div></div>
<p class="note">Magnitude type and network differences mostly reflect detection and reporting practice (moment magnitudes are computed for larger events), not physical differences.</p></div>
</div><script>function show(i,b){{document.querySelectorAll('.page').forEach((p,j)=>p.classList.toggle('on',i===j));
document.querySelectorAll('.tabs button').forEach(x=>x.classList.remove('on'));b.classList.add('on');window.dispatchEvent(new Event('resize'));}}</script></body></html>"""
(Path(__file__).parent / "index.html").write_text(page)
print("wrote dashboard/index.html", len(page) // 1024, "KB")

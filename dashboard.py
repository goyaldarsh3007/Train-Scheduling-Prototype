from pathlib import Path

import networkx as nx
import plotly.graph_objects as go
import streamlit as st

from Prototype_02 import build_network, evaluate_routes, get_blocked_edges, load_data


st.set_page_config(
    page_title="Railway Dispatch Control",
    page_icon="🚆",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@500;600;700&family=DM+Mono:wght@400;500&display=swap');
    :root { --ink: #f4f1ea; --muted: #9ca5a7; --panel: #172124; --line: #2c393c; --green: #72e0a0; --amber: #f2b84b; --red: #f27b72; }
    .stApp { background: #0c1416; color: var(--ink); }
    [data-testid="stSidebar"] { background: #111c1f; border-right: 1px solid var(--line); }
    [data-testid="stSidebar"] > div:first-child { padding-top: 2rem; }
    h1, h2, h3, p, label, [data-testid="stMetricLabel"] { font-family: 'Barlow Condensed', sans-serif; }
    h1 { font-size: 3.4rem !important; line-height: .95 !important; letter-spacing: 0 !important; font-weight: 700 !important; }
    h2 { font-size: 1.7rem !important; letter-spacing: 0 !important; }
    .mono, [data-testid="stMetricValue"] { font-family: 'DM Mono', monospace !important; }
    .eyebrow { color: var(--green); font-family: 'DM Mono', monospace; font-size: .72rem; letter-spacing: .12em; text-transform: uppercase; }
    .subtitle { color: var(--muted); font-size: 1.1rem; margin-top: -.8rem; margin-bottom: 1.6rem; }
    .metric { background: var(--panel); border: 1px solid var(--line); border-top: 3px solid var(--green); padding: 1rem 1.1rem; min-height: 108px; }
    .metric.warn { border-top-color: var(--amber); } .metric.alert { border-top-color: var(--red); }
    .metric-label { color: var(--muted); text-transform: uppercase; font-size: .75rem; letter-spacing: .1em; }
    .metric-value { color: var(--ink); font: 500 2rem 'DM Mono', monospace; margin-top: .35rem; }
    .section-title { border-bottom: 1px solid var(--line); padding-bottom: .5rem; margin-top: 1.8rem; }
    .stDataFrame { border: 1px solid var(--line); }
    div[data-testid="stButton"] button { border-radius: 2px; border: 1px solid var(--green); color: var(--green); background: transparent; }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data
def get_dispatch_data(data_directory, selected_maintenance_ids):
    data = load_data(data_directory)
    graph = build_network(data["nodes"], data["sections"])
    selected_maintenance = data["maintenance_blocks"][
        data["maintenance_blocks"]["maintenance_id"].isin(selected_maintenance_ids)
    ]
    blocked_edges = get_blocked_edges(
        selected_maintenance, data["tracks"], data["sections"]
    )
    results = evaluate_routes(
        graph,
        data["train_routes"],
        blocked_edges,
        selected_maintenance,
    )
    return data, graph, selected_maintenance, blocked_edges, results


def network_figure(graph, blocked_edges, highlighted_path=None):
    # Approximate longitude/latitude positions keep the schematic aligned with geography.
    geographic_positions = {
        "N001": (0, 72),    # Ludhiana
        "N002": (20, 78),   # Khanna
        "N003": (62, 48),   # Ambala
        "N004": (62, 82),   # Chandigarh
        "N005": (35, 56),   # Sirhind
        "N006": (48, 38),   # Rajpura
        "N007": (34, 20),   # Patiala
        "N008": (84, 96),   # Kalka
        "N009": (-4, 92),   # Doraha
        "N010": (86, 22),   # Panipat
        "N011": (88, 4),    # Samalkha
        "N012": (88, -22),  # Delhi
    }
    positions = {
        node: geographic_positions.get(node, (0, 0))
        for node in graph.nodes()
    }
    blocked = {frozenset(edge) for edge in blocked_edges}
    highlighted = {
        frozenset((highlighted_path[index], highlighted_path[index + 1]))
        for index in range(len(highlighted_path or []) - 1)
    }
    edge_traces = []
    for start, end, attributes in graph.edges(data=True):
        start_x, start_y = positions[start]
        end_x, end_y = positions[end]
        section_id = attributes["section_id"]
        track_count = int(attributes.get("num_tracks", 1))
        is_blocked = frozenset((start, end)) in blocked
        edge_traces.append(go.Scatter(
            x=[start_x, end_x], y=[start_y, end_y], mode="lines",
            hovertemplate=(
                f"{section_id}<br>{track_count} track(s)<br>"
                f"{attributes['time']} min<extra></extra>"
            ),
            line=dict(
                width=3 + track_count,
                color="#f27b72" if is_blocked else "#52676b",
            ),
            showlegend=False,
        ))
    node_ids = list(graph.nodes())
    label_positions = {
        "N001": "middle left",
        "N002": "top center",
        "N003": "bottom center",
        "N004": "top center",
        "N005": "middle left",
        "N006": "bottom center",
        "N007": "bottom center",
        "N008": "top center",
        "N009": "top center",
        "N010": "top center",
        "N011": "bottom center",
        "N012": "bottom center",
    }
    node_trace = go.Scatter(
        x=[positions[node][0] for node in node_ids],
        y=[positions[node][1] for node in node_ids],
        mode="markers+text",
        text=[f"{graph.nodes[node]['name']}<br><sup>{node}</sup>" for node in node_ids],
        textposition=[label_positions.get(node, "top center") for node in node_ids],
        hovertext=node_ids,
        hoverinfo="text",
        marker=dict(size=15, color="#72e0a0", line=dict(width=2, color="#0c1416")),
        textfont=dict(color="#f4f1ea", size=11),
    )
    figure = go.Figure(edge_traces + [node_trace])
    for start, end in graph.edges():
        if frozenset((start, end)) in blocked:
            figure.add_trace(go.Scatter(
                x=[positions[start][0], positions[end][0]],
                y=[positions[start][1], positions[end][1]],
                mode="lines", hoverinfo="none",
                line=dict(width=5, color="#f27b72"), showlegend=False,
            ))
        elif frozenset((start, end)) in highlighted:
            figure.add_trace(go.Scatter(
                x=[positions[start][0], positions[end][0]],
                y=[positions[start][1], positions[end][1]],
                mode="lines", hoverinfo="none",
                line=dict(width=5, color="#72e0a0"), showlegend=False,
            ))
    figure.update_layout(
        height=760, margin=dict(l=8, r=8, t=8, b=8),
        paper_bgcolor="#172124", plot_bgcolor="#172124",
        showlegend=False,
        xaxis=dict(visible=False, range=[-18, 105], scaleanchor="y", scaleratio=1),
        yaxis=dict(visible=False, range=[-36, 110]),
    )
    return figure


def metric(label, value, style=""):
    st.markdown(
        f'<div class="metric {style}"><div class="metric-label">{label}</div>'
        f'<div class="metric-value">{value}</div></div>',
        unsafe_allow_html=True,
    )


st.sidebar.markdown('<div class="eyebrow">DISPATCH / LIVE BOARD</div>', unsafe_allow_html=True)
st.sidebar.title("Control filters")
data_directory = st.sidebar.text_input("Data directory", str(Path(__file__).resolve().parent))

try:
    source_data = load_data(data_directory)
    maintenance_ids = source_data["maintenance_blocks"]["maintenance_id"].tolist()
    maintenance_labels = {
        row["maintenance_id"]: f'{row["maintenance_id"]} | {row["track_id"]} | {row["duration_hours"]}h'
        for _, row in source_data["maintenance_blocks"].iterrows()
    }
    selected_maintenance_ids = st.sidebar.multiselect(
        "Maintenance work to simulate",
        maintenance_ids,
        default=maintenance_ids,
        format_func=lambda value: maintenance_labels[value],
    )
    data, graph, selected_maintenance, blocked_edges, results = get_dispatch_data(
        data_directory, tuple(selected_maintenance_ids)
    )
except (FileNotFoundError, KeyError, ValueError) as error:
    st.error(f"Could not load the dispatch data: {error}")
    st.stop()

baseline = evaluate_routes(
    graph,
    data["train_routes"],
    [],
    data["maintenance_blocks"].iloc[0:0],
)
comparison = results.merge(
    baseline[["train_id", "original_path"]].rename(columns={"original_path": "baseline_path"}),
    on="train_id",
)
comparison["affected"] = comparison.apply(
    lambda row: row["status"] != "ON TIME"
    or row["final_path"] != row["baseline_path"],
    axis=1,
)
status_options = ["ALL"] + sorted(results["status"].unique().tolist())
selected_status = st.sidebar.selectbox("Train status filter", status_options)
visible_results = results if selected_status == "ALL" else results[results["status"] == selected_status]
train_labels = {
    row["train_id"]: f'{row["train_id"]}  ·  {row["origin"]} → {row["destination"]}'
    for _, row in results.iterrows()
}
selected_train = st.sidebar.selectbox(
    "Train to dispatch",
    results["train_id"].tolist(),
    format_func=lambda train_id: train_labels[train_id],
)
selected = results[results["train_id"] == selected_train].iloc[0]
affected_trains = comparison[comparison["affected"] & (comparison["train_id"] != selected_train)]

st.markdown('<div class="eyebrow">RAILWAY NETWORK / OPERATIONS</div>', unsafe_allow_html=True)
st.title("Dispatch control room")
st.markdown('<div class="subtitle">A live read on route resilience, maintenance exposure, and train delay risk.</div>', unsafe_allow_html=True)

halted = int((results["status"] == "HALTED").sum())
detours = int((results["status"] == "DETOUR").sum())
average_delay = results["delay_penalty_min"].mean()

kpi_columns = st.columns(4)
with kpi_columns[0]: metric("Trains evaluated", len(results))
with kpi_columns[1]: metric("Active detours", detours, "warn")
with kpi_columns[2]: metric("Halted trains", halted, "alert")
with kpi_columns[3]: metric("Average delay", f"{average_delay:.1f} min")

st.markdown(
    f'<div class="mono">SCENARIO: {len(selected_maintenance_ids)} maintenance block(s) selected · '
    f'{len(affected_trains)} other train(s) affected</div>',
    unsafe_allow_html=True,
)

left, right = st.columns([1.9, 0.75], gap="medium")
with left:
    st.markdown('<h2 class="section-title">Network status</h2>', unsafe_allow_html=True)
    st.plotly_chart(
        network_figure(graph, blocked_edges, selected["final_path"]),
        use_container_width=True,
        config={"displayModeBar": False},
    )
with right:
    st.markdown('<h2 class="section-title">Maintenance watch</h2>', unsafe_allow_html=True)
    maintenance_view = selected_maintenance.merge(
        data["tracks"][["track_id", "section_id"]], on="track_id", how="left"
    )[["maintenance_id", "track_id", "section_id", "duration_hours"]]
    st.dataframe(maintenance_view, hide_index=True, use_container_width=True)
    st.markdown(f'<div class="mono">{len(blocked_edges)} section edges currently unavailable</div>', unsafe_allow_html=True)

st.markdown('<h2 class="section-title">Selected train dispatch</h2>', unsafe_allow_html=True)
dispatch_left, dispatch_right = st.columns([1, 1])
with dispatch_left:
    st.markdown(f'### {train_labels[selected_train]}  ·  {selected["status"]}')
    st.markdown(f'`{selected["origin"]} → {selected["destination"]}`')
    st.metric("Final delay penalty", f'{selected["delay_penalty_min"]:.1f} min')
with dispatch_right:
    st.markdown("**Generated route**")
    st.code(" -> ".join(selected["final_path"]) or "TRAIN HALTED", language="text")

st.markdown('<h2 class="section-title">Other trains affected</h2>', unsafe_allow_html=True)
if affected_trains.empty:
    st.success("No other trains are affected by this maintenance plan.")
else:
    affected_view = affected_trains.copy()
    affected_view["train"] = affected_view.apply(
        lambda row: f'{row["train_id"]}  ·  {row["origin"]} → {row["destination"]}',
        axis=1,
    )
    affected_view["delay_penalty_min"] = affected_view["delay_penalty_min"].round(1)
    affected_view = affected_view[["train", "status", "delay_penalty_min"]]
    affected_view.columns = ["Train / movement", "Status", "Delay penalty (min)"]
    st.dataframe(affected_view, hide_index=True, use_container_width=True)

st.markdown('<h2 class="section-title">Train movement board</h2>', unsafe_allow_html=True)
display = visible_results.copy()
display["train"] = display.apply(
    lambda row: f'{row["train_id"]}  ·  {row["origin"]} → {row["destination"]}',
    axis=1,
)
display["delay_penalty_min"] = display["delay_penalty_min"].round(1)
display = display[["train", "status", "original_time_min", "final_time_min", "delay_penalty_min"]]
display.columns = ["Train / movement", "Status", "Original (min)", "Final (min)", "Delay penalty (min)"]
st.dataframe(display, hide_index=True, use_container_width=True)

st.markdown('<h2 class="section-title">Route comparison</h2>', unsafe_allow_html=True)
detail_left, detail_right = st.columns(2)
with detail_left:
    st.markdown(f'**Original path**  \n`{" -> ".join(selected["original_path"]) or "No path"}`')
with detail_right:
    st.markdown(f'**Final dispatch path**  \n`{" -> ".join(selected["final_path"]) or "Train halted"}`')

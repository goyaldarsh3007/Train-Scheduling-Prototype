from pathlib import Path

import networkx as nx
import pandas as pd


def load_data(data_directory=None):
    """Load all tables required by the dispatch pipeline."""
    directory = Path(data_directory) if data_directory else Path(__file__).resolve().parent
    filenames = {
        "nodes": "nodes.csv",
        "sections": "sections.csv",
        "tracks": "tracks.csv",
        "maintenance_blocks": "maintenance_blocks.csv",
        "train_routes": "train_routes.csv",
    }

    try:
        return {
            name: pd.read_csv(directory / filename)
            for name, filename in filenames.items()
        }
    except FileNotFoundError as error:
        raise FileNotFoundError(
            f"Required CSV file was not found in {directory}: {error.filename}"
        ) from error


def build_network(nodes_df, sections_df):
    """Build an undirected network with travel time and section metadata."""
    graph = nx.Graph()

    for _, row in nodes_df.iterrows():
        graph.add_node(
            row["node_id"],
            node_type=row["node_type"],
            name=row["name"],
        )

    for _, row in sections_df.iterrows():
        graph.add_edge(
            row["node_1"],
            row["node_2"],
            time=row["travel_time_min"],
            section_id=row["section_id"],
            num_tracks=row["num_tracks"],
        )

    return graph


def get_blocked_edges(maintenance_blocks_df, tracks_df, sections_df):
    """Map maintained tracks to the endpoint pairs of their sections."""
    blocked_sections = maintenance_blocks_df.merge(
        tracks_df[["track_id", "section_id"]], on="track_id", how="inner"
    ).merge(
        sections_df[["section_id", "node_1", "node_2"]],
        on="section_id",
        how="inner",
    )

    return list(
        blocked_sections[["node_1", "node_2"]]
        .drop_duplicates()
        .itertuples(index=False, name=None)
    )


def _shortest_time(graph, origin, destination):
    """Return a shortest path and its travel time, or ``None`` if unreachable."""
    try:
        path = nx.shortest_path(
            graph, source=origin, target=destination, weight="time"
        )
        return path, nx.path_weight(graph, path, weight="time")
    except nx.NetworkXNoPath:
        return None


def evaluate_routes(
    graph,
    train_routes_df,
    blocked_edges,
    maintenance_blocks_df,
):
    """Evaluate every train against the network with all mapped blocks removed."""
    blocked_graph = graph.copy()
    blocked_graph.remove_edges_from(blocked_edges)
    maintenance_duration = maintenance_blocks_df["duration_hours"].sum() * 60
    results = []

    for _, route in train_routes_df.iterrows():
        train_id = route["train_id"]
        origin = route["origin"]
        destination = route["destination"]
        original = _shortest_time(graph, origin, destination)

        if original is None:
            results.append({
                "train_id": train_id,
                "origin": origin,
                "destination": destination,
                "status": "HALTED",
                "original_time_min": None,
                "final_time_min": None,
                "delay_penalty_min": maintenance_duration,
                "original_path": [],
                "final_path": [],
            })
            print(
                f"Train {train_id}: HALTED - no original path from "
                f"{origin} to {destination}."
            )
            continue

        original_path, original_time = original
        current = _shortest_time(blocked_graph, origin, destination)

        if current is None:
            results.append({
                "train_id": train_id,
                "origin": origin,
                "destination": destination,
                "status": "HALTED",
                "original_time_min": original_time,
                "final_time_min": None,
                "delay_penalty_min": maintenance_duration,
                "original_path": original_path,
                "final_path": [],
            })
            print(
                f"Train {train_id}: HALTED - no route remains after maintenance; "
                f"final delay penalty: {maintenance_duration:.1f} minutes."
            )
            continue

        current_path, current_time = current
        detour_penalty = current_time - original_time

        if current_path != original_path and detour_penalty < maintenance_duration:
            status = "DETOUR"
            print(
                f"Train {train_id}: DETOUR - {origin} -> {destination}; "
                f"original: {original_time:.1f} min, detour: {current_time:.1f} min, "
                f"final delay penalty: {detour_penalty:.1f} minutes."
            )
        elif current_path != original_path:
            status = "HALTED"
            print(
                f"Train {train_id}: HALTED - detour penalty ({detour_penalty:.1f} min) "
                f"exceeds maintenance duration ({maintenance_duration:.1f} min); "
                f"final delay penalty: {maintenance_duration:.1f} minutes."
            )
        else:
            status = "ON TIME"
            print(
                f"Train {train_id}: NO DETOUR - original route remains available; "
                f"final delay penalty: 0.0 minutes."
            )

        results.append({
            "train_id": train_id,
            "origin": origin,
            "destination": destination,
            "status": status,
            "original_time_min": original_time,
            "final_time_min": current_time,
            "delay_penalty_min": (
                detour_penalty if status == "DETOUR" else maintenance_duration
                if status == "HALTED" else 0
            ),
            "original_path": original_path,
            "final_path": current_path if status == "DETOUR" else original_path,
        })

    return pd.DataFrame(results)


if __name__ == "__main__":
    try:
        data = load_data()
        network = build_network(data["nodes"], data["sections"])
        blocked_edges = get_blocked_edges(
            data["maintenance_blocks"], data["tracks"], data["sections"]
        )

        print(f"Loaded {network.number_of_nodes()} nodes and {network.number_of_edges()} sections.")
        print(f"Mapped {len(blocked_edges)} blocked section edge(s).")
        evaluate_routes(
            network,
            data["train_routes"],
            blocked_edges,
            data["maintenance_blocks"],
        )
    except (FileNotFoundError, KeyError, ValueError) as error:
        print(f"Dispatch pipeline failed: {error}")
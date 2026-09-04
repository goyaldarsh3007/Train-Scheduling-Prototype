# Train Scheduling Prototype: Project Documentation

## 1. Purpose

This project is a railway dispatch and route-resilience prototype. It models a railway network as a graph, applies selected maintenance blocks, recalculates the shortest available route for every train, and presents the resulting operating scenario in a Streamlit dashboard.

The prototype is intended to answer questions such as:

- Which trains can keep their original route?
- Which trains need a detour because of maintenance?
- Which trains can no longer reach their destination?
- How much additional travel time does each affected train incur?
- Which maintenance blocks affect the largest number of trains?
- What route should be dispatched for a selected train?

It is a decision-support demonstration rather than a production railway signalling or timetable system.

## 2. Main capabilities

The application can:

- Load railway topology, track, maintenance, and train route data from CSV files.
- Build an undirected railway network from nodes and sections.
- Use section travel time as the routing cost.
- Select one or more maintenance blocks in the dashboard.
- Translate maintained track IDs into blocked network edges.
- Remove blocked edges from a copy of the network.
- Calculate baseline and post-maintenance shortest paths.
- Classify trains as `ON TIME`, `DETOUR`, or `HALTED`.
- Calculate route travel times and delay penalties in minutes.
- Highlight blocked sections and the selected train path on a Plotly network diagram.
- Show maintenance details, selected dispatch instructions, affected trains, and a movement board.
- Filter the movement board by train status.
- Select a different data directory from the dashboard sidebar.

## 3. Technology stack

| Component | Purpose |
| --- | --- |
| Python | Application and route-evaluation logic |
| pandas | CSV loading, joins, filtering, and tabular results |
| NetworkX | Graph construction and weighted shortest-path calculations |
| Streamlit | Interactive dashboard and controls |
| Plotly | Interactive railway network visualization |

The package requirements are listed in `requirements.txt`.

## 4. Application architecture

The project has two main Python modules:

### `Prototype_02.py`

This is the data and scheduling engine. It contains:

- `load_data()` - reads the required CSV tables.
- `build_network()` - converts nodes and sections into a NetworkX graph.
- `get_blocked_edges()` - maps maintenance track IDs to graph edges.
- `_shortest_time()` - finds a minimum-travel-time route.
- `evaluate_routes()` - evaluates every train under a maintenance scenario.

It can also be run directly from the command line to print a route evaluation summary.

### `dashboard.py`

This is the Streamlit user interface. It:

1. Loads the source data.
2. Builds the railway graph.
3. Lets the user select maintenance blocks.
4. Evaluates routes for the selected scenario.
5. Calculates an unblocked baseline for comparison.
6. Renders the network map, KPIs, dispatch route, affected trains, and tables.

The dashboard imports the scheduling engine rather than duplicating its routing logic.

## 5. Data model

### 5.1 Required execution files

These five files are loaded by `load_data()` and are required for the dashboard and route evaluator.

#### `nodes.csv`

Defines graph nodes.

| Column | Meaning |
| --- | --- |
| `node_id` | Unique node identifier, such as `N001` |
| `node_type` | Operational type, such as `STATION` or `JUNCTION` |
| `name` | Human-readable location name |

#### `sections.csv`

Defines graph edges between nodes.

| Column | Meaning |
| --- | --- |
| `section_id` | Unique section identifier |
| `node_1` | First endpoint node ID |
| `node_2` | Second endpoint node ID |
| `travel_time_min` | Routing cost for the section, in minutes |
| `num_tracks` | Track count used for display metadata |

Each row becomes an edge in an undirected NetworkX graph. The edge stores the section ID, travel time, and number of tracks.

#### `tracks.csv`

Maps individual tracks to sections.

| Column | Meaning |
| --- | --- |
| `track_id` | Unique track identifier, such as `TR001_01` |
| `section_id` | Section containing the track |
| `track_number` | Track number within the section |
| `track_type` | Track classification, such as `MAIN` or `LOOP` |

The current evaluator uses `track_id` and `section_id` to determine which section is affected by maintenance.

#### `maintenance_blocks.csv`

Defines work blocks that can be selected in the dashboard.

| Column | Meaning |
| --- | --- |
| `maintenance_id` | Unique maintenance block ID |
| `track_id` | Track closed by the block |
| `track_segment_id` | Segment associated with the work |
| `chainage_start_m` | Start position of the work, in metres |
| `chainage_end_m` | End position of the work, in metres |
| `planned_start` | Planned work start time |
| `planned_end` | Planned work end time |
| `duration_hours` | Duration used in the delay-penalty calculation |

The current logic maps the maintained track to its whole section. Chainage and clock times are displayed as source data but are not used to perform time-window conflict detection.

#### `train_routes.csv`

Defines the train movements that are evaluated.

| Column | Meaning |
| --- | --- |
| `route_id` | Unique route record ID |
| `train_id` | Train identifier |
| `origin` | Starting node ID |
| `destination` | Destination node ID |
| `section_path` | Source route description |

The current evaluator uses `train_id`, `origin`, and `destination`. It recalculates paths from the graph, so `section_path` is retained as source information but is not used as the routing result.

### 5.2 Supporting files

The repository also contains the following operational tables:

- `junctions.csv` - junction IDs and their node IDs.
- `track_connections.csv` - track-to-track connections and switch times.
- `track_segments.csv` - track segments and chainage ranges.
- `train_movements.csv` - train section movements and entry/exit times.
- `clean_railway_network.csv` - an additional consolidated network data source.

These files are not loaded by the current `load_data()` function. They are available for future timetable conflict, switch-time, segment-level, and movement-level modelling.

## 6. Route evaluation logic

### Step 1: Load data

`load_data(data_directory)` reads the five required CSV files with pandas. If a required file is missing, the function raises a descriptive `FileNotFoundError` identifying the data directory and missing file.

When no directory is supplied, the directory containing `Prototype_02.py` is used.

### Step 2: Build the graph

`build_network(nodes_df, sections_df)` creates a `networkx.Graph`:

- Every row in `nodes.csv` becomes a graph node.
- Every row in `sections.csv` becomes an undirected edge.
- `travel_time_min` is stored as the edge attribute `time`.
- `section_id` and `num_tracks` are stored as display and traceability metadata.

Because the graph is undirected, a section can be traversed in either direction and has the same travel time in both directions.

### Step 3: Map maintenance blocks to edges

`get_blocked_edges()` performs two joins:

1. Join maintenance blocks to tracks using `track_id`.
2. Join the result to sections using `section_id`.

The endpoint pair `(node_1, node_2)` is then returned for each affected section. Duplicate endpoint pairs are removed.

This means that closing any track mapped to a section makes the entire graph edge unavailable. The current model does not preserve remaining capacity when a multi-track section has only one track under maintenance.

### Step 4: Calculate the baseline route

For each train, `_shortest_time()` calls NetworkX weighted shortest-path logic using the graph edge attribute `time`.

The baseline route is calculated on the unblocked graph. Its result contains:

- The ordered node path.
- The sum of `travel_time_min` values along that path.

If no baseline path exists, the train is marked `HALTED` immediately.

### Step 5: Calculate the post-maintenance route

The evaluator copies the original graph and removes all blocked edges from the copy. It then calculates a shortest route between the same origin and destination.

If no route remains, the train is marked `HALTED` and receives the total selected maintenance duration as its delay penalty.

### Step 6: Classify the train

For a train with an available baseline and post-maintenance route:

```text
detour_penalty = post_maintenance_time - baseline_time
```

The status rules are:

| Condition | Status | Interpretation |
| --- | --- | --- |
| Final path equals original path | `ON TIME` | Maintenance does not change the selected route |
| Final path changes and detour penalty is less than total maintenance duration | `DETOUR` | A viable alternate route is preferred |
| Final path changes and detour penalty is greater than or equal to total maintenance duration | `HALTED` | The detour is treated as worse than waiting for maintenance |
| No final path exists | `HALTED` | The destination cannot be reached |

The returned result includes the original path, final path, original travel time, final travel time, status, and delay penalty.

### Delay penalty rules

- `ON TIME`: `0` minutes.
- `DETOUR`: the additional travel time caused by the detour.
- `HALTED`: the sum of selected maintenance durations converted from hours to minutes.

This is a simplified business rule. It does not model the train's scheduled departure time, the maintenance start and end clock times, queues, platform capacity, train priorities, or interactions between trains.

## 7. Dashboard behavior

### Sidebar controls

The sidebar provides:

- A data directory input.
- A multi-select list of maintenance blocks.
- A status filter for the train movement board.
- A train selector for dispatch inspection.

All maintenance blocks are selected by default.

### KPI cards

The dashboard calculates and displays:

- Number of trains evaluated.
- Number of active detours.
- Number of halted trains.
- Average delay penalty across all evaluated trains.

### Network status map

The Plotly diagram displays:

- Railway nodes with location names and node IDs.
- Sections with width based on `num_tracks`.
- Blocked sections in red.
- The selected train's final route in green.
- Section hover details including section ID, track count, and travel time.

The node coordinates are manually defined schematic positions for the sample network. They are not read from geographic coordinate data.

### Maintenance watch

The maintenance table shows selected maintenance IDs, track IDs, mapped section IDs, and durations. It also reports the number of currently unavailable graph edges.

### Selected train dispatch

The selected train panel shows:

- Train ID, origin, destination, and status.
- Final delay penalty.
- Generated node route, or `TRAIN HALTED` if there is no route.

### Other affected trains

The dashboard compares the maintenance scenario against a baseline scenario with no maintenance selected. A train is considered affected if its status is not `ON TIME` or its final path differs from the baseline path.

### Train movement board and route comparison

The movement board shows original and final travel times and delay penalties, with optional status filtering. The route comparison shows the original path and the final dispatch path for the selected train.

## 8. Running the project

From the repository directory:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m streamlit run dashboard.py
```

Open the local URL printed by Streamlit, normally:

```text
http://localhost:8501
```

### Running the engine without Streamlit

The core evaluator can also be run directly:

```powershell
python Prototype_02.py
```

This loads the default CSV files, builds the network, maps all maintenance blocks, and prints route evaluation messages to the terminal.

## 9. Typical workflow

1. Install the Python dependencies.
2. Start the Streamlit dashboard.
3. Confirm that the data directory points to the repository folder.
4. Select or clear maintenance blocks.
5. Review the KPI cards and red blocked sections.
6. Filter the movement board by status.
7. Select a train to inspect its generated route and delay penalty.
8. Compare the original and final paths before using the scenario for planning discussion.

## 10. Validation and error handling

The dashboard catches `FileNotFoundError`, `KeyError`, and `ValueError` while loading and evaluating data, then displays an error in the Streamlit page and stops rendering.

The command-line engine catches the same error types and prints a failure message.

The current code does not validate every CSV relationship before routing. For reliable results, IDs should be consistent across files:

- `maintenance_blocks.track_id` must exist in `tracks.track_id`.
- `tracks.section_id` must exist in `sections.section_id`.
- `sections.node_1` and `sections.node_2` must exist in `nodes.node_id`.
- `train_routes.origin` and `train_routes.destination` must exist in `nodes.node_id`.

## 11. Important assumptions and limitations

This prototype intentionally simplifies railway operations:

- The network is undirected.
- Routing cost is only section travel time.
- Maintenance blocks remove whole section edges.
- Track capacity and remaining parallel tracks are not modelled.
- Maintenance start and end times are not used for time-dependent routing.
- Train departure times and timetable conflicts are not used.
- Switch times in `track_connections.csv` are not included in route cost.
- Train movement history is not used to prevent collisions or reserve capacity.
- The provided `section_path` is not treated as a fixed schedule; paths are recalculated from origin and destination.
- A detour that takes at least as long as the total maintenance duration is classified as `HALTED` by the prototype's decision rule.
- The dashboard uses hand-authored schematic coordinates rather than geographic mapping.
- The Streamlit cache keys data by the data directory and selected maintenance IDs; changes to CSV contents may require a rerun or cache refresh during development.

## 12. Extension opportunities

The project can be extended in several directions:

### More realistic infrastructure modelling

- Represent individual tracks as parallel edges instead of removing an entire section.
- Use `track_segments.csv` and chainage ranges for partial closures.
- Include junction switch times in path cost.
- Add directionality, speed limits, platform constraints, and line capacity.

### Time-dependent scheduling

- Use planned maintenance windows and train entry times.
- Determine whether a train reaches a work zone while it is closed.
- Add waiting, holding, and rescheduling decisions.
- Account for interactions among trains competing for the same route.

### Better dispatch optimization

- Add train priorities and service-level constraints.
- Compare multiple candidate routes instead of only the shortest route.
- Optimize the maintenance plan for minimum total delay.
- Produce a dispatch timetable rather than only a route classification.

### Data quality and testing

- Add schema validation for all CSV files.
- Add automated unit tests for graph construction, edge blocking, unreachable routes, and status classification.
- Add scenario fixtures for no maintenance, single-section closure, and network partition cases.
- Add a formal geographic coordinate source for the network map.

## 13. Repository files

| File | Role |
| --- | --- |
| `dashboard.py` | Streamlit dashboard and Plotly visualizations |
| `Prototype_02.py` | Core data loading, graph, blocking, and routing logic |
| `README.md` | Short setup and usage guide |
| `PROJECT_DOCUMENTATION.md` | Detailed implementation and operations guide |
| `requirements.txt` | Python dependencies |
| `nodes.csv` | Network nodes |
| `sections.csv` | Network sections and travel times |
| `tracks.csv` | Tracks mapped to sections |
| `maintenance_blocks.csv` | Maintenance scenarios |
| `train_routes.csv` | Train origin and destination inputs |
| `junctions.csv` | Supporting junction reference data |
| `track_connections.csv` | Supporting switch connection data |
| `track_segments.csv` | Supporting chainage data |
| `train_movements.csv` | Supporting movement timing data |
| `clean_railway_network.csv` | Supporting consolidated network data |
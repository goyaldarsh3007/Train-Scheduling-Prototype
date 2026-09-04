# Train Scheduling Prototype

A Streamlit dashboard for exploring railway dispatch routes and evaluating the effect of maintenance blocks on train journeys.

## Features

- Builds a railway network from node and section data.
- Calculates shortest travel-time routes for scheduled trains.
- Simulates maintenance blocks by removing affected track sections.
- Identifies delayed, rerouted, and unreachable trains.
- Displays the network, route results, maintenance impact, and dispatch details in an interactive dashboard.

## Requirements

- Python 3.9 or newer
- The packages listed in `requirements.txt`

## Installation

From the repository directory, create and activate a virtual environment if desired, then install the dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

## Run the dashboard

```powershell
python -m streamlit run dashboard.py
```

Streamlit will display a local URL, normally `http://localhost:8501`.

## Project structure

- `dashboard.py` - Streamlit user interface and visualizations.
- `Prototype_02.py` - Network construction, data loading, maintenance blocking, and route evaluation logic.
- `requirements.txt` - Python dependencies.
- `nodes.csv`, `sections.csv`, and `tracks.csv` - Railway network data.
- `maintenance_blocks.csv` - Maintenance work used in simulations.
- `train_routes.csv` - Train origins, destinations, and route inputs.
- Other CSV files - Supporting railway and movement data.

The dashboard expects the required CSV files to be in the same directory as the Python files by default. A different data directory can be selected in the sidebar.
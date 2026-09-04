import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt
import time
import random

# ==========================================
# 1. SYNTHETIC DATA GENERATION
# ==========================================
def generate_synthetic_data():
    nodes = pd.DataFrame([
        {'node_id': 'Ludhiana',   'type': 'station'},
        {'node_id': 'Sirhind',    'type': 'junction'},
        {'node_id': 'Rajpura',    'type': 'junction'},
        {'node_id': 'Chandigarh', 'type': 'station'},
        {'node_id': 'Ambala',     'type': 'station'},
        {'node_id': 'Patiala',    'type': 'station'}
    ])

    tracks = pd.DataFrame([
        {'node_1': 'Ludhiana', 'node_2': 'Sirhind',    'time': 40},
        {'node_1': 'Sirhind',  'node_2': 'Chandigarh', 'time': 45}, 
        {'node_1': 'Sirhind',  'node_2': 'Rajpura',    'time': 20},
        {'node_1': 'Rajpura',  'node_2': 'Chandigarh', 'time': 35},
        {'node_1': 'Rajpura',  'node_2': 'Ambala',     'time': 25},
        {'node_1': 'Sirhind',  'node_2': 'Patiala',    'time': 30},
        {'node_1': 'Patiala',  'node_2': 'Rajpura',    'time': 25},
        {'node_1': 'Ludhiana', 'node_2': 'Patiala',    'time': 50}
    ])
    return nodes, tracks

# ==========================================
# 2. THE SMART ROUTING ALGORITHM
# ==========================================
def smart_route_train(G, start, end, blocked_edges, halt_penalty_mins):
    print(f"\n🧠 AI DISPATCHER: Evaluating route {start} -> {end}")
    
    try:
        original_path = nx.shortest_path(G, source=start, target=end, weight='time')
        original_time = nx.path_weight(G, original_path, weight='time')
        print(f"   🛤️ Original Plan: {' -> '.join(original_path)} ({original_time} mins)")
    except nx.NetworkXNoPath:
        print(f"   ❌ No valid original path exists.")
        return None, None

    G_active = G.copy()
    for u, v in blocked_edges:
        if G_active.has_edge(u, v):
            G_active.remove_edge(u, v)

    try:
        detour_path = nx.shortest_path(G_active, source=start, target=end, weight='time')
        detour_time = nx.path_weight(G_active, detour_path, weight='time')
        detour_penalty = detour_time - original_time
        
        if detour_penalty < halt_penalty_mins:
            print(f"   ✅ DECISION: Detour is faster (+{detour_penalty} mins) than waiting (+{halt_penalty_mins} mins).")
            print(f"   🔄 New Route: {' -> '.join(detour_path)}\n")
            return original_path, detour_path
        else:
            print(f"   🛑 DECISION: Detour takes too long (+{detour_penalty} mins). Train will HALT.\n")
            return original_path, original_path # Halt means we stick to original path but delayed
            
    except nx.NetworkXNoPath:
        print(f"   ❌ DECISION: No detour exists. Train must HALT.\n")
        return original_path, original_path

# ==========================================
# 3. LIVE SLIDING WINDOW SIMULATOR
# ==========================================
def simulate_sliding_window(G, path, train_name="Express-101"):
    print(f"⏱️ STARTING LIVE SLIDING WINDOW SIMULATION FOR {train_name}...\n")
    current_time = 0
    
    for i in range(len(path) - 1):
        current_node = path[i]
        next_node = path[i+1]
        travel_time = G[current_node][next_node]['time']
        
        # 1. LOCK the track ahead
        print(f"[{current_time:03d}m] 🔒 {current_node}: LOCKED track to {next_node}. Train entering...")
        
        # Simulate time passing
        time.sleep(1.5) 
        current_time += travel_time
        
        # 2. RELEASE the track behind
        print(f"[{current_time:03d}m] 🔓 {next_node}: RELEASED track from {current_node}. Free for next train.")
        print("-" * 60)
        
    print(f"🏁 {train_name} successfully arrived at {path[-1]} at t={current_time}m.")

# ==========================================
# 4. SIDE-BY-SIDE VISUALIZATION
# ==========================================
def visualize_side_by_side(G, original_path, detour_path, blocked_edges):
    pos = nx.spring_layout(G, seed=10) 
    
    # Create a 1-row, 2-column figure layout
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
    fig.canvas.manager.set_window_title('AI Railway Dispatcher Prototype')
    
    # --- LEFT MAP: Original Route ---
    nx.draw_networkx_edges(G, pos, ax=ax1, edge_color='lightgrey', width=2)
    nx.draw_networkx_nodes(G, pos, ax=ax1, node_color='lightblue', node_size=700)
    nx.draw_networkx_labels(G, pos, ax=ax1, font_size=10, font_weight='bold')
    nx.draw_networkx_edge_labels(G, pos, ax=ax1, edge_labels=nx.get_edge_attributes(G, 'time'))
    
    if original_path:
        orig_edges = [(original_path[i], original_path[i+1]) for i in range(len(original_path)-1)]
        nx.draw_networkx_edges(G, pos, ax=ax1, edgelist=orig_edges, edge_color='blue', width=4, label='Original Route')
    
    ax1.set_title("Original Schedule (No Maintenance)", fontsize=14)
    ax1.legend(loc="upper right")
    ax1.axis('off')

    # --- RIGHT MAP: Detour & Crisis ---
    nx.draw_networkx_edges(G, pos, ax=ax2, edge_color='lightgrey', width=2)
    nx.draw_networkx_nodes(G, pos, ax=ax2, node_color='lightblue', node_size=700)
    nx.draw_networkx_labels(G, pos, ax=ax2, font_size=10, font_weight='bold')
    nx.draw_networkx_edge_labels(G, pos, ax=ax2, edge_labels=nx.get_edge_attributes(G, 'time'))

    # Draw the block in red
    nx.draw_networkx_edges(G, pos, ax=ax2, edgelist=blocked_edges, edge_color='red', width=4, style='dashed', label='Maintenance Block')
    
    # Draw the detour in green
    if detour_path and detour_path != original_path:
        detour_edges = [(detour_path[i], detour_path[i+1]) for i in range(len(detour_path)-1)]
        nx.draw_networkx_edges(G, pos, ax=ax2, edgelist=detour_edges, edge_color='green', width=4, label='AI Detour Route')
    elif detour_path == original_path:
        # If it halted, draw original path but note the halt
        ax2.text(0.5, 0.05, "TRAIN HALTED - NO DETOUR TAKEN", transform=ax2.transAxes, ha='center', color='red', fontsize=12, fontweight='bold')
        
    ax2.set_title("Dynamic AI Rerouting (With Maintenance)", fontsize=14)
    ax2.legend(loc="upper right")
    ax2.axis('off')

    # This draws the plot but allows the script to continue running the console simulation
    plt.draw()
    plt.pause(0.1)

# ==========================================
# 5. INTERACTIVE CLI MENU
# ==========================================
def interactive_demo():
    nodes_df, tracks_df = generate_synthetic_data()
    G = nx.Graph()
    for _, row in tracks_df.iterrows():
        G.add_edge(row['node_1'], row['node_2'], time=row['time'])

    nodes_list = list(G.nodes())
    edges_list = list(G.edges())

    print("=" * 60)
    print("🚂 WELCOME TO THE DYNAMIC ROUTING ENGINE PROTOTYPE")
    print("=" * 60)
    
    start_node = input("\nEnter START station (or press Enter for 'Ludhiana'): ").strip()
    if not start_node or start_node not in nodes_list: start_node = 'Ludhiana'

    end_node = input("Enter DESTINATION station (or press Enter for 'Chandigarh'): ").strip()
    if not end_node or end_node not in nodes_list: end_node = 'Chandigarh'

    print("\nAvailable Tracks to Block:")
    for i, (u, v) in enumerate(edges_list):
        print(f"  {i}: {u} <--> {v}")
    
    block_idx = input("\nEnter the NUMBER of the track to put under maintenance (or press Enter for Random): ").strip()
    if block_idx.isdigit() and int(block_idx) < len(edges_list):
        blocked_track = edges_list[int(block_idx)]
    else:
        blocked_track = random.choice(edges_list)
        
    maintenance = [blocked_track]
    halt_penalty = int(input("Enter maintenance duration in minutes (e.g., 240): ") or "240")

    print("\n" + "=" * 60)
    print(f"🚨 ALERT: {halt_penalty}-minute maintenance block scheduled on {blocked_track[0]} <--> {blocked_track[1]}")
    print("=" * 60)

    # Calculate routes
    original_path, detour_path = smart_route_train(G, start_node, end_node, maintenance, halt_penalty)
    
    if detour_path:
        # Show side-by-side map (non-blocking)
        visualize_side_by_side(G, original_path, detour_path, maintenance)
        
        # Run console simulation
        simulate_sliding_window(G, detour_path)
    
    # This keeps the plot window open until you close it manually or press Enter in the console
    input("\n✅ Simulation complete! Check the Matplotlib window. Press Enter here to exit...")
    plt.close('all')

if __name__ == "__main__":
    interactive_demo()
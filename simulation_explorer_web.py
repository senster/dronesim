#!/usr/bin/env python3
"""
Simulation Explorer Web - A web-based tool for exploring drone simulation outputs.

This tool allows users to browse, filter, and view simulation results based on
various parameters such as drone type, seed, strategy, and more.
"""
import os
import re
import json
from flask import Flask, render_template, request, send_from_directory, jsonify
from werkzeug.serving import run_simple
import webbrowser
import threading
import time

app = Flask(__name__, template_folder=os.path.dirname(os.path.abspath(__file__)))

# Global variables
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
SIMULATION_FILES = []
DRONE_TYPES = set()
SEEDS = set()
STRATEGIES = set()

def load_simulations():
    """Load simulation files from the output directory."""
    global SIMULATION_FILES, DRONE_TYPES, SEEDS, STRATEGIES
    
    # Check if output directory exists
    if not os.path.exists(OUTPUT_DIR):
        return []
    
    # Get all GIF files in the output directory
    SIMULATION_FILES = [f for f in os.listdir(OUTPUT_DIR) 
                        if f.endswith('.gif') and f.startswith('simulation_')]
    
    # Extract filter values
    DRONE_TYPES = set()
    SEEDS = set()
    STRATEGIES = set()
    
    for filename in SIMULATION_FILES:
        # Extract drone type
        match = re.search(r'simulation_(\w+)', filename)
        if match:
            DRONE_TYPES.add(match.group(1))
        
        # Extract seed
        match = re.search(r'seed(\d+)', filename)
        if match:
            SEEDS.add(match.group(1))
        
        # Extract strategy
        match = re.search(r'_([^_]+)_H', filename)
        if match:
            STRATEGIES.add(match.group(1).replace('_', ' '))
    
    return SIMULATION_FILES

def extract_simulation_info(filename):
    """Extract and format information from the simulation filename."""
    info = {}
    
    # Extract drone type
    match = re.search(r'simulation_(\w+)', filename)
    if match:
        info['drone_type'] = match.group(1)
    
    # Extract seed
    match = re.search(r'seed(\d+)', filename)
    if match:
        info['seed'] = match.group(1)
    
    # Extract strategy (if lawnmower)
    if "lawnmower" in filename:
        match = re.search(r'_([^_]+)_H', filename)
        if match:
            info['strategy'] = match.group(1).replace('_', ' ')
        
        # Extract H and V values
        match = re.search(r'H(\d+\.\d+)_V(\d+\.\d+)', filename)
        if match:
            info['h_value'] = match.group(1)
            info['v_value'] = match.group(2)
    
    # Extract timestamp
    match = re.search(r'(\d{8}_\d{6})\.gif', filename)
    if match:
        timestamp = match.group(1)
        # Format: YYYYMMDD_HHMMSS
        formatted_time = f"{timestamp[0:4]}-{timestamp[4:6]}-{timestamp[6:8]} {timestamp[9:11]}:{timestamp[11:13]}:{timestamp[13:15]}"
        info['timestamp'] = formatted_time
    
    return info

def filter_simulations(drone_type="All", seed="All", strategy="All"):
    """Filter simulations based on selected criteria."""
    filtered_files = []
    
    for filename in SIMULATION_FILES:
        # Check drone type filter
        if drone_type != "All":
            if drone_type not in filename:
                continue
        
        # Check seed filter
        if seed != "All":
            if f"seed{seed}" not in filename:
                continue
        
        # Check strategy filter
        if strategy != "All":
            # Only apply to lawnmower simulations
            if "lawnmower" in filename:
                strategy_pattern = f"_{strategy.replace(' ', '_')}_"
                if strategy_pattern not in filename:
                    continue
            elif "lawnmower" not in filename and strategy != "All":
                # Skip non-lawnmower simulations when strategy filter is active
                continue
        
        filtered_files.append(filename)
    
    return filtered_files

@app.route('/')
def index():
    """Render the main page."""
    # Load simulations
    load_simulations()
    
    # Prepare options for dropdowns
    drone_type_options = ["All"] + sorted(list(DRONE_TYPES))
    seed_options = ["All"] + sorted(list(SEEDS), key=lambda x: int(x))
    strategy_options = ["All"] + sorted(list(STRATEGIES))
    
    # Return HTML template
    return get_html_template(drone_type_options, seed_options, strategy_options)

@app.route('/api/simulations')
def get_simulations():
    """Get filtered simulations."""
    # Get filter parameters
    drone_type = request.args.get('drone_type', 'All')
    seed = request.args.get('seed', 'All')
    strategy = request.args.get('strategy', 'All')
    
    # Filter simulations
    filtered_files = filter_simulations(drone_type, seed, strategy)
    
    # Prepare response
    simulations = []
    for filename in filtered_files:
        info = extract_simulation_info(filename)
        info['filename'] = filename
        simulations.append(info)
    
    # Sort by timestamp (newest first)
    simulations.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
    
    return jsonify(simulations)

@app.route('/simulation/<path:filename>')
def get_simulation(filename):
    """Get a specific simulation file."""
    return send_from_directory(OUTPUT_DIR, filename)

def get_html_template(drone_type_options, seed_options, strategy_options):
    """Generate the HTML template with the provided options."""
    
    # Generate options HTML
    drone_type_html = ''
    for option in drone_type_options:
        drone_type_html += f'<option value="{option}">{option}</option>'
    
    seed_html = ''
    for option in seed_options:
        seed_html += f'<option value="{option}">{option}</option>'
    
    strategy_html = ''
    for option in strategy_options:
        strategy_html += f'<option value="{option}">{option}</option>'
    
    html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Simulation Explorer</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            display: flex;
            max-width: 1200px;
            margin: 0 auto;
            background-color: white;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
            overflow: hidden;
        }}
        .sidebar {{
            width: 300px;
            padding: 20px;
            border-right: 1px solid #eee;
            background-color: #f9f9f9;
        }}
        .content {{
            flex: 1;
            padding: 20px;
        }}
        h1 {{
            margin-top: 0;
            color: #333;
        }}
        .filter-group {{
            margin-bottom: 15px;
        }}
        label {{
            display: block;
            margin-bottom: 5px;
            font-weight: bold;
        }}
        select {{
            width: 100%;
            padding: 8px;
            border: 1px solid #ddd;
            border-radius: 4px;
            margin-bottom: 10px;
        }}
        button {{
            background-color: #4CAF50;
            color: white;
            border: none;
            padding: 10px 15px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 14px;
            margin-top: 10px;
        }}
        button:hover {{
            background-color: #45a049;
        }}
        .simulation-list {{
            max-height: 400px;
            overflow-y: auto;
            border: 1px solid #eee;
            border-radius: 4px;
            margin-top: 15px;
        }}
        .simulation-item {{
            padding: 10px;
            border-bottom: 1px solid #eee;
            cursor: pointer;
        }}
        .simulation-item:hover {{
            background-color: #f0f0f0;
        }}
        .simulation-item.selected {{
            background-color: #e0f7fa;
        }}
        .info-panel {{
            margin-bottom: 20px;
            padding: 15px;
            background-color: #f9f9f9;
            border-radius: 4px;
        }}
        .viewer {{
            text-align: center;
        }}
        .simulation-gif {{
            max-width: 100%;
            border: 1px solid #ddd;
            border-radius: 4px;
            display: none;
        }}
        .controls {{
            margin-top: 15px;
            display: flex;
            justify-content: center;
            align-items: center;
        }}
        .speed-control {{
            display: flex;
            align-items: center;
            margin-left: 15px;
        }}
        .speed-control label {{
            margin: 0 5px 0 0;
        }}
        .no-simulations {{
            padding: 20px;
            text-align: center;
            color: #666;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="sidebar">
            <h1>Simulation Explorer</h1>
            
            <div class="filter-group">
                <label for="drone-type">Drone Type:</label>
                <select id="drone-type">
                    {drone_type_html}
                </select>
                
                <label for="seed">Seed:</label>
                <select id="seed">
                    {seed_html}
                </select>
                
                <label for="strategy">Strategy:</label>
                <select id="strategy">
                    {strategy_html}
                </select>
                
                <button id="apply-filters">Apply Filters</button>
                <button id="reset-filters">Reset Filters</button>
            </div>
            
            <h2>Simulations</h2>
            <div class="simulation-list" id="simulation-list">
                <div class="no-simulations">No simulations found</div>
            </div>
            
            <button id="refresh-button">Refresh Simulations</button>
        </div>
        
        <div class="content">
            <div class="info-panel" id="info-panel">
                Select a simulation to view details
            </div>
            
            <div class="viewer" id="viewer">
                <img id="simulation-gif" class="simulation-gif" src="" alt="Simulation">
                
                <div class="controls">
                    <button id="play-button">Play</button>
                    
                    <div class="speed-control">
                        <label for="speed">Speed:</label>
                        <input type="range" id="speed" min="0.25" max="3" step="0.25" value="1">
                        <span id="speed-value">1x</span>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        // Global variables
        let simulations = [];
        let selectedSimulation = null;
        let isPlaying = false;
        let gifPlayer = null;
        
        // DOM elements
        const droneTypeSelect = document.getElementById('drone-type');
        const seedSelect = document.getElementById('seed');
        const strategySelect = document.getElementById('strategy');
        const applyFiltersButton = document.getElementById('apply-filters');
        const resetFiltersButton = document.getElementById('reset-filters');
        const simulationList = document.getElementById('simulation-list');
        const infoPanel = document.getElementById('info-panel');
        const simulationGif = document.getElementById('simulation-gif');
        const playButton = document.getElementById('play-button');
        const speedSlider = document.getElementById('speed');
        const speedValue = document.getElementById('speed-value');
        const refreshButton = document.getElementById('refresh-button');
        
        // Event listeners
        applyFiltersButton.addEventListener('click', loadSimulations);
        resetFiltersButton.addEventListener('click', resetFilters);
        playButton.addEventListener('click', togglePlay);
        speedSlider.addEventListener('input', updateSpeed);
        refreshButton.addEventListener('click', () => {{
            window.location.reload();
        }});
        
        // Load simulations on page load
        loadSimulations();
        
        // Functions
        function loadSimulations() {{
            const droneType = droneTypeSelect.value;
            const seed = seedSelect.value;
            const strategy = strategySelect.value;
            
            fetch(`/api/simulations?drone_type=${{droneType}}&seed=${{seed}}&strategy=${{strategy}}`)
                .then(response => response.json())
                .then(data => {{
                    simulations = data;
                    updateSimulationList();
                }})
                .catch(error => {{
                    console.error('Error loading simulations:', error);
                    simulationList.innerHTML = '<div class="no-simulations">Error loading simulations</div>';
                }});
        }}
        
        function updateSimulationList() {{
            if (simulations.length === 0) {{
                simulationList.innerHTML = '<div class="no-simulations">No simulations found</div>';
                return;
            }}
            
            simulationList.innerHTML = '';
            
            simulations.forEach(simulation => {{
                const item = document.createElement('div');
                item.className = 'simulation-item';
                item.textContent = simulation.filename;
                item.dataset.filename = simulation.filename;
                
                item.addEventListener('click', () => {{
                    selectSimulation(simulation);
                    
                    // Remove selected class from all items
                    document.querySelectorAll('.simulation-item').forEach(el => {{
                        el.classList.remove('selected');
                    }});
                    
                    // Add selected class to clicked item
                    item.classList.add('selected');
                }});
                
                simulationList.appendChild(item);
            }});
        }}
        
        function selectSimulation(simulation) {{
            selectedSimulation = simulation;
            
            // Stop any playing animation
            stopAnimation();
            
            // Update info panel
            let info = '<strong>Simulation Details:</strong><br>';
            info += `<strong>Drone Type:</strong> ${{simulation.drone_type || 'N/A'}}<br>`;
            info += `<strong>Seed:</strong> ${{simulation.seed || 'N/A'}}<br>`;
            
            if (simulation.strategy) {{
                info += `<strong>Strategy:</strong> ${{simulation.strategy}}<br>`;
            }}
            
            if (simulation.h_value && simulation.v_value) {{
                info += `<strong>H:</strong> ${{simulation.h_value}}, <strong>V:</strong> ${{simulation.v_value}}<br>`;
            }}
            
            if (simulation.timestamp) {{
                info += `<strong>Date:</strong> ${{simulation.timestamp}}<br>`;
            }}
            
            infoPanel.innerHTML = info;
            
            // Load the GIF
            simulationGif.src = `/simulation/${{simulation.filename}}`;
            simulationGif.style.display = 'block';
        }}
        
        function resetFilters() {{
            droneTypeSelect.value = 'All';
            seedSelect.value = 'All';
            strategySelect.value = 'All';
            loadSimulations();
        }}
        
        function togglePlay() {{
            if (!selectedSimulation) return;
            
            if (isPlaying) {{
                stopAnimation();
            }} else {{
                startAnimation();
            }}
        }}
        
        function startAnimation() {{
            isPlaying = true;
            playButton.textContent = 'Pause';
            
            // Force reload the GIF to restart animation
            const src = simulationGif.src;
            simulationGif.src = '';
            simulationGif.src = src;
        }}
        
        function stopAnimation() {{
            isPlaying = false;
            playButton.textContent = 'Play';
            
            // Pause animation by replacing with a static image
            // This is a hack since GIFs can't be easily paused
            if (selectedSimulation) {{
                // We could implement a more sophisticated pause mechanism
                // but for simplicity, we'll just rely on the browser's behavior
            }}
        }}
        
        function updateSpeed() {{
            const speed = speedSlider.value;
            speedValue.textContent = `${{speed}}x`;
            
            // Adjust animation speed
            // Note: Controlling GIF animation speed is challenging in browsers
            // This is a limitation of the web-based approach
        }}
    </script>
</body>
</html>
"""
    return html

def open_browser():
    """Open the browser after a short delay."""
    time.sleep(1)
    webbrowser.open('http://localhost:5000')

def main():
    """Main function to start the application."""
    # Start browser in a separate thread
    threading.Thread(target=open_browser).start()
    
    # Start Flask server
    run_simple('localhost', 5000, app, use_reloader=False)

if __name__ == "__main__":
    main()

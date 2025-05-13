#!/usr/bin/env python3
"""
Simulation Explorer Web - A web-based tool for exploring drone simulation outputs.

This tool allows users to browse, filter, and view simulation results based on
various parameters such as drone type, seed, strategy, and more.
"""
import os
import re
import json
import sys
import subprocess
import datetime
import random
from flask import Flask, render_template, request, send_from_directory, jsonify, redirect, url_for
from werkzeug.serving import run_simple
import webbrowser
import threading
import time

# Import simulation components
from ocean_map import OceanMap
from lawnmower_drone import LawnmowerDrone
from circular_drone import CircularDrone
from ai_drone import AIDrone
from catching_system import CatchingSystem
from simulation_engine import SimulationEngine
from visualization import SimulationVisualizer
from strategy_manager import StrategyManager

# Create a Flask application with static file configuration
app = Flask(__name__, static_folder='static', static_url_path='/static', template_folder=os.path.dirname(os.path.abspath(__file__)))

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



# Global variable to track simulation progress
SIMULATION_PROGRESS = {"current_step": 0, "total_steps": 0}

@app.route('/api/progress')
def get_progress():
    """Get the current simulation progress."""
    return jsonify(SIMULATION_PROGRESS)

# Custom progress callback function
def progress_callback(step, total_steps):
    """Update the simulation progress."""
    global SIMULATION_PROGRESS
    SIMULATION_PROGRESS["current_step"] = step
    SIMULATION_PROGRESS["total_steps"] = total_steps

@app.route('/api/run_simulation', methods=['POST'])
def run_simulation():
    """Run a new simulation with the provided parameters."""
    global SIMULATION_PROGRESS
    
    # Reset progress
    SIMULATION_PROGRESS = {"current_step": 0, "total_steps": 0}
    
    # Get simulation parameters
    pattern = request.form.get('pattern', 'lawnmower')
    strategy = request.form.get('strategy', None)
    seed = request.form.get('seed', None)
    num_drones = int(request.form.get('num_drones', 4))
    steps = int(request.form.get('steps', 200))
    
    # Set total steps for progress tracking
    SIMULATION_PROGRESS["total_steps"] = steps
    
    # Convert empty seed to None or int
    if seed and seed.strip():
        seed = int(seed)
    else:
        seed = None
    
    # Create output directory if it doesn't exist
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Run the simulation based on the pattern
    result = {}
    
    try:
        # Monkey patch the SimulationEngine.step method to track progress
        original_step = SimulationEngine.step
        
        def step_with_progress(self):
            stats = original_step(self)
            progress_callback(self.current_step, SIMULATION_PROGRESS["total_steps"])
            return stats
        
        # For debugging
        print(f"Running simulation with pattern={pattern}, strategy={strategy}, seed={seed}, num_drones={num_drones}, steps={steps}")
        
        # Prepare the command to run run_simulation.py
        python_executable = sys.executable
        zarr_path = "pset/36_Particles.zarr"  # Default zarr file path
        
        # Build the command based on the pattern
        command = [python_executable, "run_simulation.py"]
        
        # Add pattern-specific arguments
        if pattern == "circular":
            command.extend(["--pattern", "circular", "--steps", str(steps)])
        elif pattern == "ai":
            command.extend(["--pattern", "ai", "--num-drones", str(num_drones), "--steps", str(steps)])
        else:  # lawnmower
            command.extend(["--pattern", "lawnmower", "--steps", str(steps)])
            if strategy:
                command.extend(["--strategy", strategy])
        
        # Add seed if provided
        if seed is not None:
            command.extend(["--seed", str(seed)])
            
        # Add output directory
        command.extend(["--output", OUTPUT_DIR])
        
        # Add zarr path
        command.extend(["--zarr", zarr_path])
        
        print(f"Running command: {' '.join(command)}")
        
        try:
            # Run the command
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            
            # Monitor the process and update progress
            # This is a simple implementation - in a real app, you'd parse the output for progress info
            while process.poll() is None:
                # Update progress (simulated here)
                SIMULATION_PROGRESS["current_step"] += 1
                if SIMULATION_PROGRESS["current_step"] > SIMULATION_PROGRESS["total_steps"]:
                    SIMULATION_PROGRESS["current_step"] = SIMULATION_PROGRESS["total_steps"]
                time.sleep(0.1)
            
            # Get the output
            stdout, stderr = process.communicate()
            
            # Check if successful
            if process.returncode == 0:
                # Find the generated GIF file (most recent in OUTPUT_DIR)
                gif_files = [f for f in os.listdir(OUTPUT_DIR) if f.endswith('.gif')]
                if gif_files:
                    # Sort by creation time, newest first
                    gif_files.sort(key=lambda x: os.path.getctime(os.path.join(OUTPUT_DIR, x)), reverse=True)
                    gif_path = gif_files[0]
                    result = {"success": True, "gif_path": gif_path}
                else:
                    result = {"success": False, "error": "No simulation output generated"}
            else:
                result = {"success": False, "error": stderr}
                
        except Exception as e:
            result = {"success": False, "error": str(e)}
        
        # Restore the original method
        SimulationEngine.step = original_step
        
        # Reload simulations to include the new one
        load_simulations()
        
    except Exception as e:
        # Restore the original method in case of exception
        SimulationEngine.step = original_step if 'original_step' in locals() else SimulationEngine.step
        result = {"success": False, "error": str(e)}
    
    return jsonify(result)

@app.route('/api/strategies')
def get_strategies():
    """Get all available scanning strategies."""
    strategy_manager = StrategyManager()
    strategies = strategy_manager.get_strategy_names()
    return jsonify(strategies)

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
    <title>Drone Explorer</title>
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
        select, input[type="number"], input[type="text"] {{
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
            margin-right: 5px;
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
        .tabs {{
            display: flex;
            margin-bottom: 20px;
            border-bottom: 1px solid #ddd;
        }}
        .tab {{
            padding: 10px 20px;
            cursor: pointer;
            border: 1px solid transparent;
            border-bottom: none;
            border-radius: 4px 4px 0 0;
            margin-right: 5px;
        }}
        .tab.active {{
            background-color: #fff;
            border-color: #ddd;
            border-bottom-color: #fff;
            margin-bottom: -1px;
            font-weight: bold;
        }}
        .tab-content {{
            display: none;
        }}
        .tab-content.active {{
            display: block;
        }}
        .form-group {{
            margin-bottom: 15px;
        }}
        .progress-container {{
            width: 100%;
            background-color: #f1f1f1;
            border-radius: 4px;
            margin-top: 20px;
            display: none;
        }}
        .progress-bar {{
            width: 0%;
            height: 20px;
            background-color: #4CAF50;
            border-radius: 4px;
            text-align: center;
            line-height: 20px;
            color: white;
        }}
        .status-message {{
            margin-top: 10px;
            font-style: italic;
            color: #666;
        }}
        .header {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 20px;
            padding: 10px;
            background-color: #f5f5f5;
            border-radius: 4px;
        }}
        .logo-container {{
            display: flex;
            align-items: center;
        }}
        .logo {{
            height: 40px;
            margin-right: 15px;
        }}
        .title-container {{
            flex: 1;
            text-align: center;
        }}
    </style>
</head>
<body>
    <div class="header">
        <div class="logo-container">
            <img src="/static/logo-aws.svg" alt="AWS Logo" class="logo">
        </div>
        <div class="title-container">
            <img src="/static/logo-drone.png" alt="Drone Logo" style="height: 60px; margin-bottom: 5px; display: block; margin-left: auto; margin-right: auto;">
            <h1>Drone Explorer</h1>
        </div>
        <div class="logo-container">
            <img src="/static/logo-toc.svg" alt="TOC Logo" class="logo">
        </div>
    </div>
    <div class="container">
        <div class="sidebar">
            <div class="tabs">
                <div class="tab active" data-tab="history-tab">History</div>
                <div class="tab" data-tab="new-simulation-tab">New Simulation</div>
            </div>
            
            <div id="history-tab" class="tab-content active">
                <div class="filter-group">
                    <label for="drone-type">Drone Type:</label>
                    <select id="drone-type">
                        {drone_type_html}
                    </select>
                    
                    <label for="seed">Seed:</label>
                    <select id="seed">
                        {seed_html}
                    </select>
                    
                    <label for="strategy">Camera:</label>
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
            
            <div id="new-simulation-tab" class="tab-content">
                <h2>Create New Simulation</h2>
                <form id="simulation-form">
                    <div class="form-group">
                        <label for="pattern">Drone Pattern:</label>
                        <select id="pattern" name="pattern">
                            <option value="lawnmower">Lawnmower</option>
                            <option value="circular">Circular</option>
                            <option value="ai">AI</option>
                        </select>
                    </div>
                    
                    <div class="form-group" id="strategy-group">
                        <label for="new-strategy">Strategy:</label>
                        <select id="new-strategy" name="strategy">
                            <option value="">Default</option>
                            <!-- Will be populated via JavaScript -->
                        </select>
                    </div>
                    
                    <div class="form-group">
                        <label for="new-seed">Seed (optional):</label>
                        <input type="text" id="new-seed" name="seed" placeholder="Random if empty">
                    </div>
                    
                    <div class="form-group" id="num-drones-group">
                        <label for="num-drones">Number of Drones:</label>
                        <input type="number" id="num-drones" name="num_drones" min="1" max="10" value="4">
                    </div>
                    
                    <div class="form-group">
                        <label for="steps">Simulation Steps:</label>
                        <input type="number" id="steps" name="steps" min="1" max="500" value="200">
                    </div>
                    
                    <button type="submit" id="run-simulation-button">Run Simulation</button>
                </form>
                
                <div class="progress-container" id="progress-container">
                    <div class="progress-bar" id="progress-bar">0%</div>
                </div>
                <div class="status-message" id="status-message"></div>
            </div>
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
        const tabs = document.querySelectorAll('.tab');
        const tabContents = document.querySelectorAll('.tab-content');
        const simulationForm = document.getElementById('simulation-form');
        const patternSelect = document.getElementById('pattern');
        const newStrategySelect = document.getElementById('new-strategy');
        const newSeedInput = document.getElementById('new-seed');
        const numDronesInput = document.getElementById('num-drones');
        const stepsInput = document.getElementById('steps');
        const runSimulationButton = document.getElementById('run-simulation-button');
        const progressContainer = document.getElementById('progress-container');
        const progressBar = document.getElementById('progress-bar');
        const statusMessage = document.getElementById('status-message');
        
        // Event listeners
        applyFiltersButton.addEventListener('click', loadSimulations);
        resetFiltersButton.addEventListener('click', resetFilters);
        playButton.addEventListener('click', togglePlay);
        speedSlider.addEventListener('input', updateSpeed);
        refreshButton.addEventListener('click', () => {{
            window.location.reload();
        }});
        tabs.forEach(tab => {{
            tab.addEventListener('click', () => {{
                // Remove active class from all tabs
                tabs.forEach(t => {{
                    t.classList.remove('active');
                }});
                // Add active class to clicked tab
                tab.classList.add('active');
                // Hide all tab contents
                tabContents.forEach(content => {{
                    content.classList.remove('active');
                }});
                // Show the corresponding tab content
                const tabContent = document.getElementById(tab.dataset.tab);
                tabContent.classList.add('active');
            }});
        }});
        simulationForm.addEventListener('submit', runNewSimulation);
        
        // Load simulations on page load
        loadSimulations();
        
        // Load strategies for the new simulation form
        loadStrategies();
        
        // Update form fields based on pattern selection
        patternSelect.addEventListener('change', updateFormFields);
        
        // Initialize form fields based on default pattern
        updateFormFields();
        
        // Functions
        function loadSimulations() {{
            const droneType = droneTypeSelect.value;
            const seed = seedSelect.value;
            const strategy = strategySelect.value;
            
            fetch('/api/simulations?drone_type=' + droneType + '&seed=' + seed + '&strategy=' + strategy)
                .then(response => response.json())
                .then(data => {{
                    simulations = data;
                    updateSimulationList();
                }})
                .catch(error => {{
                    console.error('Error loading simulations:', error);
                    simulationList.innerHTML = '<div class="no-simulations">Error loading simulations</div>';
                }});
            
            // Return a promise for chaining
            return new Promise((resolve, reject) => {{
                setTimeout(() => resolve(), 500);
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
            info += '<strong>Drone Type:</strong> ' + (simulation.drone_type || 'N/A') + '<br>';
            info += '<strong>Seed:</strong> ' + (simulation.seed || 'N/A') + '<br>';
            
            if (simulation.strategy) {{
                info += '<strong>Strategy:</strong> ' + simulation.strategy + '<br>';
            }}
            
            if (simulation.h_value && simulation.v_value) {{
                info += '<strong>H:</strong> ' + simulation.h_value + ', <strong>V:</strong> ' + simulation.v_value + '<br>';
            }}
            
            if (simulation.timestamp) {{
                info += '<strong>Date:</strong> ' + simulation.timestamp + '<br>';
            }}
            
            infoPanel.innerHTML = info;
            
            // Load the GIF
            simulationGif.src = '/simulation/' + simulation.filename;
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
            speedValue.textContent = speed + 'x';
            
            // Adjust animation speed
            // Note: Controlling GIF animation speed is challenging in browsers
            // This is a limitation of the web-based approach
        }}
        
        function runNewSimulation(event) {{
            event.preventDefault();
            
            // Disable form elements during simulation
            const formElements = simulationForm.elements;
            for (let i = 0; i < formElements.length; i++) {{
                formElements[i].disabled = true;
            }}
            
            // Show progress container and reset
            progressContainer.style.display = 'block';
            progressBar.style.width = '0%';
            progressBar.textContent = '0%';
            statusMessage.textContent = 'Starting simulation...';
            
            // Create form data
            const formData = new FormData(simulationForm);
            
            // Send request to run simulation
            fetch('/api/run_simulation', {{
                method: 'POST',
                body: formData
            }})
            .then(response => response.json())
            .then(data => {{
                if (data.success) {{
                    // Show success message
                    statusMessage.textContent = 'Simulation completed successfully!';
                    
                    // Set progress to 100%
                    progressBar.style.width = '100%';
                    progressBar.textContent = '100%';
                    
                    // Switch to history tab and select the new simulation
                    tabs[0].click(); // Click on History tab
                    
                    // Refresh the simulation list
                    loadSimulations().then(() => {{
                        // Find and select the new simulation
                        if (data.gif_path) {{
                            const simulationItems = document.querySelectorAll('.simulation-item');
                            for (const item of simulationItems) {{
                                if (item.dataset.filename === data.gif_path) {{
                                    item.click();
                                    item.scrollIntoView({{ behavior: 'smooth' }});
                                    break;
                                }}
                            }}
                        }}
                    }});
                    
                    // Re-enable form elements
                    for (let i = 0; i < formElements.length; i++) {{
                        formElements[i].disabled = false;
                    }}
                }} else {{
                    // Show error message
                    progressBar.style.width = '100%';
                    progressBar.textContent = 'Error';
                    progressBar.style.backgroundColor = '#f44336';
                    statusMessage.textContent = data.error || 'Error creating simulation!';
                    
                    // Re-enable form elements
                    for (let i = 0; i < formElements.length; i++) {{
                        formElements[i].disabled = false;
                    }}
                }}
            }})
            .catch(error => {{
                console.error('Error running simulation:', error);
                progressBar.style.width = '100%';
                progressBar.textContent = 'Error';
                progressBar.style.backgroundColor = '#f44336';
                statusMessage.textContent = 'Error creating simulation!';
                
                // Re-enable form elements
                for (let i = 0; i < formElements.length; i++) {{
                    formElements[i].disabled = false;
                }}
            }});
            
            // Start polling for progress updates
            pollProgress();
        }}
        
        function pollProgress() {{
            // Create a polling interval to check progress
            const progressInterval = setInterval(() => {{
                fetch('/api/progress')
                    .then(response => response.json())
                    .then(data => {{
                        // Calculate progress percentage
                        if (data.total_steps > 0) {{
                            const progressPercent = Math.round((data.current_step / data.total_steps) * 100);
                            
                            // Update progress bar
                            progressBar.style.width = progressPercent + '%';
                            progressBar.textContent = progressPercent + '%';
                            
                            // Update status message
                            statusMessage.textContent = 'Running simulation... Step ' + 
                                data.current_step + ' of ' + data.total_steps;
                            
                            // If simulation is complete, clear the interval
                            if (data.current_step >= data.total_steps) {{
                                clearInterval(progressInterval);
                            }}
                        }}
                    }})
                    .catch(error => {{
                        console.error('Error fetching progress:', error);
                    }});
            }}, 500); // Poll every 500ms
            
            // Store the interval ID in a global variable so we can clear it if needed
            window.progressIntervalId = progressInterval;
        }}
        
        function loadStrategies() {{
            fetch('/api/strategies')
                .then(response => response.json())
                .then(strategies => {{
                    // Clear existing options except the first one
                    while (newStrategySelect.options.length > 1) {{
                        newStrategySelect.remove(1);
                    }}
                    
                    // Add new options
                    strategies.forEach(strategy => {{
                        const option = document.createElement('option');
                        option.value = strategy;
                        option.textContent = strategy;
                        newStrategySelect.appendChild(option);
                    }});
                }})
                .catch(error => {{
                    console.error('Error loading strategies:', error);
                }});
        }}
        
        function updateFormFields() {{
            const pattern = patternSelect.value;
            
            // Show/hide strategy field based on pattern
            if (pattern === 'lawnmower') {{
                document.getElementById('strategy-group').style.display = 'block';
            }} else {{
                document.getElementById('strategy-group').style.display = 'none';
            }}
            
            // Show/hide num drones field based on pattern
            if (pattern === 'ai') {{
                document.getElementById('num-drones-group').style.display = 'block';
            }} else {{
                document.getElementById('num-drones-group').style.display = 'none';
            }}
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

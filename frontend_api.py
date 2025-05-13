#!/usr/bin/env python3
"""
API endpoints for the frontend portal to interact with the drone simulation.
"""
import os
import json
import argparse
import http.server
import socketserver
from urllib.parse import urlparse, parse_qs
import threading
import time
from pathlib import Path

# Import simulation modules
from ocean_map import OceanMap
from lawnmower_drone import LawnmowerDrone
from circular_drone import CircularDrone
from catching_system import CatchingSystem
from simulation_engine import SimulationEngine
from visualization import SimulationVisualizer
from strategy_manager import StrategyManager

# Global variables
OUTPUT_DIR = "output"
FRONTEND_DIR = "frontend"

class SimulationRequestHandler(http.server.SimpleHTTPRequestHandler):
    """Custom request handler for the simulation API."""
    
    def __init__(self, *args, **kwargs):
        # Set the directory to serve static files from
        self.directory = os.path.join(os.getcwd(), FRONTEND_DIR)
        super().__init__(*args, **kwargs)
    
    def do_GET(self):
        """Handle GET requests."""
        parsed_url = urlparse(self.path)
        path = parsed_url.path
        
        # API endpoints
        if path == '/api/strategies':
            self.send_strategies()
        elif path == '/api/simulation-results':
            self.send_simulation_results()
        else:
            # Serve static files
            super().do_GET()
    
    def do_POST(self):
        """Handle POST requests."""
        parsed_url = urlparse(self.path)
        path = parsed_url.path
        
        # API endpoints
        if path == '/api/run-simulation':
            self.run_simulation()
        else:
            self.send_error(404, "API endpoint not found")
    
    def send_strategies(self):
        """Send the list of available strategies."""
        strategy_manager = StrategyManager()
        strategies = {}
        
        for name in strategy_manager.get_strategy_names():
            strategies[name] = strategy_manager.get_strategy(name)
        
        self.send_json_response(strategies)
    
    def send_simulation_results(self):
        """Send the list of available simulation results."""
        # Get query parameters
        parsed_url = urlparse(self.path)
        query = parse_qs(parsed_url.query)
        
        # Get list of simulation results (GIF files in the output directory)
        results = []
        output_path = Path(OUTPUT_DIR)
        
        if output_path.exists() and output_path.is_dir():
            for file in output_path.glob("*.gif"):
                results.append({
                    "filename": file.name,
                    "path": f"/output/{file.name}",
                    "created": file.stat().st_mtime
                })
        
        # Sort by creation time (newest first)
        results.sort(key=lambda x: x["created"], reverse=True)
        
        # Limit results if requested
        limit = int(query.get('limit', [10])[0])
        results = results[:limit]
        
        self.send_json_response(results)
    
    def run_simulation(self):
        """Run a simulation with the provided parameters."""
        # Get the request body
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length).decode('utf-8')
        params = json.loads(post_data)
        
        # Extract parameters
        pattern = params.get('pattern', 'lawnmower')
        strategy = params.get('strategy')
        seed = params.get('seed')
        steps = int(params.get('steps', 200))
        
        # Additional parameters
        ocean_width = float(params.get('ocean_width', 100.0))
        ocean_height = float(params.get('ocean_height', 100.0))
        particle_density = float(params.get('particle_density', 0.5))
        
        # Convert seed to int if provided
        if seed:
            try:
                seed = int(seed)
            except ValueError:
                seed = None
        
        # Run the simulation in a separate thread
        thread = threading.Thread(
            target=self._run_simulation_thread,
            args=(pattern, strategy, seed, steps, ocean_width, ocean_height, particle_density)
        )
        thread.start()
        
        # Return a success response
        self.send_json_response({
            "status": "success",
            "message": "Simulation started",
            "jobId": int(time.time())  # Use timestamp as job ID
        })
    
    def _run_simulation_thread(self, pattern, strategy, seed, steps, ocean_width, ocean_height, particle_density):
        """Run the simulation in a separate thread."""
        try:
            # Create output directory if it doesn't exist
            os.makedirs(OUTPUT_DIR, exist_ok=True)
            
            # Run the appropriate simulation
            if pattern == 'circular':
                self._run_circular_simulation(seed, steps, ocean_width, ocean_height, particle_density)
            else:
                self._run_lawnmower_simulation(strategy, seed, steps, ocean_width, ocean_height, particle_density)
                
            print(f"Simulation completed successfully")
        except Exception as e:
            print(f"Error running simulation: {e}")
    
    def _run_circular_simulation(self, seed, steps, ocean_width, ocean_height, particle_density):
        """Run a simulation with circular pattern drones."""
        # Create the ocean map
        ocean = OceanMap(width=ocean_width, height=ocean_height, particle_density=particle_density, seed=seed)
        
        # Create the catching system in the center of the map
        system_x = ocean_width / 2
        system_y = ocean_height / 2
        system = CatchingSystem(x_km=system_x, y_km=system_y)
        
        # Create circular drones
        drones = [
            CircularDrone(x_km=system_x, y_km=system_y, scan_radius=0.3,
                         center_x=system_x, center_y=system_y,
                         orbit_radius=2.0, drone_id=0, total_drones=5,
                         catching_system=system),
            
            CircularDrone(x_km=system_x, y_km=system_y, scan_radius=0.3,
                         center_x=system_x, center_y=system_y,
                         orbit_radius=2.5, drone_id=1, total_drones=5,
                         catching_system=system),
            
            CircularDrone(x_km=system_x, y_km=system_y, scan_radius=0.3,
                         center_x=system_x, center_y=system_y,
                         orbit_radius=3.0, drone_id=2, total_drones=5,
                         catching_system=system)
        ]
        
        # Run the simulation
        self._run_simulation(ocean, drones, system, steps, "circular", {"seed": ocean.seed})
    
    def _run_lawnmower_simulation(self, strategy_name, seed, steps, ocean_width, ocean_height, particle_density):
        """Run a simulation with lawnmower pattern drones."""
        # Create the ocean map
        ocean = OceanMap(width=ocean_width, height=ocean_height, particle_density=particle_density, seed=seed)
        
        # Create the catching system in the center of the map
        system_x = ocean_width / 2
        system_y = ocean_height / 2
        system = CatchingSystem(x_km=system_x, y_km=system_y)
        
        # Create lawnmower drones
        drones = [
            LawnmowerDrone(x_km=system_x, y_km=system_y, scan_radius=0.3, 
                          min_x=0.0, max_x=ocean_width, min_y=0.0, max_y=ocean_height,
                          step_size=2.0, initial_direction=1, initial_vertical_direction=1,
                          strategy_name=strategy_name),
            
            LawnmowerDrone(x_km=system_x, y_km=system_y, scan_radius=0.3, 
                          min_x=0.0, max_x=ocean_width, min_y=0.0, max_y=ocean_height,
                          step_size=2.0, initial_direction=-1, initial_vertical_direction=-1,
                          strategy_name=strategy_name)
        ]
        
        # Get strategy parameters for filename
        pattern_params = {"seed": ocean.seed}
        
        if strategy_name:
            strategy_manager = StrategyManager()
            strategy = strategy_manager.get_strategy(strategy_name)
            if strategy and "H (km)" in strategy and "V (km)" in strategy:
                pattern_params.update({
                    "strategy": strategy_name,
                    "H": strategy["H (km)"],
                    "V": strategy["V (km)"]
                })
            else:
                pattern_params["strategy"] = strategy_name
        
        # Run the simulation
        self._run_simulation(ocean, drones, system, steps, "lawnmower", pattern_params)
    
    def _run_simulation(self, ocean, drones, system, steps, pattern_name, pattern_params):
        """Run a simulation with the given components."""
        # Create the simulation engine
        simulation = SimulationEngine(ocean, drones, system)
        
        # Create the visualizer
        visualizer = SimulationVisualizer(ocean, drones, system, output_dir=OUTPUT_DIR, simulation_engine=simulation)
        
        # Run the simulation
        print(f"Starting simulation with {pattern_name} pattern drones...")
        for i in range(steps):
            # Run one simulation step
            stats = simulation.step()
            
            # Capture the current state as a frame
            visualizer.capture_frame(i + 1)
            
            # Print stats every 10 steps
            if i % 10 == 0:
                print(f"Step {stats['step']}: Detected {stats['particles_detected']:.2f}, "
                      f"Processed {stats['particles_processed']:.2f}")
        
        # Generate timestamp for unique filename
        import datetime
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Create a descriptive filename with parameters
        filename_parts = [f"simulation_{pattern_name}"]
        
        # Add strategy parameters if available
        if pattern_params:
            if "strategy" in pattern_params:
                # Clean up strategy name for filename
                clean_strategy = pattern_params["strategy"].replace(":", "-").replace(" ", "_")
                filename_parts.append(clean_strategy)
                
            if "H" in pattern_params and "V" in pattern_params:
                filename_parts.append(f"H{pattern_params['H']}_V{pattern_params['V']}")
                
            # Always include seed in filename
            if "seed" in pattern_params:
                filename_parts.append(f"seed{pattern_params['seed']}")
        
        # Add timestamp and extension
        filename_parts.append(timestamp)
        gif_filename = "_".join(filename_parts) + ".gif"
        
        # Save the animation
        gif_path = visualizer.save_animation(filename=gif_filename, fps=4)
        
        # Print final statistics
        final_stats = simulation.stats
        print("\nSimulation complete!")
        print(f"Total steps: {final_stats['total_steps']}")
        print(f"Total particles detected: {final_stats['total_particles_detected']:.2f}")
        print(f"Total particles processed: {final_stats['total_particles_processed']:.2f}")
        print(f"Animation saved to: {gif_path}")
    
    def send_json_response(self, data):
        """Send a JSON response."""
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

def run_server(port=8000):
    """Run the HTTP server."""
    # Create output directory if it doesn't exist
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Set up the server
    handler = SimulationRequestHandler
    httpd = socketserver.ThreadingTCPServer(("", port), handler)
    
    print(f"Serving at http://localhost:{port}")
    print(f"Frontend available at http://localhost:{port}/index.html")
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        httpd.shutdown()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Drone Simulation Frontend API")
    parser.add_argument("--port", type=int, default=8000, help="Port to run the server on")
    args = parser.parse_args()
    
    run_server(args.port)
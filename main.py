#!/usr/bin/env python3
"""
Main script to demonstrate the drone simulation framework.

Simulation Scale and Speeds:
- Map: 100km x 100km (1 grid unit = 1 km)
- Drones: 100 km/h (10 grid units per step)
- Drone Field of View: 300m x 300m (0.3km x 0.3km)
- Drone Pattern: Dense lawnmower pattern with 2km spacing between lines
- Collecting System: 1.5 knots ≈ 2.78 km/h (0.278 grid units per step)
- Collecting System Range: 900m (0.9km) in all directions
- Particles: 0.5 knots ≈ 0.93 km/h (0.093 grid units per step)
"""
import os
import datetime
import sys
import argparse
from ocean_map import OceanMap
from lawnmower_drone import LawnmowerDrone
from circular_drone import CircularDrone
from catching_system import CatchingSystem
from simulation_engine import SimulationEngine
from visualization import SimulationVisualizer
from strategy_manager import StrategyManager

def run_lawnmower_simulation(output_dir, strategy_name=None, seed=None):
    """
    Run a simulation using lawnmower pattern drones.
    
    Args:
        output_dir (str): Directory to save output files
        strategy_name (str, optional): Name of the scanning strategy to use
        seed (int, optional): Random seed for reproducible particle dispersion
        
    Returns:
        tuple: (final_stats, gif_path)
    """
    # Create the ocean map with optional seed
    ocean = OceanMap(width=100.0, height=100.0, particle_density=0.5, seed=seed)
    
    # Create the catching system in the center of the map
    system_lat = 50.0
    system_long = 50.0
    system = CatchingSystem(lat=system_lat, long=system_long, capacity=50.0)
    
    # Create a fleet of drones all starting at the catching system's location
    # but heading in different directions to avoid path overlap
    drones = [
        # Drone 1: Start at system, move east and north
        # Field of view is 300m x 300m (0.3km x 0.3km)
        # Using a small step size (2.0 km) for a denser pattern with more lines
        LawnmowerDrone(lat=system_lat, long=system_long, scan_radius=0.3, 
                       min_lat=0.0, max_lat=100.0, min_long=0.0, max_long=100.0,
                       step_size=2.0, initial_direction=1, initial_vertical_direction=1,
                       strategy_name=strategy_name),
        
        # Drone 2: Start at system, move west and south
        # Field of view is 300m x 300m (0.3km x 0.3km)
        # Using a small step size (2.0 km) for a denser pattern with more lines
        LawnmowerDrone(lat=system_lat, long=system_long, scan_radius=0.3, 
                       min_lat=0.0, max_lat=100.0, min_long=0.0, max_long=100.0,
                       step_size=2.0, initial_direction=-1, initial_vertical_direction=-1,
                       strategy_name=strategy_name)
    ]
    
    # Include strategy name and seed in pattern_name if provided
    pattern_name = "lawnmower"
    pattern_params = {}
    
    if strategy_name:
        # Get strategy parameters for filename
        strategy_manager = StrategyManager()
        strategy = strategy_manager.get_strategy(strategy_name)
        if strategy and "H (km)" in strategy and "V (km)" in strategy:
            pattern_params = {
                "strategy": strategy_name,
                "H": strategy["H (km)"],
                "V": strategy["V (km)"]
            }
        else:
            pattern_params = {"strategy": strategy_name}
    
    # Add seed to pattern parameters
    pattern_params["seed"] = ocean.seed
            
    return run_simulation(ocean, drones, system, output_dir, pattern_name, pattern_params)

def run_circular_simulation(output_dir, seed=None):
    """
    Run a simulation using circular pattern drones.
    
    Args:
        output_dir (str): Directory to save output files
        seed (int, optional): Random seed for reproducible particle dispersion
        
    Returns:
        tuple: (final_stats, gif_path)
    """
    # Create the ocean map with optional seed
    ocean = OceanMap(width=100.0, height=100.0, particle_density=0.5, seed=seed)
    
    # Create the catching system in the center of the map
    system_lat = 50.0
    system_long = 50.0
    system = CatchingSystem(lat=system_lat, long=system_long, capacity=50.0)
    
    # Create a fleet of circular drones
    # Each drone will fly in circles in front of the system
    # Pass the catching system reference so drones can follow it
    drones = [
        # Drone 1: Closest to the system, small circle
        CircularDrone(lat=system_lat, long=system_long, scan_radius=0.3,
                     center_lat=system_lat, center_long=system_long,
                     orbit_radius=2.0, drone_id=0, total_drones=5,
                     catching_system=system),
        
        # Drone 2: Medium distance, left side
        CircularDrone(lat=system_lat, long=system_long, scan_radius=0.3,
                     center_lat=system_lat, center_long=system_long,
                     orbit_radius=2.5, drone_id=1, total_drones=5,
                     catching_system=system),
        
        # Drone 3: Medium distance, right side
        CircularDrone(lat=system_lat, long=system_long, scan_radius=0.3,
                     center_lat=system_lat, center_long=system_long,
                     orbit_radius=2.5, drone_id=2, total_drones=5,
                     catching_system=system),
        
        # Drone 4: Further out, left side
        CircularDrone(lat=system_lat, long=system_long, scan_radius=0.3,
                     center_lat=system_lat, center_long=system_long,
                     orbit_radius=3.0, drone_id=3, total_drones=5,
                     catching_system=system),
        
        # Drone 5: Further out, right side
        CircularDrone(lat=system_lat, long=system_long, scan_radius=0.3,
                     center_lat=system_lat, center_long=system_long,
                     orbit_radius=3.0, drone_id=4, total_drones=5,
                     catching_system=system)
    ]
    
    # Add seed to pattern parameters
    pattern_params = {"seed": ocean.seed}
    return run_simulation(ocean, drones, system, output_dir, "circular", pattern_params)

def run_simulation(ocean, drones, system, output_dir, pattern_name, pattern_params={}):
    """
    Run a simulation with the given components.
    
    Args:
        ocean (OceanMap): The ocean map
        drones (list): List of drone objects
        system (CatchingSystem): The catching system
        output_dir (str): Directory to save output files
        pattern_name (str): Name of the drone pattern for the output filename
        pattern_params (dict): Additional parameters to include in the filename
        
    Returns:
        tuple: (final_stats, gif_path)
    """
    # Create the simulation engine
    simulation = SimulationEngine(ocean, drones, system)
    
    # Create the visualizer and pass the simulation engine for trajectory tracking
    visualizer = SimulationVisualizer(ocean, drones, system, output_dir=output_dir, simulation_engine=simulation)
    
    # Number of steps to run
    num_steps = 200  # Increased to see longer simulation behavior
    
    # Run the simulation
    print(f"Starting simulation with {pattern_name} pattern drones...")
    for i in range(num_steps):
        # Run one simulation step
        stats = simulation.step()
        
        # Capture the current state as a frame
        visualizer.capture_frame(i + 1)
        
        # Print stats every 10 steps
        if i % 10 == 0:
            print(f"Step {stats['step']}: Detected {stats['particles_detected']:.2f}, "
                  f"Processed {stats['particles_processed']:.2f}")
    
    # Generate timestamp for unique filename
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
    
    return final_stats, gif_path

def list_strategies():
    """List all available scanning strategies."""
    strategy_manager = StrategyManager()
    strategies = strategy_manager.get_strategy_names()
    default_strategy = strategy_manager.get_default_strategy_name()
    
    print("\nAvailable scanning strategies:")
    for i, strategy in enumerate(strategies, 1):
        if strategy == default_strategy:
            print(f"{i}. {strategy} (default)")
        else:
            print(f"{i}. {strategy}")

def main():
    # Create output directory
    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)
    
    # Set up argument parser
    parser = argparse.ArgumentParser(description="Drone Simulation")
    parser.add_argument("pattern", nargs="?", choices=["circular", "lawnmower"], default="lawnmower",
                        help="Drone flight pattern (default: lawnmower)")
    parser.add_argument("--strategy", "-s", help="Scanning strategy for lawnmower pattern")
    parser.add_argument("--list-strategies", "-l", action="store_true", help="List available scanning strategies")
    parser.add_argument("--seed", type=int, help="Random seed for reproducible particle dispersion")
    
    args = parser.parse_args()
    
    # List strategies if requested
    if args.list_strategies:
        list_strategies()
        return
    
    # Run the appropriate simulation
    if args.pattern == "circular":
        if args.strategy:
            print("Note: Strategy selection is only applicable for lawnmower pattern")
        run_circular_simulation(output_dir, args.seed)
    else:
        run_lawnmower_simulation(output_dir, args.strategy, args.seed)

if __name__ == "__main__":
    main()

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
import math
from ocean_map import OceanMap
from lawnmower_drone import LawnmowerDrone
from circular_drone import CircularDrone
from ai_drone import AIDrone
from catching_system import CatchingSystem
from simulation_engine import SimulationEngine
from visualization import SimulationVisualizer
from strategy_manager import StrategyManager

def run_lawnmower_simulation(output_dir, strategy_name=None, zarr_path=None, num_steps=200):
    """
    Run a simulation using lawnmower pattern drones.
    
    Args:
        output_dir (str): Directory to save output files
        strategy_name (str, optional): Name of the scanning strategy to use
        zarr_path (str, optional): Path to the zarr file containing particle data
        num_steps (int, optional): Number of simulation steps to run
        
    Returns:
        tuple: (final_stats, gif_path)
    """
    # Create the ocean map with zarr path
    ocean = OceanMap(width=100.0, height=100.0, zarr_path=zarr_path)
    
    # Create the catching system in the center of the map
    system_x = 50.0
    system_y = 50.0
    system = CatchingSystem(x_km=system_x, y_km=system_y)
    
    # Create a fleet of drones all starting at the catching system's location
    # but heading in different directions to avoid path overlap
    drones = [
        # Drone 1: Start at system, move east and north
        # Field of view is 300m x 300m (0.3km x 0.3km)
        # Using a small step size (2.0 km) for a denser pattern with more lines
        LawnmowerDrone(x_km=system_x, y_km=system_y, scan_radius=0.3, 
                       min_x=0.0, max_x=100.0, min_y=0.0, max_y=100.0,
                       step_size=2.0, initial_direction=1, initial_vertical_direction=1,
                       strategy_name=strategy_name),
        
        # Drone 2: Start at system, move west and south
        # Field of view is 300m x 300m (0.3km x 0.3km)
        # Using a small step size (2.0 km) for a denser pattern with more lines
        LawnmowerDrone(x_km=system_x, y_km=system_y, scan_radius=0.3, 
                       min_x=0.0, max_x=100.0, min_y=0.0, max_y=100.0,
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
    
    # No need to add seed parameter since we're using zarr files
            
    return run_simulation(ocean, drones, system, output_dir, pattern_name, pattern_params, num_steps)

def run_circular_simulation(output_dir, zarr_path=None, num_steps=200):
    """
    Run a simulation using circular pattern drones.
    
    Args:
        output_dir (str): Directory to save output files
        zarr_path (str, optional): Path to the zarr file containing particle data
        num_steps (int, optional): Number of simulation steps to run
    """
    # Create the ocean map with particles from zarr file
    ocean = OceanMap(zarr_path=zarr_path)
    
    # Create a catching system in the center of the map
    system_x = ocean.width / 2
    system_y = ocean.height / 2
    system = CatchingSystem(x_km=system_x, y_km=system_y)
    
    # Create drones in a circular pattern around the catching system
    drones = [
        CircularDrone(x_km=system_x, y_km=system_y + 5, scan_radius=0.3,
                     center_x=system_x, center_y=system_y,
                     orbit_radius=5.0, drone_id=0, total_drones=5,
                     catching_system=system),
        CircularDrone(x_km=system_x + 5, y_km=system_y, scan_radius=0.3,
                     center_x=system_x, center_y=system_y,
                     orbit_radius=5.0, drone_id=1, total_drones=5,
                     catching_system=system),
        CircularDrone(x_km=system_x, y_km=system_y - 5, scan_radius=0.3,
                     center_x=system_x, center_y=system_y,
                     orbit_radius=5.0, drone_id=2, total_drones=5,
                     catching_system=system),
        CircularDrone(x_km=system_x - 5, y_km=system_y, scan_radius=0.3,
                     center_x=system_x, center_y=system_y,
                     orbit_radius=5.0, drone_id=3, total_drones=5,
                     catching_system=system),
        CircularDrone(x_km=system_x, y_km=system_y, scan_radius=0.3,
                     center_x=system_x, center_y=system_y,
                     orbit_radius=3.0, drone_id=4, total_drones=5,
                     catching_system=system)
    ]
    
    # Create pattern parameters for the filename
    pattern_params = {}
    return run_simulation(ocean, drones, system, output_dir, "circular", pattern_params, num_steps)

def run_ai_simulation(output_dir, zarr_path=None, num_drones=4, num_steps=200):
    """
    Run a simulation using AI drones with dynamic path planning.
    
    Args:
        output_dir (str): Directory to save output files
        seed (int, optional): Random seed for reproducible particle dispersion
        num_drones (int, optional): Number of drones to use in the simulation
        
    Returns:
        tuple: (final_stats, gif_path)
    """
    # Create the ocean map with optional seed
    ocean = OceanMap(width=100.0, height=100.0, particle_density=0.5, seed=seed)
    
    # Create the catching system in the center of the map
    system_x = 50.0
    system_y = 50.0
    system = CatchingSystem(x_km=system_x, y_km=system_y)
    
    # Create a fleet of AI drones with dynamic path planning
    drones = []
    
    # Calculate starting positions distributed around the catching system
    # This helps drones start in different areas to avoid initial overlap
    for i in range(num_drones):
        # Calculate angle for this drone (evenly distributed around a circle)
        angle = 2 * math.pi * i / num_drones
        
        # Calculate starting position (10 units away from center)
        start_offset = 10.0
        start_x = system_x + start_offset * math.cos(angle)
        start_y = system_y + start_offset * math.sin(angle)
        
        # Ensure within boundaries
        start_x = max(0.0, min(100.0, start_x))
        start_y = max(0.0, min(100.0, start_y))
        
        # Create drone with unique ID and initial heading toward its assigned sector
        drone = AIDrone(
            x_km=start_x, 
            y_km=start_y, 
            scan_radius=0.3, 
            min_x=0.0, 
            max_x=100.0, 
            min_y=0.0, 
            max_y=100.0,
            step_size=2.0,  # Increased step size for faster exploration
            drone_id=i
        )
        
        # Set initial heading toward the drone's preferred sector
        sector = i % 4  # 0=SW, 1=SE, 2=NW, 3=NE
        if sector == 0:  # Southwest
            drone.current_heading = 5 * math.pi / 4  # 225 degrees
        elif sector == 1:  # Southeast
            drone.current_heading = 7 * math.pi / 4  # 315 degrees
        elif sector == 2:  # Northwest
            drone.current_heading = 3 * math.pi / 4  # 135 degrees
        else:  # Northeast
            drone.current_heading = math.pi / 4  # 45 degrees
        
        drones.append(drone)
    
    # Add seed and drone count to pattern parameters
    pattern_name = "ai"
    pattern_params = {
        "seed": ocean.seed,
        "num_drones": num_drones
    }
            
    return run_simulation(ocean, drones, system, output_dir, pattern_name, pattern_params, num_steps)

def run_circular_simulation(output_dir, zarr_path=None, num_steps=200):
    """
    Run a simulation using circular pattern drones.
    
    Args:
        output_dir (str): Directory to save output files
        zarr_path (str, optional): Path to the zarr file containing particle data
        num_steps (int, optional): Number of simulation steps to run
        
    Returns:
        tuple: (final_stats, gif_path)
    """
    # Create the ocean map with zarr path
    ocean = OceanMap(width=100.0, height=100.0, zarr_path=zarr_path)
    
    # Create the catching system in the center of the map
    system_x = 50.0
    system_y = 50.0
    system = CatchingSystem(x_km=system_x, y_km=system_y)
    
    # Create a fleet of circular drones
    drones = [
        # Drone 1: Closest to the system, small circle
        CircularDrone(x_km=system_x, y_km=system_y, scan_radius=0.3,
                     center_x=system_x, center_y=system_y,
                     orbit_radius=2.0, drone_id=0, total_drones=5,
                     catching_system=system),
        
        # Drone 2: Medium distance, left side
        CircularDrone(x_km=system_x, y_km=system_y, scan_radius=0.3,
                     center_x=system_x, center_y=system_y,
                     orbit_radius=2.5, drone_id=1, total_drones=5,
                     catching_system=system),
        
        # Drone 3: Medium distance, right side
        CircularDrone(x_km=system_x, y_km=system_y, scan_radius=0.3,
                     center_x=system_x, center_y=system_y,
                     orbit_radius=2.5, drone_id=2, total_drones=5,
                     catching_system=system),
        
        # Drone 4: Further out, left side
        CircularDrone(x_km=system_x, y_km=system_y, scan_radius=0.3,
                     center_x=system_x, center_y=system_y,
                     orbit_radius=3.0, drone_id=3, total_drones=5,
                     catching_system=system),
        
        # Drone 5: Further out, right side
        CircularDrone(x_km=system_x, y_km=system_y, scan_radius=0.3,
                     center_x=system_x, center_y=system_y,
                     orbit_radius=3.0, drone_id=4, total_drones=5,
                     catching_system=system)
    ]
    
    # Create pattern parameters for the filename
    pattern_params = {}
    return run_simulation(ocean, drones, system, output_dir, "circular", pattern_params, num_steps)

def run_simulation(ocean, drones, system, output_dir, pattern_name, pattern_params={}, num_steps=200):
    """
    Run a simulation with the given components.
    
    Args:
        ocean (OceanMap): The ocean map
        drones (list): List of drone objects
        system (CatchingSystem): The catching system
        output_dir (str): Directory to save output files
        pattern_name (str): Name of the drone pattern for filename
        pattern_params (dict): Additional parameters to include in the filename
        num_steps (int): Number of simulation steps to run
        
    Returns:
        tuple: (final_stats, gif_path)
    """
    # Create the simulation engine
    simulation = SimulationEngine(ocean, drones, system)
    
    # Create the visualizer and pass the simulation engine for trajectory tracking
    visualizer = SimulationVisualizer(ocean, drones, system, output_dir=output_dir, simulation_engine=simulation)
    
    # Run the simulation
    print(f"Starting simulation with {pattern_name} pattern drones for {num_steps} steps...")
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
    parser.add_argument("pattern", nargs="?", choices=["circular", "lawnmower", "ai"], default="lawnmower",
                        help="Drone flight pattern (default: lawnmower)")
    parser.add_argument("--strategy", "-s", help="Scanning strategy for lawnmower pattern")
    parser.add_argument("--list-strategies", "-l", action="store_true", help="List available scanning strategies")
    # Zarr file parameter for particle data
    parser.add_argument("--zarr", "-z", help="Path to OceanParcels zarr file for particle data")
    parser.add_argument("--num-drones", "-n", type=int, default=4, help="Number of drones to use (default: 4, only applicable for AI pattern)")
    parser.add_argument("--steps", type=int, default=200, help="Number of simulation steps to run (default: 200)")
    
    args = parser.parse_args()
    
    # List strategies if requested
    if args.list_strategies:
        list_strategies()
        return
    
    # Run the appropriate simulation
    if args.pattern == "circular":
        if args.strategy:
            print("Note: Strategy selection is only applicable for lawnmower pattern")
        print(f"Running circular simulation for {args.steps} steps...")
        run_circular_simulation(output_dir, args.zarr, args.steps)
    elif args.pattern == "ai":
        if args.strategy:
            print("Note: Strategy selection is only applicable for lawnmower pattern")
        print(f"Running AI simulation with {args.num_drones} drones for {args.steps} steps...")
        run_ai_simulation(output_dir, args.zarr, args.num_drones, args.steps)
    else:
        run_lawnmower_simulation(output_dir, args.strategy, args.zarr, args.steps)

if __name__ == "__main__":
    main()

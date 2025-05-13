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
from ocean_map import OceanMap
from lawnmower_drone import LawnmowerDrone
from circular_drone import CircularDrone
from catching_system import CatchingSystem
from simulation_engine import SimulationEngine
from visualization import SimulationVisualizer

def run_lawnmower_simulation(output_dir):
    """
    Run a simulation using lawnmower pattern drones.
    
    Args:
        output_dir (str): Directory to save output files
        
    Returns:
        tuple: (final_stats, gif_path)
    """
    # Create the ocean map
    ocean = OceanMap(width=100.0, height=100.0, particle_density=0.5)
    
    # Create the catching system in the center of the map
    system_lat = 50.0
    system_long = 50.0
    system = CatchingSystem(lat=system_lat, long=system_long)
    
    # Create a fleet of drones all starting at the catching system's location
    # but heading in different directions to avoid path overlap
    drones = [
        # Drone 1: Start at system, move east and north
        # Field of view is 300m x 300m (0.3km x 0.3km)
        # Using a small step size (2.0 km) for a denser pattern with more lines
        LawnmowerDrone(lat=system_lat, long=system_long, scan_radius=0.3, 
                       min_lat=0.0, max_lat=100.0, min_long=0.0, max_long=100.0,
                       step_size=2.0, initial_direction=1, initial_vertical_direction=1),
        
        # Drone 2: Start at system, move west and south
        # Field of view is 300m x 300m (0.3km x 0.3km)
        # Using a small step size (2.0 km) for a denser pattern with more lines
        LawnmowerDrone(lat=system_lat, long=system_long, scan_radius=0.3, 
                       min_lat=0.0, max_lat=100.0, min_long=0.0, max_long=100.0,
                       step_size=2.0, initial_direction=-1, initial_vertical_direction=-1)
    ]
    
    return run_simulation(ocean, drones, system, output_dir, "lawnmower")

def run_circular_simulation(output_dir):
    """
    Run a simulation using circular pattern drones.
    
    Args:
        output_dir (str): Directory to save output files
        
    Returns:
        tuple: (final_stats, gif_path)
    """
    # Create the ocean map
    ocean = OceanMap(width=100.0, height=100.0, particle_density=0.5)
    
    # Create the catching system in the center of the map
    system_lat = 50.0
    system_long = 50.0
    system = CatchingSystem(lat=system_lat, long=system_long)
    
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
    
    return run_simulation(ocean, drones, system, output_dir, "circular")

def run_simulation(ocean, drones, system, output_dir, pattern_name):
    """
    Run a simulation with the given components.
    
    Args:
        ocean (OceanMap): The ocean map
        drones (list): List of drone objects
        system (CatchingSystem): The catching system
        output_dir (str): Directory to save output files
        pattern_name (str): Name of the drone pattern for the output filename
        
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
    gif_filename = f"simulation_{pattern_name}_{timestamp}.gif"
    
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

def main():
    # Create output directory
    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)
    
    # Get drone pattern from command line argument if provided
    if len(sys.argv) > 1 and sys.argv[1].lower() == "circular":
        pattern = "circular"
    else:
        pattern = "lawnmower"
    
    # Run the appropriate simulation
    if pattern == "circular":
        run_circular_simulation(output_dir)
    else:
        run_lawnmower_simulation(output_dir)

if __name__ == "__main__":
    main()

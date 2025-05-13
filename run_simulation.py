#!/usr/bin/env python3
"""
Script to run the simulation with configurable parameters.
"""
import os
import sys
import subprocess
import argparse

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Run drone simulation with configurable parameters')
    
    # Required parameters
    parser.add_argument('--pattern', type=str, required=True, choices=['lawnmower', 'circular', 'ai'],
                        help='Drone pattern to use (lawnmower, circular, or ai)')
    
    # Optional parameters
    parser.add_argument('--strategy', type=str, help='Camera/strategy name for lawnmower pattern')
    parser.add_argument('--seed', type=int, help='Random seed for reproducible results')
    parser.add_argument('--num-drones', type=int, default=4, help='Number of drones for AI pattern')
    parser.add_argument('--steps', type=int, default=200, help='Number of simulation steps')
    # Note: Output directory is defined in main.py and not configurable via command line
    parser.add_argument('--zarr', type=str, default='pset/36_Particles.zarr', help='Path to zarr file with particle data')
    
    return parser.parse_args()

def main():
    """Main function to run the simulation."""
    # Parse command line arguments
    args = parse_arguments()
    
    # Path to the Python executable (use the current Python interpreter)
    python_executable = sys.executable
    
    # Build the command to run the simulation
    command = [python_executable, "main.py", args.pattern]
    
    # Add pattern-specific arguments
    if args.pattern == 'lawnmower' and args.strategy:
        command.extend(["--strategy", args.strategy])
    elif args.pattern == 'ai' and args.num_drones:
        command.extend(["--num-drones", str(args.num_drones)])
    
    # Add common arguments
    if args.seed is not None:
        command.extend(["--seed", str(args.seed)])
    if args.steps:
        command.extend(["--steps", str(args.steps)])
    # Output directory is handled by main.py internally
    if args.zarr:
        command.extend(["--zarr", args.zarr])
    
    # Run the command
    print(f"Running command: {' '.join(command)}")
    result = subprocess.run(command, capture_output=True, text=True)
    
    # Print the output
    print("\nOutput:")
    print(result.stdout)
    
    # Print any errors
    if result.stderr:
        print("\nErrors:")
        print(result.stderr)
    
    # Return the exit code
    return result.returncode

if __name__ == "__main__":
    sys.exit(main())

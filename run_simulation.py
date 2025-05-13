#!/usr/bin/env python3
"""
Script to run the simulation with the 36_Particles.zarr file.
"""
import os
import sys
import subprocess

# Path to the Python executable in the virtual environment
python_executable = "./venv/bin/python3"

# Command to run the simulation with the 36_Particles.zarr file
command = [python_executable, "main.py", "lawnmower", "--zarr", "pset/36_Particles.zarr"]

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

print("\nSimulation complete!")

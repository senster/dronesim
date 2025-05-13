# Drone Simulation

A Python-based simulation of drones detecting and processing particles in an ocean environment.

## Overview

This project simulates a fleet of drones that fly in various patterns to detect particles in an ocean environment. A catching system follows the drones and processes the detected particles. The simulation visualizes the movement of drones, the catching system, and the particle density in the ocean.

## Features

- **Multiple Drone Types**:
  - Circular Drones: Fly in circular patterns in front of the catching system
  - Lawnmower Drones: Follow a back-and-forth pattern to cover a large area

- **Smart Catching System**:
  - Navigates toward high-density areas detected by drones
  - Processes particles when drones are in range
  - Limited turning capability (45° per 3 hours)
  - Constant movement speed (2.78 km/h)

- **Dynamic Ocean Environment**:
  - Particle clusters that drift with wind patterns
  - Realistic particle distribution with high-density areas
  - Particles are removed from the map when processed by the catching system

- **Visualization**:
  - Animated GIF output showing the simulation progress
  - Heatmap of particle density
  - Drone and catching system trajectories

## Getting Started

### Prerequisites

- Python 3.6+
- Required packages: numpy, matplotlib

### Installation

1. Clone the repository:
   ```
   git clone https://github.com/senster/dronesim.git
   cd dronesim
   ```

2. Create a virtual environment (optional but recommended):
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

### Running the Simulation

Run the simulation with circular pattern drones:
```
python main.py circular
```

Run the simulation with lawnmower pattern drones:
```
python main.py lawnmower
```

#### Scanning Strategies

The lawnmower pattern supports different scanning strategies that affect how drones move and scan the area. To list all available strategies:
```
python main.py --list-strategies
```

To run the simulation with a specific strategy:
```
python main.py lawnmower --strategy "1:5 Ratio"
```
or using the short option:
```
python main.py lawnmower -s "1:5 Ratio"
```

If no strategy is specified, a default strategy will be used.

#### Reproducible Simulations

You can specify a random seed to ensure reproducible particle dispersion across multiple runs:
```
python main.py lawnmower --seed 12345
```

This can be combined with strategy selection:
```
python main.py lawnmower -s "1:5 Ratio" --seed 12345
```

If no seed is specified, a random seed will be generated and displayed in the output. The seed is also included in the output GIF filename for reference.

## Output

The simulation generates an animated GIF in the `output` directory showing:
- Drone positions and movements (blue)
- Catching system position and movement (yellow)
- Particle density (heatmap)
- Areas where particles have been processed (visible as cleared areas in the heatmap)

## Project Structure

- `main.py`: Entry point for the simulation
- `actor.py`: Base class for all objects in the simulation
- `drone.py`: Base class for drone objects
- `circular_drone.py`: Implementation of drones flying in circular patterns
- `lawnmower_drone.py`: Implementation of drones flying in lawnmower patterns
- `catching_system.py`: Implementation of the system that processes particles
- `ocean_map.py`: Representation of the ocean environment with particle distribution
- `simulation_engine.py`: Coordinates all actors and runs the simulation
- `visualization.py`: Handles visualization and animation of the simulation

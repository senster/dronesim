# Drone Simulation Frontend Portal

This directory contains a web-based frontend portal for the Drone Simulation project. The portal provides an interactive interface to configure, run, and visualize drone simulations.

## Features

- **Interactive Tree View**: Browse through project components, strategies, and simulation outputs
- **Dropdown Menus**: Select drone patterns, scanning strategies, and other simulation parameters
- **Advanced Settings**: Configure detailed simulation parameters through a modal dialog
- **Simulation Results**: View simulation animations and statistics

## Getting Started

### Prerequisites

- Python 3.6+
- Required packages: flask, flask-cors (included in the main requirements.txt)

### Running the Frontend Portal

1. Start the frontend API server:
   ```
   python frontend_api.py
   ```

2. Open your web browser and navigate to:
   ```
   http://localhost:8000/index.html
   ```

## Usage

1. **Configure Simulation**:
   - Select a drone pattern (Circular or Lawnmower)
   - Choose a scanning strategy (for Lawnmower pattern)
   - Optionally set a random seed for reproducible results
   - Adjust the number of simulation steps

2. **Advanced Settings**:
   - Click the "Advanced Settings" button to access additional configuration options
   - Adjust ocean dimensions, particle density, and number of drones

3. **Run Simulation**:
   - Click the "Run Simulation" button to start the simulation
   - Wait for the simulation to complete (this may take a few moments)

4. **View Results**:
   - The simulation animation will be displayed in the results area
   - Statistics about the simulation will be shown in the sidebar

## Project Structure

- `index.html`: Main HTML file for the frontend portal
- `css/styles.css`: CSS styles for the portal
- `js/main.js`: Main JavaScript functionality
- `js/tree-view.js`: Tree view component implementation
- `js/strategies.js`: Strategy management functionality
- `images/`: Directory containing placeholder images and sample simulations

## Integration with Backend

The frontend portal communicates with the simulation backend through the `frontend_api.py` script, which provides API endpoints for:

- Retrieving available strategies
- Running simulations with specified parameters
- Accessing simulation results

## Customization

You can customize the frontend portal by:

- Adding new visualization options
- Extending the tree view with additional project components
- Creating new interactive controls for simulation parameters
- Implementing real-time simulation monitoring
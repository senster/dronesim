import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
from PIL import Image
import io
import os

class SimulationVisualizer:
    """
    Handles visualization and animation of the simulation.
    """
    def __init__(self, ocean_map, drones, catching_system, output_dir="output", simulation_engine=None):
        """
        Initialize the visualizer.
        
        Args:
            ocean_map (OceanMap): The ocean map for the simulation
            drones (list): List of Drone objects
            catching_system (CatchingSystem): The catching system
            output_dir (str): Directory to save output files
            simulation_engine (SimulationEngine, optional): The simulation engine for trajectory data
        """
        self.ocean_map = ocean_map
        self.drones = drones
        self.catching_system = catching_system
        self.output_dir = output_dir
        self.frames = []
        self.simulation_engine = simulation_engine
        
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
    def capture_frame(self, step_num):
        """
        Capture a frame of the current simulation state.
        
        Args:
            step_num (int): Current step number
        """
        # Create figure with two subplots - map view and time series
        fig = plt.figure(figsize=(12, 12))
        
        # Create grid spec to control subplot layout
        gs = fig.add_gridspec(2, 1, height_ratios=[2, 1])  # Map view is twice as tall as time series
        
        # Create main map view subplot
        ax_map = fig.add_subplot(gs[0])
        
        # Set title and limits for map view
        ax_map.set_title(f"Simulation Step {step_num}")
        ax_map.set_xlim(0, self.ocean_map.width)
        ax_map.set_ylim(0, self.ocean_map.height)
        ax_map.set_xlabel("Longitude")
        ax_map.set_ylabel("Latitude")
        
        # Plot particle density as a heatmap
        self._plot_particle_density(ax_map)
        
        # Plot drone positions and scan areas
        self._plot_drones(ax_map)
        
        # Plot catching system
        self._plot_catching_system(ax_map)
        
        # Add a legend to map view
        ax_map.legend(loc='upper left')
        
        # Create time series subplot if we have simulation engine data
        if self.simulation_engine and hasattr(self.simulation_engine, 'time_series_data'):
            ax_time = fig.add_subplot(gs[1])
            self._plot_time_series(ax_time, step_num)
        
        # Save the figure to a buffer
        buf = io.BytesIO()
        plt.savefig(buf, format='png')
        buf.seek(0)
        
        # Convert to PIL Image and append to frames
        img = Image.open(buf)
        self.frames.append(img)
        
        # Close the figure to free memory
        plt.close(fig)
        
    def save_animation(self, filename="simulation.gif", fps=5):
        """
        Save all captured frames as an animated GIF.
        
        Args:
            filename (str): Name of the output file
            fps (int): Frames per second for the animation
        
        Returns:
            str: Path to the saved GIF file
        """
        if not self.frames:
            print("No frames to save!")
            return None
            
        output_path = os.path.join(self.output_dir, filename)
        
        # Save the frames as an animated GIF
        self.frames[0].save(
            output_path,
            save_all=True,
            append_images=self.frames[1:],
            optimize=False,
            duration=1000//fps,  # milliseconds per frame
            loop=0  # 0 means loop forever
        )
        
        print(f"Animation saved to {output_path}")
        return output_path
        
    def _plot_particle_density(self, ax):
        """
        Plot the particle density as a heatmap.
        
        Args:
            ax (matplotlib.axes.Axes): Axes to plot on
        """
        # For visualization purposes, we'll use a coarser grid than the actual simulation
        # to make the heatmap more readable and efficient to render
        vis_grid_size = 2
        
        # Create a grid for the heatmap
        x_grid = np.linspace(0, self.ocean_map.width, int(self.ocean_map.width/vis_grid_size) + 1)
        y_grid = np.linspace(0, self.ocean_map.height, int(self.ocean_map.height/vis_grid_size) + 1)
        X, Y = np.meshgrid(x_grid, y_grid)
        
        # Get density values for each grid cell by sampling the high-resolution data
        Z = np.zeros((len(y_grid)-1, len(x_grid)-1))
        
        # Sample points within each visualization grid cell
        for i in range(len(y_grid)-1):
            for j in range(len(x_grid)-1):
                # Calculate the center of this visualization grid cell
                center_x = (x_grid[j] + x_grid[j+1]) / 2
                center_y = (y_grid[i] + y_grid[i+1]) / 2
                
                # Sample the density at this point using the ocean map's calculation
                if hasattr(self.ocean_map, '_calculate_density_at_point'):
                    # Use the direct calculation method if available
                    Z[i, j] = self.ocean_map._calculate_density_at_point(center_x, center_y)
                else:
                    # Fall back to grid-based lookup
                    grid_x = int(center_x / self.ocean_map.grid_size)
                    grid_y = int(center_y / self.ocean_map.grid_size)
                    key = (grid_x, grid_y)
                    if key in self.ocean_map.particle_map:
                        Z[i, j] = self.ocean_map.particle_map[key]
                    else:
                        Z[i, j] = 0.0  # Default to zero density if not in particle map
        
        # Plot the heatmap with blue (low density) to red (high density) colormap
        im = ax.pcolormesh(X, Y, Z, cmap='coolwarm', alpha=0.7, vmin=0, vmax=1)
        plt.colorbar(im, ax=ax, label="Particle Density")
        
        # No need to plot clusters as they've been removed from the OceanMap class
        
    def _plot_wind(self, ax):
        """
        Plot the wind direction and speed.
        
        Args:
            ax (matplotlib.axes.Axes): Axes to plot on
        """
        # Wind visualization removed as we're now using zarr files for particle data
        pass
    
    def _plot_drones(self, ax):
        """
        Plot drone positions, trajectories, and scan areas.
        
        Args:
            ax (matplotlib.axes.Axes): Axes to plot on
        """
        colors = ['red', 'green', 'blue', 'purple', 'orange']
        
        for i, drone in enumerate(self.drones):
            color = colors[i % len(colors)]
            
            # Get trajectory from simulation engine if available, otherwise use current position
            trajectories = self.simulation_engine.drone_trajectories if self.simulation_engine else {i: [(drone.x_km, drone.y_km)]}
            
            # Plot drone trajectory
            if i in trajectories and len(trajectories[i]) > 1:
                traj_x, traj_y = zip(*trajectories[i])
                ax.plot(traj_x, traj_y, color=color, linestyle='-', alpha=0.5, 
                        label=f"Drone {i+1} Trajectory" if len(trajectories[i]) == 2 else "")
            
            # Plot drone position
            ax.scatter(drone.x_km, drone.y_km, color=color, s=100, marker='o', 
                       edgecolors='black', linewidths=1, label=f"Drone {i+1}")
            
            # Plot scan area
            polygon = drone._create_scan_polygon()
            poly_x = [p[1] for p in polygon]  # Note: polygon points are (lat, long)
            poly_y = [p[0] for p in polygon]
            poly_x.append(poly_x[0])  # Close the polygon
            poly_y.append(poly_y[0])
            ax.plot(poly_x, poly_y, color=color, linestyle='--')
            
            # Fill the scan area with a transparent color
            scan_polygon = patches.Polygon(list(zip(poly_x, poly_y)), 
                                          closed=True, fill=True, 
                                          color=color, alpha=0.2)
            ax.add_patch(scan_polygon)
    
    def _plot_time_series(self, ax, current_step):
        """
        Plot time series data showing particle densities and catching system performance.
        
        Args:
            ax (matplotlib.axes.Axes): Axes to plot on
            current_step (int): Current simulation step
        """
        time_data = self.simulation_engine.time_series_data
        
        # Only plot if we have data
        if not time_data['steps'] or len(time_data['steps']) < 2:
            ax.text(0.5, 0.5, "Collecting data...", 
                   ha='center', va='center', fontsize=14, 
                   transform=ax.transAxes)
            return
            
        # Set up the plot
        ax.set_title("Particle Density and Collection Over Time")
        ax.set_xlabel("Simulation Step")
        ax.set_ylabel("Particle Density / Collection")
        
        # Get the x-axis data (steps)
        steps = time_data['steps']
        max_step = max(current_step, max(steps) if steps else 0)
        
        # Set x-axis limits with some padding for future steps
        ax.set_xlim(0, max_step + 5)
        
        # Plot cumulative caught particles (on a separate y-axis if values are very different)
        if time_data['cumulative_caught'] and max(time_data['cumulative_caught']) > 10:
            ax2 = ax.twinx()
            cumulative_line = ax2.plot(range(len(time_data['cumulative_caught'])), 
                                     time_data['cumulative_caught'], 
                                     'k-', linewidth=2, label="Cumulative Caught")
            ax2.set_ylabel("Cumulative Particles Caught")
            ax2.set_ylim(bottom=0)
        else:
            cumulative_line = ax.plot(range(len(time_data['cumulative_caught'])), 
                                    time_data['cumulative_caught'], 
                                    'k-', linewidth=2, label="Cumulative Caught")
        
        # Plot current caught particles
        current_line = ax.plot(steps, time_data['current_caught'], 
                              'k--', linewidth=1.5, label="Current Caught")
        
        # Plot system density
        system_line = ax.plot(steps, time_data['system_density'], 
                             'y-', linewidth=1.5, label="System Density")
        
        # Plot drone densities
        drone_lines = []
        colors = ['r', 'g', 'b', 'purple', 'orange']
        linestyles = ['-', '--', '-.', ':']
        
        for i, densities in time_data['drone_densities'].items():
            if len(densities) > 0:
                color = colors[i % len(colors)]
                style = linestyles[i % len(linestyles)]
                line = ax.plot(steps, densities, 
                              color=color, linestyle=style, linewidth=1.5, 
                              label=f"Drone {i+1} Density")
                drone_lines.append(line)
        
        # Add grid and legend
        ax.grid(True, linestyle='--', alpha=0.7)
        
        # Combine all lines for the legend
        all_lines = []
        all_labels = []
        
        # Add cumulative line to legend
        if 'ax2' in locals():
            all_lines.extend(cumulative_line)
            all_labels.append("Cumulative Caught")
            
        all_lines.extend(current_line)
        all_labels.append("Current Caught")
        
        all_lines.extend(system_line)
        all_labels.append("System Density")
        
        for i, line in enumerate(drone_lines):
            all_lines.extend(line)
            all_labels.append(f"Drone {i+1} Density")
        
        # Create legend
        ax.legend(all_lines, all_labels, loc='upper left')
        
        # Set y-axis to start at 0
        ax.set_ylim(bottom=0)
    
    def _plot_catching_system(self, ax):
        """
        Plot the catching system, its heading, and target position.
        
        Args:
            ax (matplotlib.axes.Axes): Axes to plot on
        """
        # Plot catching system position
        ax.scatter(self.catching_system.x_km, self.catching_system.y_km, 
                  color='black', s=200, marker='s', 
                  edgecolors='yellow', linewidths=2, label="Catching System")
        
        # Plot catching system range - 900 meters (0.9 km)
        range_circle = patches.Circle((self.catching_system.x_km, self.catching_system.y_km), 
                                     radius=0.9, fill=False, 
                                     color='yellow', linestyle='-.')
        ax.add_patch(range_circle)
        
        # Plot movement direction based on recent trajectory
        if self.simulation_engine and hasattr(self.simulation_engine, 'catching_system_trajectory'):
            trajectory = self.simulation_engine.catching_system_trajectory
            if len(trajectory) >= 2:
                # Calculate direction from the last two positions
                last_pos = trajectory[-1]
                prev_pos = trajectory[-2]
                
                # Calculate direction vector
                dx = last_pos[0] - prev_pos[0]  # Change in x_km
                dy = last_pos[1] - prev_pos[1]  # Change in y_km
                
                # Only draw if there's actual movement
                if dx != 0 or dy != 0:
                    # Normalize and scale the vector
                    magnitude = np.sqrt(dx*dx + dy*dy)
                    if magnitude > 0:
                        arrow_length = 10.0
                        dx = arrow_length * dx / magnitude
                        dy = arrow_length * dy / magnitude
                        
                        # Draw an arrow indicating the movement direction
                        ax.arrow(self.catching_system.x_km, self.catching_system.y_km, 
                                dx, dy, head_width=3, head_length=3, 
                                fc='yellow', ec='black', linewidth=2)
        
        # Fallback to heading attribute if trajectory not available
        elif hasattr(self.catching_system, 'heading'):
            # Convert heading to radians (0 = North, 90 = East)
            heading_rad = np.radians(self.catching_system.heading - 90)  # Adjust for coordinate system
            arrow_length = 10.0
            dx = arrow_length * np.cos(heading_rad)
            dy = arrow_length * np.sin(heading_rad)
            
            # Draw an arrow indicating the heading
            ax.arrow(self.catching_system.x_km, self.catching_system.y_km, 
                    dx, dy, head_width=3, head_length=3, 
                    fc='yellow', ec='black', linewidth=2)
        
        # Target position visualization removed
        
        # Plot catching system trajectory if available from simulation engine
        if self.simulation_engine and hasattr(self.simulation_engine, 'catching_system_trajectory'):
            trajectory = self.simulation_engine.catching_system_trajectory
            if len(trajectory) > 1:
                traj_x, traj_y = zip(*trajectory)
                ax.plot(traj_x, traj_y, color='yellow', linestyle='-', alpha=0.7, 
                        linewidth=2, label="Catching System Path")

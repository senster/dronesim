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
    def __init__(self, ocean_map, drones, catching_systems, output_dir="output", simulation_engine=None):
        """
        Initialize the visualizer.
        
        Args:
            ocean_map (OceanMap): The ocean map for the simulation
            drones (list): List of Drone objects
            catching_systems (list or CatchingSystem): The catching system(s) - can be a single system or a list
            output_dir (str): Directory to save output files
            simulation_engine (SimulationEngine, optional): The simulation engine for trajectory data
        """
        self.ocean_map = ocean_map
        self.drones = drones
        
        # Handle either a single catching system or a list of systems
        if not isinstance(catching_systems, list):
            self.catching_systems = [catching_systems]
        else:
            self.catching_systems = catching_systems
            
        # For backward compatibility
        self.catching_system = self.catching_systems[0] if self.catching_systems else None
        
        # Define colors for different catching systems - to be used consistently across all plots
        # Order: drone, random, optimal, etc.
        self.system_colors = ['blue', 'red', 'green', 'purple', 'orange']
        
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
        Plot time series data showing cumulative caught particles for both catching systems.
        
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
        ax.set_title("Cumulative Particles Caught by System Type")
        ax.set_xlabel("Simulation Step")
        ax.set_ylabel("Cumulative Particles Caught")
        
        # Get the x-axis data (steps)
        steps = time_data['steps']
        max_step = max(current_step, max(steps) if steps else 0)
        
        # Set x-axis limits with some padding for future steps
        ax.set_xlim(0, max_step + 5)
        
        # Plot cumulative caught particles for each system
        system_lines = []
        system_labels = []
        
        # Use the same colors defined in the class initialization for consistency
        system_strategies = []
        
        # Get strategy names for labels
        for i, system in enumerate(self.catching_systems):
            if hasattr(system, 'strategy'):
                system_strategies.append(system.strategy)
            else:
                system_strategies.append(f"System {i+1}")
        
        # Plot each system's cumulative caught particles
        for i, cumulative in time_data['system_cumulative_caught'].items():
            if len(cumulative) > 1:  # Need at least two points to plot a line
                color = self.system_colors[i % len(self.system_colors)]
                strategy = system_strategies[i]
                
                # Plot the cumulative caught line
                x_values = range(len(cumulative))
                line = ax.plot(x_values, cumulative, 
                              color=color, linestyle='-', linewidth=2.5, 
                              label=f"{strategy.capitalize()} Strategy")
                
                system_lines.append(line)
                system_labels.append(f"{strategy.capitalize()} Strategy")
        
        # Add grid and legend
        ax.grid(True, linestyle='--', alpha=0.7)
        
        # Combine all lines for the legend
        all_lines = []
        all_labels = []
        
        for i, line in enumerate(system_lines):
            all_lines.extend(line)
            all_labels.append(system_labels[i])
        
        # Create legend
        if all_lines:
            ax.legend(all_lines, all_labels, loc='upper left')
        
        # Set y-axis to start at 0
        ax.set_ylim(bottom=0)
    
    def _plot_catching_system(self, ax):
        """
        Plot the catching systems, their headings, and trajectories.
        
        Args:
            ax (matplotlib.axes.Axes): Axes to plot on
        """
        # Plot each catching system with a different color
        for i, system in enumerate(self.catching_systems):
            # Select color for this system
            color_idx = i % len(self.system_colors)
            main_color = self.system_colors[color_idx]
            edge_color = 'yellow' if main_color != 'yellow' else 'white'
            
            # Create a label with strategy if available
            label = f"System ({system.strategy})" if hasattr(system, 'strategy') else f"System {i+1}"
            
            # Plot catching system position
            ax.scatter(system.x_km, system.y_km, 
                      color=main_color, s=200, marker='s', 
                      edgecolors=edge_color, linewidths=2, label=label)
            
            # Plot catching system range - 900 meters (0.9 km)
            range_circle = patches.Circle((system.x_km, system.y_km), 
                                         radius=0.9, fill=False, 
                                         color=edge_color, linestyle='-.')
            ax.add_patch(range_circle)
            
            # Plot movement direction based on trajectory or heading
            if self.simulation_engine and hasattr(self.simulation_engine, f'catching_system_{i}_trajectory'):
                trajectory = getattr(self.simulation_engine, f'catching_system_{i}_trajectory')
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
                            ax.arrow(system.x_km, system.y_km, 
                                    dx, dy, head_width=3, head_length=3, 
                                    fc=edge_color, ec=main_color, linewidth=2)
            
            # Fallback to heading attribute if trajectory not available
            elif hasattr(system, 'heading'):
                # Convert heading to radians (0 = North, 90 = East)
                heading_rad = np.radians(system.heading - 90)  # Adjust for coordinate system
                arrow_length = 10.0
                dx = arrow_length * np.cos(heading_rad)
                dy = arrow_length * np.sin(heading_rad)
                
                # Draw an arrow indicating the heading
                ax.arrow(system.x_km, system.y_km, 
                        dx, dy, head_width=3, head_length=3, 
                        fc=edge_color, ec=main_color, linewidth=2)
            
            # Plot catching system trajectory if available
            if self.simulation_engine:
                # Check for system-specific trajectory
                if hasattr(self.simulation_engine, f'catching_system_{i}_trajectory'):
                    trajectory = getattr(self.simulation_engine, f'catching_system_{i}_trajectory')
                # Fall back to main trajectory for the first system (backward compatibility)
                elif i == 0 and hasattr(self.simulation_engine, 'catching_system_trajectory'):
                    trajectory = self.simulation_engine.catching_system_trajectory
                else:
                    trajectory = None
                    
                if trajectory and len(trajectory) > 1:
                    traj_x, traj_y = zip(*trajectory)
                    ax.plot(traj_x, traj_y, color=main_color, linestyle='-', alpha=0.7, 
                            linewidth=2, label=f"{label} Path")

import os

import matplotlib.patches as patches
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
from matplotlib.lines import Line2D


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

    def capture_frame(self, step_number):
        """Capture the current state of the simulation."""
        import io

        # Recreate the figure for the next frame
        fig = plt.figure(figsize=(15, 12))  # Increased height to accommodate time series

        # Create grid spec for three subplots: main view, zoomed view, and time series
        grid_spec = fig.add_gridspec(2, 2, width_ratios=[2, 1], height_ratios=[2, 1])

        fig.clear()

        # Create main view subplot
        ax_main = fig.add_subplot(grid_spec[0, 0])
        # Create zoomed view subplot
        ax_zoom = fig.add_subplot(grid_spec[0, 1])
        # Create time series subplot (spans bottom row)
        ax_time = fig.add_subplot(grid_spec[1, :])

        # Plot main view
        self._plot_particle_density(ax_main)
        self._plot_wind(ax_main)
        self._plot_drones(ax_main)
        self._plot_catching_system(ax_main)

        # Plot zoomed view
        self._plot_zoomed_area(ax_zoom)

        # Plot time series
        self._plot_time_series(ax_time, step_number)

        # Adjust layout to prevent overlap
        fig.tight_layout()

        # Save the figure to a buffer
        buf = io.BytesIO()
        fig.savefig(buf, format='png', bbox_inches='tight')
        buf.seek(0)

        # Convert to PIL Image and append to frames
        img = Image.open(buf)
        # Create a copy of the image in memory
        img_copy = img.copy()
        self.frames.append(img_copy)

        # Close the buffer and the original image
        buf.close()
        img.close()

        # Close the figure to free memory
        plt.close(fig)

    def _plot_zoomed_area(self, ax, vessel_span=1.4):
        """
        Plot a zoomed view of the area around the catching system.

        Args:
            ax (matplotlib.axes.Axes): Axes to plot on
            vessel_span (float): Distance between vessels in km (default: 1.4)
        """
        # Define zoom area size (in km)
        zoom_radius = 4.0  # 8km total coverage (4km radius)

        # Get catching system position and heading
        cs_x = self.catching_system.x_km
        cs_y = self.catching_system.y_km

        # Get heading in radians
        if hasattr(self.catching_system, 'heading'):
            heading_rad = np.radians(self.catching_system.heading - 90)
        elif self.simulation_engine and len(self.simulation_engine.catching_system_trajectory) >= 2:
            trajectory = self.simulation_engine.catching_system_trajectory
            last_pos = trajectory[-1]
            prev_pos = trajectory[-2]
            dx = last_pos[0] - prev_pos[0]
            dy = last_pos[1] - prev_pos[1]
            heading_rad = np.arctan2(dy, dx)
        else:
            heading_rad = 0

        # Calculate vessel positions
        vessel_offset = vessel_span / 2
        cos_h = np.cos(heading_rad)
        sin_h = np.sin(heading_rad)

        vessel1_x = cs_x + (-vessel_offset * sin_h)  # Changed from cos_h to sin_h
        vessel1_y = cs_y + (vessel_offset * cos_h)  # Changed from sin_h to cos_h
        vessel2_x = cs_x + (vessel_offset * sin_h)  # Changed from cos_h to sin_h
        vessel2_y = cs_y + (-vessel_offset * cos_h)  # Changed from sin_h to cos_h

        # Calculate center point between vessels
        center_x = (vessel1_x + vessel2_x) / 2
        center_y = (vessel1_y + vessel2_y) / 2

        # Set plot limits centered between vessels
        ax.set_xlim(center_x - zoom_radius, center_x + zoom_radius)
        ax.set_ylim(center_y - zoom_radius, center_y + zoom_radius)

        # Plot particles
        particles = self._get_particles_in_zoom_area(center_x, center_y, zoom_radius)
        if particles:
            particle_x, particle_y = zip(*particles)
            ax.scatter(particle_x, particle_y, c='g', s=20, alpha=0.6, label='Particles')

        # Plot vessels as yellow dots
        ax.scatter([vessel1_x, vessel2_x], [vessel1_y, vessel2_y],
                   color='yellow', s=100, zorder=5, edgecolor='black')

        # Create curved net behind vessels
        num_points = 20
        t = np.linspace(0, 1, num_points)
        curve_depth = 0.7

        # Calculate control point for the net behind vessels
        control_x = center_x - curve_depth * cos_h
        control_y = center_y - curve_depth * sin_h

        # Generate quadratic Bezier curve for the net
        net_x = (1 - t) ** 2 * vessel1_x + 2 * (1 - t) * t * control_x + t ** 2 * vessel2_x
        net_y = (1 - t) ** 2 * vessel1_y + 2 * (1 - t) * t * control_y + t ** 2 * vessel2_y

        # Plot the net
        ax.plot(net_x, net_y, 'y-', linewidth=2, alpha=0.8, zorder=4)

        # Plot nearby drones (relative to center point)
        drone_plotted = False
        for drone in self.drones:
            if (abs(drone.x_km - center_x) <= zoom_radius and
                    abs(drone.y_km - center_y) <= zoom_radius):
                ax.plot(drone.x_km, drone.y_km, 'bo', markersize=8,
                        label='Drones' if not drone_plotted else '')
                drone_plotted = True

        # Add legend
        legend_elements = [
            Line2D([0], [0], marker='o', color='b', label='Drones',
                   markerfacecolor='b', markersize=8, linestyle='None'),
            Line2D([0], [0], marker='o', color='yellow', label='Catching System',
                   markerfacecolor='yellow', markersize=8, linestyle='None', markeredgecolor='black'),
            Line2D([0], [0], marker='o', color='g', label='Particles',
                   markerfacecolor='g', markersize=8, linestyle='None', alpha=0.6)
        ]
        ax.legend(handles=legend_elements, loc='upper right', bbox_to_anchor=(0.98, 0.98))

        # Add title and grid
        ax.set_title('Zoomed View (8km coverage)')
        ax.grid(True)

    def _get_particles_in_zoom_area(self, center_lat, center_long, radius):
        """Get individual particle positions in the zoomed area."""
        if not hasattr(self.ocean_map, 'get_particle_positions'):
            # If the ocean map doesn't provide individual particle positions,
            # we'll simulate them based on density
            particles = []
            resolution = 0.1  # 100m resolution

            for lat in np.arange(center_lat - radius, center_lat + radius, resolution):
                for long in np.arange(center_long - radius, center_long + radius, resolution):
                    density = self.ocean_map._calculate_density_at_point(lat, long)
                    # Convert density to number of particles (simplified)
                    num_particles = int(density * 10)  # Scale factor

                    # Add random offset to spread particles
                    for _ in range(num_particles):
                        particle_lat = lat + np.random.uniform(-resolution / 2, resolution / 2)
                        particle_long = long + np.random.uniform(-resolution / 2, resolution / 2)
                        if ((particle_lat - center_lat) ** 2 +
                                (particle_long - center_long) ** 2 <= radius ** 2):
                            particles.append((particle_lat, particle_long))

            return particles
        else:
            # If the ocean map provides particle positions, use them directly
            return self.ocean_map.get_particle_positions(
                center_lat, center_long, radius)

    def save_animation(self, filename="simulation.gif", fps=4):
        """Save the animation as a GIF file."""
        if not self.frames:
            return None

        output_path = os.path.join(self.output_dir, filename)

        # Duration between frames in milliseconds
        duration = int(1000 / fps)

        # Save as GIF
        self.frames[0].save(
            output_path,
            save_all=True,
            append_images=self.frames[1:],
            duration=duration,
            loop=0,  # Loop forever
            format='GIF'
        )

        # Close all frames to free memory
        for frame in self.frames:
            frame.close()

        # Clear the frames list
        self.frames = []

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
        x_grid = np.linspace(0, self.ocean_map.width, int(self.ocean_map.width / vis_grid_size) + 1)
        y_grid = np.linspace(0, self.ocean_map.height, int(self.ocean_map.height / vis_grid_size) + 1)
        X, Y = np.meshgrid(x_grid, y_grid)

        # Get density values for each grid cell by sampling the high-resolution data
        Z = np.zeros((len(y_grid) - 1, len(x_grid) - 1))

        # Sample points within each visualization grid cell
        for i in range(len(y_grid) - 1):
            for j in range(len(x_grid) - 1):
                # Calculate the center of this visualization grid cell
                center_x = (x_grid[j] + x_grid[j + 1]) / 2
                center_y = (y_grid[i] + y_grid[i + 1]) / 2

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
                        Z[i, j] = self.ocean_map.base_density

        # Plot the heatmap with blue (low density) to red (high density) colormap
        im = ax.pcolormesh(X, Y, Z, cmap='coolwarm', alpha=0.7, vmin=0, vmax=1)
        plt.colorbar(im, ax=ax, label="Particle Density")

        # Optionally plot cluster centers for debugging
        if hasattr(self.ocean_map, 'clusters'):
            for x, y, strength, radius in self.ocean_map.clusters:
                # Draw a small circle at each cluster center
                circle = patches.Circle((x, y), radius=radius / 2,
                                        fill=False, edgecolor='white',
                                        linestyle='--', alpha=0.5)
                ax.add_patch(circle)

    def _plot_wind(self, ax):
        """
        Plot the wind direction and speed.

        Args:
            ax (matplotlib.axes.Axes): Axes to plot on
        """
        if hasattr(self.ocean_map, 'wind_direction') and hasattr(self.ocean_map, 'wind_speed'):
            # Get wind parameters
            wind_dir = self.ocean_map.wind_direction
            wind_speed = self.ocean_map.wind_speed

            # In our simulation (ocean_map.py), the wind direction is in radians where:
            # - 0 radians points east
            # - π/2 radians points north
            # - π radians points west
            # - 3π/2 radians points south
            #
            # This is actually the same convention that matplotlib uses for the arrow function,
            # so we can use the wind direction directly.

            # Calculate wind vector components
            dx = wind_speed * 15 * np.cos(wind_dir)  # Scale for visibility
            dy = wind_speed * 15 * np.sin(wind_dir)  # Scale for visibility

            # Plot wind vector in top-right corner
            wind_pos_x = self.ocean_map.width * 0.85
            wind_pos_y = self.ocean_map.height * 0.85

            # Draw arrow for wind direction
            ax.arrow(wind_pos_x, wind_pos_y, dx, dy,
                     head_width=3, head_length=3,
                     fc='cyan', ec='white', linewidth=2)

            # Add text label
            ax.text(wind_pos_x, wind_pos_y + 5,
                    f"Wind: {wind_speed:.1f}",
                    color='white', fontweight='bold',
                    ha='center', va='bottom',
                    bbox=dict(facecolor='black', alpha=0.5))

            # Add a small compass indicator
            compass_radius = 5
            compass_circle = patches.Circle((wind_pos_x, wind_pos_y),
                                            radius=compass_radius,
                                            fill=False, edgecolor='white',
                                            alpha=0.5)
            ax.add_patch(compass_circle)

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
            trajectories = self.simulation_engine.drone_trajectories if self.simulation_engine else {
                i: [(drone.x_km, drone.y_km)]}

            # Plot drone trajectory
            if i in trajectories and len(trajectories[i]) > 1:
                traj_x, traj_y = zip(*trajectories[i])
                ax.plot(traj_x, traj_y, color=color, linestyle='-', alpha=0.5,
                        label=f"Drone {i + 1} Trajectory" if len(trajectories[i]) == 2 else "")

            # Plot drone position
            ax.scatter(drone.x_km, drone.y_km, color=color, s=100, marker='o',
                       edgecolors='black', linewidths=1, label=f"Drone {i + 1}")

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
                               label=f"Drone {i + 1} Density")
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
            all_labels.append(f"Drone {i + 1} Density")

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
                    magnitude = np.sqrt(dx * dx + dy * dy)
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

        # Plot target position if available
        if hasattr(self.catching_system, 'target_position') and self.catching_system.target_position is not None:
            target_y_km, target_x_km = self.catching_system.target_position
            ax.scatter(target_x_km, target_y_km,
                       color='yellow', s=100, marker='*',
                       edgecolors='black', linewidths=1, label="Target Position")

            # Draw a line from current position to target
            ax.plot([self.catching_system.x_km, target_x_km],
                    [self.catching_system.y_km, target_y_km],
                    'y--', alpha=0.5)

        # Plot catching system trajectory if available from simulation engine
        if self.simulation_engine and hasattr(self.simulation_engine, 'catching_system_trajectory'):
            trajectory = self.simulation_engine.catching_system_trajectory
            if len(trajectory) > 1:
                traj_x, traj_y = zip(*trajectory)
                ax.plot(traj_x, traj_y, color='yellow', linestyle='-', alpha=0.7,
                        linewidth=2, label="Catching System Path")

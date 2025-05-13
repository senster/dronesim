import numpy as np
import xarray as xr
import os
from datetime import datetime
from actor import Actor

class OceanMap(Actor):
    """
    Represents the ocean environment with particle distribution.
    Loads particles from OceanParcels zarr files.
    """
    def __init__(self, width=100.0, height=100.0, zarr_path="pset/0_Particles.zarr"):
        """
        Initialize an OceanMap with dimensions and particle distribution from zarr file.
        
        Args:
            width (float): Width of the map in kilometers
            height (float): Height of the map in kilometers
            zarr_path (str): Path to OceanParcels zarr file for particle data
        """
        super().__init__(0.0, 0.0)  # Position not relevant for the map
        self.width = width
        self.height = height
        self.particle_map = {}  # Will store density values for different regions
        self.grid_size = 1  # Higher resolution grid (1x1 units)

        # Track processed particles (where particles have been removed)
        self.processed_particles = {}  # Will store grid cells where particles have been processed
        
        # Zarr file path for loading particles
        self.zarr_path = zarr_path

        # Time-related attributes
        self.current_time_index = 0
        self.time_steps = []
        self.particles_data = None
        self.seconds_per_step = 300.0  # Default value (5 minutes)

        # Load particle data from zarr file
        print(f"Loading particles from zarr file: {self.zarr_path}")
        self._load_particles_from_zarr()
        
    def step(self):
        """
        Update the particle distribution for one time step.
        """
        self._update_particles_from_zarr()
        
    def get_particles_in_area(self, polygon):
        """
        Get the density of particles in a specified area.
        Takes into account areas where particles have been processed (removed).
        Optimized for performance.
        
        Args:
            polygon (list): List of (x_km, y_km) points defining the area to check
            
        Returns:
            float: Density of particles in the area (0.0 to 1.0)
        """
        # For simplicity, we'll just use the center point of the polygon
        # In a real implementation, this would calculate the actual intersection
        center_x_km = sum(p[0] for p in polygon) / len(polygon)
        center_y_km = sum(p[1] for p in polygon) / len(polygon)
        
        # Get the density at this point using the higher resolution grid
        grid_x = int(center_x_km / self.grid_size)
        grid_y = int(center_y_km / self.grid_size)
        key = (grid_x, grid_y)
        
        # Use cached values when possible for better performance
        # Check if this area has been processed (particles removed)
        if key in self.processed_particles:
            # Return the reduced density after processing
            return self.processed_particles[key]
        elif key in self.particle_map:
            return self.particle_map[key]
        else:
            # For points outside the grid, return zero density
            return 0.0

    def process_particles_at_location(self, x_km, y_km, amount):
        """
        Calculate particle densities for multiple points at once.
        Optimized for performance using vectorized operations.
        
        Args:
            lats (numpy.ndarray): Array of latitude positions
            longs (numpy.ndarray): Array of longitude positions
            
        Returns:
            numpy.ndarray: Array of density values between 0.0 and 1.0
        """
        # Start with base density for all points
        n_points = len(lats)
        densities = np.full(n_points, self.base_density)
        
        if len(self.clusters) == 0:
            return densities
            
        # Get cluster data
        cluster_positions = self.cluster_array[:, :2]  # x, y coordinates
        strengths = self.cluster_array[:, 2]
        radii = self.cluster_array[:, 3]
        radii_squared_2x = 2 * (radii ** 2)
        radii_3x_squared = (radii * 3) ** 2
        
        # For each point, calculate contributions from all clusters
        for i in range(n_points):
            lat, long = lats[i], longs[i]
            
            # Calculate distances to all clusters at once
            dx = lat - cluster_positions[:, 0]
            dy = long - cluster_positions[:, 1]
            distances_squared = dx*dx + dy*dy
            
            # Only consider clusters within 3x radius
            mask = distances_squared < radii_3x_squared
            
            # Calculate contributions for relevant clusters
            if np.any(mask):
                relevant_distances_squared = distances_squared[mask]
                relevant_strengths = strengths[mask]
                relevant_radii_squared = radii_squared_2x[mask]
                
                # Gaussian falloff from center
                contributions = relevant_strengths * np.exp(-relevant_distances_squared / relevant_radii_squared)
                densities[i] += np.sum(contributions)
        
        # Ensure densities are between 0.0 and 1.0
        return np.clip(densities, 0.0, 1.0)
            
    def process_particles_at_location(self, x_km, y_km, amount):
        """
        Process (remove) particles at a specific location.
        
        Args:
            x_km (float): X position in kilometers
            y_km (float): Y position in kilometers
            amount (float): Amount of particles to process (0.0 to 1.0)
        """
        # Get the grid cell for this location
        grid_x = int(x_km / self.grid_size)
        grid_y = int(y_km / self.grid_size)
        key = (grid_x, grid_y)
        
        # Get current density
        if key in self.particle_map:
            current_density = self.particle_map[key]
        else:
            current_density = 0.0

        # Check if this area has already been processed
        if key in self.processed_particles:
            current_density = self.processed_particles[key]
        
        # Calculate how much can be processed (can't process more than exists)
        processable = min(amount, current_density)
        
        # Reduce density by the processed amount
        new_density = max(0.0, current_density - processable)
        self.processed_particles[key] = new_density
        
        # Also process neighboring cells with a falloff effect
        radius = 1  # Process particles in a small radius around the target
        for dx in range(-radius, radius + 1):
            for dy in range(-radius, radius + 1):
                if dx == 0 and dy == 0:
                    continue  # Skip the center cell (already processed)
                
                neighbor_key = (grid_x + dx, grid_y + dy)

                # Get current density at neighbor
                if neighbor_key in self.particle_map:
                    neighbor_density = self.particle_map[neighbor_key]
                else:
                    neighbor_density = 0.0
                
                # Check if this neighbor has already been processed
                if neighbor_key in self.processed_particles:
                    neighbor_density = self.processed_particles[neighbor_key]
                
                # Calculate falloff based on distance
                distance = np.sqrt(dx*dx + dy*dy)
                falloff = max(0.0, 1.0 - distance/radius)

                # Process a portion of the neighbor's particles
                neighbor_processable = min(amount * falloff * 0.5, neighbor_density)
                new_neighbor_density = max(0.0, neighbor_density - neighbor_processable)

                # Update the processed particles map for this neighbor
                self.processed_particles[neighbor_key] = new_neighbor_density

                # Add the neighbor's processed amount to the total
                processable += neighbor_processable

        return processable
        
    def get_seconds_per_step(self):
        """
        Get the number of seconds per simulation step.

        Returns:
            float: Number of seconds per step
        """
        return self.seconds_per_step

    def _load_particles_from_zarr(self):
        """
        Load particle data from OceanParcels zarr file.
        Converts lat/lon coordinates to x/y in kilometers for our simulation.
        """
        try:
            # Load the zarr dataset
            ds = xr.open_zarr(self.zarr_path)

            # Extract time steps
            self.time_steps = ds.time.values

            # Store the dataset for later use
            self.particles_data = ds

            # Get the lat/lon ranges from the data
            min_lon = float(np.nanmin(ds.lon.values))
            max_lon = float(np.nanmax(ds.lon.values))
            min_lat = float(np.nanmin(ds.lat.values))
            max_lat = float(np.nanmax(ds.lat.values))

            # Store conversion parameters
            self.min_lon = min_lon
            self.max_lon = max_lon
            self.min_lat = min_lat
            self.max_lat = max_lat

            # Calculate time step in seconds
            try:
                if len(self.time_steps) > 1 and len(self.time_steps[0]) > 1:
                    # Get the first two valid timestamps for the first trajectory
                    valid_times = []
                    for i in range(len(self.time_steps[0])):
                        if not np.isnat(self.time_steps[0, i]):
                            valid_times.append(self.time_steps[0, i])
                        if len(valid_times) >= 2:
                            break

                    if len(valid_times) >= 2:
                        # Calculate time difference in seconds
                        time_diff = (valid_times[1] - valid_times[0]).astype('timedelta64[s]').astype(np.float64)
                        if time_diff > 0:
                            self.seconds_per_step = time_diff
                            print(f"Zarr time step: {self.seconds_per_step} seconds")
                        else:
                            # Default to 5 minutes if calculation gives negative or zero
                            self.seconds_per_step = 300.0
                            print("Invalid time step detected, using default: 300 seconds (5 minutes)")
                    else:
                        # Default to 5 minutes if not enough valid timestamps
                        self.seconds_per_step = 300.0
                        print("Not enough valid timestamps, using default: 300 seconds (5 minutes)")
                else:
                    # Default to 5 minutes if not enough data
                    self.seconds_per_step = 300.0
                    print("Not enough time data, using default: 300 seconds (5 minutes)")
            except Exception as e:
                # Default to 5 minutes if there's an error
                self.seconds_per_step = 300.0
                print(f"Error calculating time step: {e}")
                print("Using default time step: 300 seconds (5 minutes)")

            # Initialize the particle map based on the first time step
            self._update_particles_from_zarr()

            print(f"Successfully loaded particles from {self.zarr_path}")
            print(f"Lat range: {min_lat} to {max_lat}, Lon range: {min_lon} to {max_lon}")
            print(f"Time steps: {len(self.time_steps[0])}")

        except Exception as e:
            print(f"Error loading zarr file: {e}")
            raise e  # Re-raise the exception since we don't have a fallback

    def _update_particles_from_zarr(self):
        """
        Update the particle distribution based on the current time step in the zarr file.
        """
        if self.particles_data is None:
            return

        # Clear the current particle map
        self.particle_map = {}

        # Get the current time step data
        time_index = min(self.current_time_index, len(self.time_steps[0]) - 1)

        # Extract lat/lon for all particles at this time step
        lats = self.particles_data.lat.values[:, time_index]
        lons = self.particles_data.lon.values[:, time_index]

        # Count particles in each grid cell
        grid_counts = {}
        total_particles = 0

        # Process each particle
        for i in range(len(lats)):
            if np.isnan(lats[i]) or np.isnan(lons[i]):
                continue

            # Map from [min_lon, max_lon] to [0, width] and [min_lat, max_lat] to [0, height]
            x_km = ((lons[i] - self.min_lon) / (self.max_lon - self.min_lon)) * self.width
            y_km = ((lats[i] - self.min_lat) / (self.max_lat - self.min_lat)) * self.height

            # Skip if outside our map
            if x_km < 0 or x_km >= self.width or y_km < 0 or y_km >= self.height:
                continue

            # Convert to grid coordinates
            grid_x = int(x_km / self.grid_size)
            grid_y = int(y_km / self.grid_size)
            key = (grid_x, grid_y)

            # Increment count for this grid cell
            grid_counts[key] = grid_counts.get(key, 0) + 1
            total_particles += 1

        # Calculate average particles per cell if we have particles
        if total_particles > 0:
            # Find the maximum count for reference
            max_count = max(grid_counts.values()) if grid_counts else 1

            # Convert counts to density values
            for key, count in grid_counts.items():
                # Use a simple approach: high visibility for any cell with particles
                # Scale between 0.7 and 1.0 based on relative count
                relative_to_max = count / max_count
                density = 0.7 + (relative_to_max * 0.3)  # Ensures all particles are highly visible

                # Store in particle map
                self.particle_map[key] = density

        # Print some statistics about the particle distribution
        if total_particles > 0:
            print(f"Time step {self.current_time_index}: {total_particles} particles in {len(grid_counts)} cells (avg: {total_particles/max(1, len(grid_counts)):.2f} per occupied cell)")

        # Increment time index for next step
        self.current_time_index = (self.current_time_index + 1) % len(self.time_steps[0])

    def lon_lat_to_km(self, lon, lat):
        """
        Convert longitude and latitude to x, y coordinates in kilometers.

        Args:
            lon (float): Longitude in degrees
            lat (float): Latitude in degrees

        Returns:
            tuple: (x_km, y_km) coordinates
        """
        # Map from [min_lon, max_lon] to [0, width] and [min_lat, max_lat] to [0, height]
        x_km = ((lon - self.min_lon) / (self.max_lon - self.min_lon)) * self.width
        y_km = ((lat - self.min_lat) / (self.max_lat - self.min_lat)) * self.height
        return x_km, y_km

    def km_to_lon_lat(self, x_km, y_km):
        """
        Convert x, y coordinates in kilometers to longitude and latitude.
        
        Args:
            x_km (float): X coordinate in kilometers
            y_km (float): Y coordinate in kilometers
            
        Returns:
            tuple: (lon, lat) coordinates
        """
        # Map from [0, width] to [min_lon, max_lon] and [0, height] to [min_lat, max_lat]
        lon = self.min_lon + (x_km / self.width) * (self.max_lon - self.min_lon)
        lat = self.min_lat + (y_km / self.height) * (self.max_lat - self.min_lat)
        return lon, lat
        # Update cluster positions and properties
        self._update_clusters()
        
        # Update the numpy array for optimized calculations
        self.cluster_array = np.array(self.clusters)
        
        # Recalculate densities based on new cluster positions
        # For efficiency, only update a small portion of the grid each step
        update_fraction = 0.05  # Update only 5% of the grid each step
        
        # Use numpy for faster operations
        if len(self.particle_map) > 0:
            keys = list(self.particle_map.keys())
    def step(self):
        """
        Update the particle distribution for one time step.
        """
        # Update the particle distribution from zarr file
        self._update_particles_from_zarr()
        
    def _update_wind(self):
        """
        Update wind direction for this time step.
        Wind direction changes gradually over time, but speed remains constant at 0.5 knots.
        """
        # Since we're using zarr files, we don't need to update wind
        # The particle positions are already pre-calculated
        pass

    def km_to_lon_lat(self, x_km, y_km):
        """
        Convert x, y coordinates in kilometers to longitude and latitude.

        Args:
            x_km (float): X coordinate in kilometers
            y_km (float): Y coordinate in kilometers

        Returns:
            tuple: (lon, lat) coordinates in degrees
        """
        # Map from [0, width] to [min_lon, max_lon] and [0, height] to [min_lat, max_lat]
        lon = self.min_lon + (x_km / self.width) * (self.max_lon - self.min_lon)
        lat = self.min_lat + (y_km / self.height) * (self.max_lat - self.min_lat)
        return lon, lat

    def get_particle_positions(self, center_x, center_y, radius):
        """
        Get individual particle positions within a radius of the given center point.

        Args:
            center_x (float): Center X coordinate in kilometers
            center_y (float): Center Y coordinate in kilometers
            radius (float): Radius to search within in kilometers

        Returns:
            list: List of (x_km, y_km) tuples for particles in the area
        """
        particles = []
        resolution = 0.1  # 100m resolution

        for x in np.arange(center_x - radius, center_x + radius, resolution):
            for y in np.arange(center_y - radius, center_y + radius, resolution):
                density = self._calculate_density_at_point(x, y)
                # Convert density to number of particles (simplified)
                num_particles = int(density * 10)  # Scale factor

                # Add random offset to spread particles
                for _ in range(num_particles):
                    particle_x = x + np.random.uniform(-resolution / 2, resolution / 2)
                    particle_y = y + np.random.uniform(-resolution / 2, resolution / 2)
                    if ((particle_x - center_x) ** 2 +
                            (particle_y - center_y) ** 2 <= radius ** 2):
                        particles.append((particle_x, particle_y))

        return particles

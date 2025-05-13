import random
import math
import numpy as np
from actor import Actor

class OceanMap(Actor):
    """
    Represents the ocean environment with particle distribution.
    """
    def __init__(self, width=100.0, height=100.0, particle_density=0.5, num_clusters=8, seed=None):
        """
        Initialize an OceanMap with dimensions and particle distribution.
        
        Args:
            width (float): Width of the map
            height (float): Height of the map
            particle_density (float): Base density of particles (0.0 to 1.0)
            num_clusters (int): Number of high-density clusters to generate
        """
        super().__init__(0.0, 0.0)  # Position not relevant for the map
        self.width = width
        self.height = height
        self.base_density = particle_density
        self.particle_map = {}  # Will store density values for different regions
        self.grid_size = 1  # Higher resolution grid (1x1 units)
        self.num_clusters = num_clusters
        self.clusters = []  # Will store (x, y, strength, radius) for each cluster
        
        # Set random seed for reproducibility if provided
        self.seed = seed if seed is not None else random.randint(1, 1000000)
        self.random_state = random.Random(self.seed)
        print(f"Using ocean particle seed: {self.seed}")
        
        # Track processed particles (where particles have been removed)
        self.processed_particles = {}  # Will store grid cells where particles have been processed
        
        # Wind parameters for particle drift
        self.wind_direction = self.random_state.uniform(0, 2 * math.pi)  # Random initial wind direction in radians
        self.wind_speed = 0.093  # Wind speed (0.5 knots ≈ 0.093 km per step)
        self.wind_change_rate = 0.05  # How quickly wind direction can change
        
        # Initialize with clustered particle distribution
        self._initialize_particle_map()
        
    def step(self):
        """
        Update the particle distribution for one time step.
        """
        # For now, just slightly randomize the particle distribution
        self._update_particle_map()
        
    def get_particles_in_area(self, polygon):
        """
        Get the density of particles in a specified area.
        Takes into account areas where particles have been processed (removed).
        Optimized for performance.
        
        Args:
            polygon (list): List of (lat, long) points defining the area to check
            
        Returns:
            float: Density of particles in the area (0.0 to 1.0)
        """
        # For simplicity, we'll just use the center point of the polygon
        # In a real implementation, this would calculate the actual intersection
        center_lat = sum(p[0] for p in polygon) / len(polygon)
        center_long = sum(p[1] for p in polygon) / len(polygon)
        
        # Get the density at this point using the higher resolution grid
        grid_x = int(center_lat / self.grid_size)
        grid_y = int(center_long / self.grid_size)
        key = (grid_x, grid_y)
        
        # Use cached values when possible for better performance
        # Check if this area has been processed (particles removed)
        if key in self.processed_particles:
            # Return the reduced density after processing
            return self.processed_particles[key]
        elif key in self.particle_map:
            return self.particle_map[key]
        else:
            # For points outside the grid, calculate density based on distance to clusters
            density = self._calculate_density_at_point(center_lat, center_long)
            # Cache the result for future lookups
            self.particle_map[key] = density
            return density
            
    def _batch_calculate_densities(self, lats, longs):
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
            
    def process_particles_at_location(self, lat, long, amount):
        """
        Process (remove) particles at a specific location.
        
        Args:
            lat (float): Latitude position
            long (float): Longitude position
            amount (float): Amount of particles to process (0.0 to 1.0)
        """
        # Get the grid cell for this location
        grid_x = int(lat / self.grid_size)
        grid_y = int(long / self.grid_size)
        key = (grid_x, grid_y)
        
        # Get current density
        if key in self.particle_map:
            current_density = self.particle_map[key]
        else:
            current_density = self._calculate_density_at_point(lat, long)
            self.particle_map[key] = current_density
        
        # Calculate how much can be processed (can't process more than exists)
        processable = min(amount, current_density)
        
        # Reduce density by the processed amount
        new_density = max(0.0, current_density - processable)
        self.processed_particles[key] = new_density
        
        # Also process neighboring cells with a falloff effect
        # This creates a more natural "cleaned up" area around the processing point
        for dx in range(-2, 3):
            for dy in range(-2, 3):
                if dx == 0 and dy == 0:
                    continue  # Skip the center cell (already processed)
                
                neighbor_key = (grid_x + dx, grid_y + dy)
                
                # Calculate distance-based falloff (closer cells are processed more)
                distance = math.sqrt(dx*dx + dy*dy)
                falloff = max(0.0, 1.0 - (distance / 3.0))
                
                # Get current density at neighbor
                if neighbor_key in self.particle_map:
                    neighbor_density = self.particle_map[neighbor_key]
                else:
                    neighbor_lat = (grid_x + dx) * self.grid_size
                    neighbor_long = (grid_y + dy) * self.grid_size
                    neighbor_density = self._calculate_density_at_point(neighbor_lat, neighbor_long)
                
                # Check if this neighbor has already been processed
                if neighbor_key in self.processed_particles:
                    neighbor_density = self.processed_particles[neighbor_key]
                
                # Process a portion of the neighbor's density based on falloff
                neighbor_processable = min(processable * falloff, neighbor_density)
                new_neighbor_density = max(0.0, neighbor_density - neighbor_processable)
                self.processed_particles[neighbor_key] = new_neighbor_density
        
        return processable
        
    def _initialize_particle_map(self):
        """
        Initialize the particle distribution map with clustered density patterns.
        Creates high-density clusters surrounded by gradually decreasing density.
        """
        # Generate random cluster centers
        self._generate_clusters()
        
        # Create the high-resolution grid
        for x in range(int(self.width / self.grid_size)):
            for y in range(int(self.height / self.grid_size)):
                # Calculate actual lat/long position
                lat = x * self.grid_size
                long = y * self.grid_size
                
                # Calculate density based on distance to cluster centers
                density = self._calculate_density_at_point(lat, long)
                self.particle_map[(x, y)] = density
    
    def _generate_clusters(self):
        """
        Generate random clusters of high particle density.
        Each cluster has a center position, strength, and radius.
        Creates smaller, more numerous clusters.
        """
        self.clusters = []
        for _ in range(self.num_clusters):
            # Random position within the map
            x = self.random_state.uniform(0, self.width)
            y = self.random_state.uniform(0, self.height)
            
            # Random strength (maximum density at center)
            strength = self.random_state.uniform(0.7, 1.0)
            
            # Smaller radius of influence
            radius = self.random_state.uniform(3.0, 8.0)  # Reduced from 5.0-20.0 to create smaller clusters
            
            self.clusters.append((x, y, strength, radius))
        
        # Create a numpy array for optimized calculations
        self.cluster_array = np.array(self.clusters)
    
    def _calculate_density_at_point(self, lat, long):
        """
        Calculate particle density at a specific point based on distance to clusters.
        Optimized for performance with simplified calculations.
        
        Args:
            lat (float): Latitude position
            long (float): Longitude position
            
        Returns:
            float: Density value between 0.0 and 1.0
        """
        # Start with base density
        density = self.base_density
        
        # Simple loop-based calculation - often faster for small numbers of clusters
        for cluster_x, cluster_y, strength, radius in self.clusters:
            # Calculate distance to cluster center
            dx = lat - cluster_x
            dy = long - cluster_y
            distance_squared = dx*dx + dy*dy
            radius_3x_squared = (radius * 3) ** 2
            
            # Calculate density contribution using Gaussian distribution
            if distance_squared < radius_3x_squared:  # Only consider points within 3x radius
                # Gaussian falloff from center - avoid sqrt for performance
                contribution = strength * math.exp(-distance_squared / (2 * radius*radius))
                density += contribution
        
        # Ensure density is between 0.0 and 1.0
        return max(0.0, min(1.0, density))
                
    def _update_particle_map(self):
        """
        Update the particle distribution map for one time step.
        Clusters slowly drift and evolve over time.
        Optimized for better performance.
        """
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
            num_to_update = int(len(keys) * update_fraction)
            
            if num_to_update > 0:
                # Sample keys to update - using sample() for Python's random module
                indices = self.random_state.sample(range(len(keys)), num_to_update)
                keys_to_update = [keys[i] for i in indices]
                
                # Update the particle map with calculated densities - direct calculation is faster
                # than the multiprocessing overhead for small batches
                for key in keys_to_update:
                    lat = key[0] * self.grid_size
                    long = key[1] * self.grid_size
                    self.particle_map[key] = self._calculate_density_at_point(lat, long)
    
    def step(self):
        """
        Update the particle distribution for one time step.
        """
        # Update wind direction and speed
        self._update_wind()
        
        # Update the particle distribution
        self._update_particle_map()
        
    def _update_wind(self):
        """
        Update wind direction for this time step.
        Wind direction changes gradually over time, but speed remains constant at 0.5 knots.
        """
        # Gradually change wind direction
        direction_change = self.random_state.uniform(-self.wind_change_rate, self.wind_change_rate)
        self.wind_direction = (self.wind_direction + direction_change) % (2 * math.pi)
        
        # Wind speed remains constant at 0.5 knots (0.093 km per step)
        # No speed changes to maintain realistic simulation
    
    def _update_clusters(self):
        """
        Update cluster positions and properties for dynamic behavior.
        Clusters drift according to wind direction and speed.
        """
        for i, (x, y, strength, radius) in enumerate(self.clusters):
            # Drift primarily according to wind direction with some randomness
            # Wind component (80% of movement)
            wind_x = self.wind_speed * math.cos(self.wind_direction) * 0.8
            wind_y = self.wind_speed * math.sin(self.wind_direction) * 0.8
            
            # Random component (20% of movement)
            random_angle = self.random_state.uniform(0, 2 * math.pi)
            random_speed = self.random_state.uniform(0, 0.1)
            random_x = random_speed * math.cos(random_angle) * 0.2
            random_y = random_speed * math.sin(random_angle) * 0.2
            
            # Combined drift
            new_x = x + wind_x + random_x
            new_y = y + wind_y + random_y
            
            # Handle map boundaries - clusters that drift off one edge appear on the opposite edge
            new_x = new_x % self.width
            new_y = new_y % self.height
            
            # Slowly change strength
            new_strength = strength + self.random_state.uniform(-0.02, 0.02)
            new_strength = max(0.5, min(1.0, new_strength))
            
            # Slowly change radius
            new_radius = radius + self.random_state.uniform(-0.1, 0.1)
            new_radius = max(2.0, min(10.0, new_radius))  # Keep radius within smaller bounds
            
            # Update cluster
            self.clusters[i] = (new_x, new_y, new_strength, new_radius)

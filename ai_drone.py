from actor import Actor
import math
import random
import numpy as np

class AIDrone(Actor):
    """
    An intelligent drone that dynamically adjusts its path to find the most plastic particles.
    Uses a combination of exploration and exploitation strategies to optimize particle detection.
    Avoids revisiting areas where particles have already been discovered and processed.
    Coordinates with other drones to avoid overlapping search areas and focuses on discovered clusters.
    """
    def __init__(self, x_km, y_km, scan_radius, min_x, max_x, min_y, max_y, step_size=1.0, drone_id=None):
        """
        Initialize an AI drone with dynamic path planning.
        
        Args:
            x_km (float): Initial X position in kilometers from the left edge
            y_km (float): Initial Y position in kilometers from the bottom edge
            scan_radius (float): Radius of the drone's scanning area in kilometers
            min_x (float): Minimum X boundary in kilometers
            max_x (float): Maximum X boundary in kilometers
            min_y (float): Minimum Y boundary in kilometers
            max_y (float): Maximum Y boundary in kilometers
            step_size (float): Distance the drone moves in each step in kilometers
            drone_id (int, optional): Unique identifier for the drone
        """
        super().__init__(x_km, y_km)
        self.scan_radius = scan_radius
        self.min_x = min_x
        self.max_x = max_x
        self.min_y = min_y
        self.max_y = max_y
        self.step_size = step_size
        self.drone_id = drone_id if drone_id is not None else id(self)
        
        # Target position for the next move
        self.target_x = None
        self.target_y = None
        
        # Particle data for the catching system
        self.particle_data = None
        
        # Current heading (in radians, 0 = East, π/2 = North, etc.)
        self.current_heading = random.uniform(0, 2 * math.pi)
        
        # Memory of scanned areas and detected particles
        self.scan_memory = []  # List of (lat, long, density) tuples
        self.density_map = {}  # Grid-based density map
        self.visited_cells = set()  # Set of visited grid cells
        self.processed_cells = set()  # Set of grid cells where particles were processed
        
        # Grid size for discretizing the map
        self.grid_size = 1.0  # 1 km grid cells
        
        # Exploration parameters
        self.exploration_radius = 10.0  # Radius to look for unexplored areas
        self.exploitation_threshold = 0.5  # Density threshold to switch to exploitation
        self.consecutive_low_density_scans = 0  # Counter for low density scans
        self.low_density_threshold = 0.2  # Threshold to consider a scan as low density
        self.max_low_density_scans = 5  # Max consecutive low density scans before forced exploration
        
        # Momentum parameters to maintain straighter paths
        self.consecutive_steps_same_direction = 0
        self.max_straight_steps = 10  # Maximum steps in the same direction before changing
        self.momentum = 0.8  # Momentum factor (0-1) - higher values maintain direction
        self.turn_smoothness = 0.7  # How smooth turns should be (0-1) - higher is smoother
        
        # Coordination with other drones
        self.other_drone_positions = {}  # {drone_id: (lat, long)}
        
        # Assign a sector preference based on drone ID
        # This helps distribute drones across the map
        # Sectors: 0=SW, 1=SE, 2=NW, 3=NE
        self.sector_preference = self.drone_id % 4 if isinstance(self.drone_id, int) else random.randint(0, 3)
        
        # Calculate sector boundaries
        self.sector_boundaries = self._calculate_sector_boundaries()
        
        # Penalties for revisiting areas
        self.revisit_penalty = 0.7  # Penalty factor for revisiting cells (lower = stronger penalty)
        self.visited_area_penalty = 0.5  # Penalty factor for areas around visited cells
        
        # Particle cluster tracking
        self.active_clusters = {}  # {cluster_id: (center_lat, center_long, last_density, steps_since_update)}
        self.cluster_id_counter = 0  # Counter for generating unique cluster IDs
        self.cluster_radius = 3.0  # Radius to consider as part of the same cluster (in grid cells)
        self.min_cluster_density = 0.8  # Minimum density to consider as a cluster
        self.cluster_timeout = 10  # Steps to keep tracking a cluster without updates
        
        # Coordination parameters
        self.assigned_clusters = set()  # Clusters this drone is responsible for
        self.drone_avoidance_radius = 5.0  # Radius to avoid other drones (in grid cells)
        self.drone_coordination_weight = 0.8  # Weight for drone coordination (0-1)
        self.last_position_broadcast = 0  # Step counter for position broadcasts
        self.broadcast_interval = 3  # Steps between position broadcasts
        
        # Exploration vs exploitation balance
        self.exploration_weight = 0.7  # Initial weight for exploration (vs exploitation)
        self.min_exploration_weight = 0.3  # Minimum exploration weight
        self.exploitation_success_counter = 0  # Counter for successful exploitations
        
        # Initialize the density map with some random values
        self._initialize_density_map()
        
    def step(self, ocean_map):
        """
        Move the drone using AI-driven path planning and scan the area.
        Implements cluster tracking, anti-sticking behavior, and coordinates with other drones.
        
        Args:
            ocean_map (OceanMap): The ocean map to scan
            
        Returns:
            float: Density of particles in the scanned area
        """
        # Broadcast position to other drones periodically
        self.last_position_broadcast += 1
        if self.last_position_broadcast >= self.broadcast_interval:
            self.last_position_broadcast = 0
            # This would trigger a position update to other drones
            # The actual update happens in the update_drone_positions method
        
        # Scan the current area
        # Create a circular polygon around the drone's position
        polygon = []
        num_points = 8  # Number of points to approximate the circle
        for i in range(num_points):
            angle = 2 * math.pi * i / num_points
            x = self.x_km + self.scan_radius * math.cos(angle)
            y = self.y_km + self.scan_radius * math.sin(angle)
            polygon.append((x, y))
        
        # Get the particle density in the scanned area
        current_density = ocean_map.get_particles_in_area(polygon)
        
        # Set particle data for the catching system
        self.particle_data = current_density
        
        # Update memory with scan results
        self._update_memory(current_density)
        
        # Update clusters based on current scan
        found_cluster = self._identify_clusters(current_density)
        self._update_clusters()
        
        # Plan the next movement based on scan results and cluster tracking
        self._plan_movement(ocean_map)
        
        # Move to the target position
        self._move_to_target()
        
        return current_density
    
    def update_drone_positions(self, drones):
        """
        Update knowledge of other drone positions for coordination and share cluster information.
        This enables drones to coordinate exploration and exploitation efforts.
        
        Args:
            drones (list): List of all drones in the simulation
        """
        # Clear previous positions
        self.other_drone_positions = {}
        
        # Update with current positions of other drones and share cluster information
        for drone in drones:
            if drone.drone_id != self.drone_id and isinstance(drone, AIDrone):
                # Store position for coordination
                self.other_drone_positions[drone.drone_id] = (drone.x_km, drone.y_km)
                
                # Share cluster information
                self._share_cluster_info(drone)
                
                # Coordinate sector assignments based on drone ID
                # This ensures drones focus on different areas of the map
                if drone.sector_preference == self.sector_preference:
                    # If two drones have the same sector preference, the one with the lower ID
                    # keeps it, and the other gets reassigned to a less crowded sector
                    if self.drone_id > drone.drone_id:
                        # Count drones in each sector
                        sector_counts = [0, 0, 0, 0]
                        for other_drone in drones:
                            if isinstance(other_drone, AIDrone):
                                sector_counts[other_drone.sector_preference] += 1
                        
                        # Find the least crowded sector
                        min_count = min(sector_counts)
                        least_crowded_sectors = [i for i, count in enumerate(sector_counts) if count == min_count]
                        
                        # Assign to a least crowded sector that's not the current one
                        new_sectors = [s for s in least_crowded_sectors if s != self.sector_preference]
                        if new_sectors:
                            self.sector_preference = random.choice(new_sectors)
                            # Recalculate sector boundaries
                            self.sector_boundaries = self._calculate_sector_boundaries()
    
    def _initialize_density_map(self):
        """
        Initialize the density map with some random values.
        This gives the AI drone some initial data to work with.
        """
        # Initialize with some random values for exploration
        for _ in range(10):
            grid_x = random.randint(int(self.min_x / self.grid_size), int(self.max_x / self.grid_size) - 1)
            grid_y = random.randint(int(self.min_y / self.grid_size), int(self.max_y / self.grid_size) - 1)
            grid_cell = (grid_x, grid_y)
            self.density_map[grid_cell] = random.uniform(0.0, 0.3)  # Low random values
    
    def _update_memory(self, current_density):
        """
        Update the drone's memory with the current scan result.
        
        Args:
            current_density (float): Density of particles at current position
        """
        # Add current scan to memory
        self.scan_memory.append((self.x_km, self.y_km, current_density))
        
        # Keep memory at a reasonable size (last 50 scans)
        max_memory_size = 50
        if len(self.scan_memory) > max_memory_size:
            self.scan_memory.pop(0)
        
        # Update density map and mark cell as visited
        grid_x = int(self.x_km / self.grid_size)
        grid_y = int(self.y_km / self.grid_size)
        grid_cell = (grid_x, grid_y)
        
        self.density_map[grid_cell] = current_density
        self.visited_cells.add(grid_cell)
        
        # If particles were processed here, mark the cell
        if current_density < 0.3:  # Threshold for considering particles processed
            self.processed_cells.add(grid_cell)
    
    def _calculate_sector_boundaries(self):
        """
        Calculate the boundaries of each sector based on the drone's sector preference.
        
        Returns:
            dict: Dictionary with min/max lat/long for the preferred sector
        """
        # Calculate midpoints
        mid_x = (self.min_x + self.max_x) / 2
        mid_y = (self.min_y + self.max_y) / 2
        
        # Define sector boundaries
        sectors = {
            0: {  # Southwest
                'min_x': self.min_x,
                'max_x': mid_x,
                'min_y': self.min_y,
                'max_y': mid_y
            },
            1: {  # Southeast
                'min_x': self.min_x,
                'max_x': mid_x,
                'min_y': mid_y,
                'max_y': self.max_y
            },
            2: {  # Northwest
                'min_x': mid_x,
                'max_x': self.max_x,
                'min_y': self.min_y,
                'max_y': mid_y
            },
            3: {  # Northeast
                'min_x': mid_x,
                'max_x': self.max_x,
                'min_y': mid_y,
                'max_y': self.max_y
            }
        }
        
        return sectors[self.sector_preference]
    
    def _identify_clusters(self, current_density):
        """
        Identify and track particle clusters based on scan results.
        
        Args:
            current_density (float): Current scan density
            
        Returns:
            bool: True if a significant cluster was found or updated
        """
        # Get current position in grid coordinates
        current_grid_x = int(self.x_km / self.grid_size)
        current_grid_y = int(self.y_km / self.grid_size)
        current_grid = (current_grid_x, current_grid_y)
        
        # Check if we found a significant cluster
        if current_density >= self.min_cluster_density:
            # Check if this is part of an existing cluster
            updated_existing = False
            
            for cluster_id, (center_lat, center_long, last_density, _) in list(self.active_clusters.items()):
                # Calculate distance to cluster center
                center_grid_x = int(center_lat / self.grid_size)
                center_grid_y = int(center_long / self.grid_size)
                
                grid_dx = current_grid_x - center_grid_x
                grid_dy = current_grid_y - center_grid_y
                grid_distance = math.sqrt(grid_dx*grid_dx + grid_dy*grid_dy)
                
                if grid_distance <= self.cluster_radius:
                    # Update existing cluster
                    # Use weighted average to update center position
                    weight = current_density / (current_density + last_density)
                    new_center_x = center_lat * (1 - weight) + self.x_km * weight
                    new_center_y = center_long * (1 - weight) + self.y_km * weight
                    
                    # Update with higher density if found
                    new_density = max(current_density, last_density)
                    
                    self.active_clusters[cluster_id] = (new_center_x, new_center_y, new_density, 0)
                    updated_existing = True
                    
                    # Add this cluster to our assigned clusters if it's not already
                    self.assigned_clusters.add(cluster_id)
                    break
            
            if not updated_existing:
                # Create a new cluster
                new_cluster_id = self.cluster_id_counter
                self.cluster_id_counter += 1
                self.active_clusters[new_cluster_id] = (self.x_km, self.y_km, current_density, 0)
                self.assigned_clusters.add(new_cluster_id)
            
            return True
        
        return False
    
    def _update_clusters(self):
        """
        Update the status of all tracked clusters and remove expired ones.
        """
        # Increment the steps_since_update for all clusters
        for cluster_id in list(self.active_clusters.keys()):
            center_lat, center_long, density, steps = self.active_clusters[cluster_id]
            
            # Increment steps since last update
            steps += 1
            
            if steps > self.cluster_timeout:
                # Cluster has expired, remove it
                self.active_clusters.pop(cluster_id)
                if cluster_id in self.assigned_clusters:
                    self.assigned_clusters.remove(cluster_id)
            else:
                # Update the cluster with incremented steps
                self.active_clusters[cluster_id] = (center_lat, center_long, density, steps)
    
    def _share_cluster_info(self, other_drone):
        """
        Share cluster information with another drone and coordinate cluster assignments.
        
        Args:
            other_drone (AIDrone): Another AI drone to share information with
        """
        if not hasattr(other_drone, 'active_clusters'):
            return
            
        # Share our clusters with the other drone
        for cluster_id, (center_lat, center_long, density, steps) in self.active_clusters.items():
            # Check if other drone already knows about this cluster
            other_has_similar = False
            
            for other_id, (other_lat, other_long, _, _) in other_drone.active_clusters.items():
                # Calculate distance between cluster centers
                dx = center_lat - other_lat
                dy = center_long - other_long
                distance = math.sqrt(dx*dx + dy*dy)
                
                if distance < self.cluster_radius * self.grid_size:
                    # Clusters are close enough to be considered the same
                    other_has_similar = True
                    
                    # Decide which drone should handle this cluster
                    # Based on distance and drone ID
                    my_distance = math.sqrt((self.x_km - center_lat)**2 + (self.y_km - center_long)**2)
                    other_distance = math.sqrt((other_drone.x_km - center_lat)**2 + (other_drone.y_km - center_long)**2)
                    
                    # If the other drone is significantly closer, let it handle the cluster
                    if other_distance < my_distance * 0.7:
                        if cluster_id in self.assigned_clusters:
                            self.assigned_clusters.remove(cluster_id)
                    # If we're significantly closer, we should handle it
                    elif my_distance < other_distance * 0.7:
                        if other_id in other_drone.assigned_clusters:
                            other_drone.assigned_clusters.remove(other_id)
                            self.assigned_clusters.add(cluster_id)
                    # If distances are similar, use drone ID to break ties
                    elif self.drone_id < other_drone.drone_id:
                        if other_id in other_drone.assigned_clusters:
                            other_drone.assigned_clusters.remove(other_id)
                            self.assigned_clusters.add(cluster_id)
                    else:
                        if cluster_id in self.assigned_clusters:
                            self.assigned_clusters.remove(cluster_id)
                    break
            
            # If other drone doesn't know about this cluster, share it
            if not other_has_similar and density > self.min_cluster_density:
                # Only share significant clusters
                other_drone.active_clusters[self.cluster_id_counter] = (center_lat, center_long, density, steps)
                self.cluster_id_counter += 1
        
        # Learn about clusters from the other drone
        for other_id, (other_lat, other_long, other_density, other_steps) in other_drone.active_clusters.items():
            # Check if we already know about this cluster
            we_have_similar = False
            
            for cluster_id, (center_lat, center_long, _, _) in self.active_clusters.items():
                # Calculate distance between cluster centers
                dx = other_lat - center_lat
                dy = other_long - center_long
                distance = math.sqrt(dx*dx + dy*dy)
                
                if distance < self.cluster_radius * self.grid_size:
                    # Already tracking a similar cluster
                    we_have_similar = True
                    break
            
            # If we don't know about this cluster, add it
            if not we_have_similar and other_density > self.min_cluster_density:
                self.active_clusters[self.cluster_id_counter] = (other_lat, other_long, other_density, other_steps)
                self.cluster_id_counter += 1
    
    def _plan_movement(self, ocean_map):
        """
        Plan the next movement based on scan results, cluster tracking, and coordination.
        Balances exploration and exploitation based on current conditions.
        
        Args:
            ocean_map (OceanMap): The ocean map to scan
        """
        # Check if we need to force exploration due to consecutive low density scans
        if len(self.scan_memory) > 0:
            last_density = self.scan_memory[-1][2]
            if last_density < self.low_density_threshold:
                self.consecutive_low_density_scans += 1
            else:
                self.consecutive_low_density_scans = 0
        
        # Force exploration if we've been in low density areas for too long
        if self.consecutive_low_density_scans >= self.max_low_density_scans:
            self._plan_forced_exploration()
            return
        
        # Decide between exploration and exploitation
        # If we have assigned clusters, prioritize exploitation
        if self.assigned_clusters and random.random() > self.exploration_weight:
            self._plan_exploitation(ocean_map)
        else:
            self._plan_exploration()
    
    def _plan_exploration(self):
        """
        Plan an exploratory move to discover new areas.
        Incorporates momentum for straighter paths and sector preferences.
        """
        # Get current position in grid coordinates
        current_grid_x = int(self.x_km / self.grid_size)
        current_grid_y = int(self.y_km / self.grid_size)
        current_grid = (current_grid_x, current_grid_y)
        
        # Calculate direction options with momentum
        direction_scores = {}
        
        # If we've been moving in the same direction for a while, consider changing
        if self.consecutive_steps_same_direction >= self.max_straight_steps:
            # Reset momentum counter to encourage direction change
            self.consecutive_steps_same_direction = 0
        
        # Calculate base step size with momentum bonus
        momentum_bonus = min(self.consecutive_steps_same_direction * 0.1, 0.5)
        current_step_size = self.step_size * (1 + momentum_bonus)
        
        # Define possible directions to consider
        # If maintaining momentum, limit angle choices
        if self.consecutive_steps_same_direction > 0:
            # Only consider forward and slight turns (±45°)
            angles = [self.current_heading - math.pi/4, self.current_heading, self.current_heading + math.pi/4]
        else:
            # Consider all 8 directions
            angles = [i * math.pi/4 for i in range(8)]
        
        for angle in angles:
            # Calculate potential new position
            new_x = self.x_km + current_step_size * math.cos(angle)
            new_y = self.y_km + current_step_size * math.sin(angle)
            
            # Check if the new position is within bounds
            if not (self.min_x <= new_x <= self.max_x and self.min_y <= new_y <= self.max_y):
                continue
            
            # Calculate grid coordinates for the new position
            new_grid_x = int(new_x / self.grid_size)
            new_grid_y = int(new_y / self.grid_size)
            new_grid = (new_grid_x, new_grid_y)
            
            # Start with a base score
            score = 1.0
            
            # Add momentum bonus for continuing in the same direction
            angle_diff = min(abs(angle - self.current_heading), 2 * math.pi - abs(angle - self.current_heading))
            momentum_factor = 1.0 - angle_diff / math.pi  # 1.0 for same direction, 0.0 for opposite
            score += momentum_factor * self.momentum
            
            # Penalty for revisiting cells
            if new_grid in self.visited_cells:
                score *= self.revisit_penalty
            
            # Penalty for cells near visited cells
            for dx in [-1, 0, 1]:
                for dy in [-1, 0, 1]:
                    if (new_grid_x + dx, new_grid_y + dy) in self.visited_cells:
                        score *= self.visited_area_penalty
            
            # Bonus for moving toward preferred sector
            sector = self.sector_boundaries
            sector_center_x = (sector['min_x'] + sector['max_x']) / 2
            sector_center_y = (sector['min_y'] + sector['max_y']) / 2
            
            # Calculate vector toward sector center
            sector_dx = sector_center_x - self.x_km
            sector_dy = sector_center_y - self.y_km
            sector_angle = math.atan2(sector_dy, sector_dx)
            
            # Bonus for moving toward sector center
            sector_angle_diff = min(abs(angle - sector_angle), 2 * math.pi - abs(angle - sector_angle))
            sector_alignment = 1.0 - sector_angle_diff / math.pi  # 1.0 for same direction, 0.0 for opposite
            score += sector_alignment * 0.5  # Sector preference bonus
            
            # Penalty for moving toward other drones
            for other_drone_id, (other_x, other_y) in self.other_drone_positions.items():
                # Calculate distance to other drone
                drone_dx = other_x - new_x
                drone_dy = other_y - new_y
                drone_distance = math.sqrt(drone_dx*drone_dx + drone_dy*drone_dy)
                
                # Apply penalty if too close to another drone
                if drone_distance < self.drone_avoidance_radius * self.grid_size:
                    avoidance_factor = drone_distance / (self.drone_avoidance_radius * self.grid_size)
                    score *= avoidance_factor * self.drone_coordination_weight
            
            # Store the score for this direction
            direction_scores[angle] = score
        
        # Choose the direction with the highest score
        if direction_scores:
            best_angle = max(direction_scores.items(), key=lambda x: x[1])[0]
            
            # Update heading and consecutive steps counter
            if abs(best_angle - self.current_heading) < 0.1:  # Almost same direction
                self.consecutive_steps_same_direction += 1
            else:
                self.consecutive_steps_same_direction = 0
            
            self.current_heading = best_angle
            
            # Set target position
            self.target_x = self.x_km + current_step_size * math.cos(best_angle)
            self.target_y = self.y_km + current_step_size * math.sin(best_angle)
            
            # Ensure target is within bounds
            self.target_x = max(self.min_x, min(self.max_x, self.target_x))
            self.target_y = max(self.min_y, min(self.max_y, self.target_y))
        else:
            # If no valid direction found, just move randomly within bounds
            self._plan_random_move()
    
    def _plan_exploitation(self, ocean_map):
        """
        Plan a move toward areas with high expected particle density.
        Focuses on assigned clusters and avoids other drones.
        
        Args:
            ocean_map (OceanMap): The ocean map to scan
        """
        # Find the best cluster to exploit
        best_cluster_id = None
        best_cluster_score = -1
        
        for cluster_id in self.assigned_clusters:
            if cluster_id in self.active_clusters:
                center_lat, center_long, density, steps = self.active_clusters[cluster_id]
                
                # Calculate distance to cluster
                dx = center_lat - self.x_km
                dy = center_long - self.y_km
                distance = math.sqrt(dx*dx + dy*dy)
                
                # Score based on density and distance
                # Prefer high density and close clusters
                score = density / (1 + distance * 0.1)
                
                # Penalty for clusters that other drones are already handling
                for other_drone_id, (other_x, other_y) in self.other_drone_positions.items():
                    other_dx = center_lat - other_x
                    other_dy = center_long - other_y
                    other_distance = math.sqrt(other_dx*other_dx + other_dy*other_dy)
                    
                    # If another drone is closer to this cluster, reduce our score
                    if other_distance < distance * 0.8:
                        score *= 0.5
                
                if score > best_cluster_score:
                    best_cluster_score = score
                    best_cluster_id = cluster_id
        
        if best_cluster_id is not None:
            # Move toward the best cluster
            center_lat, center_long, _, _ = self.active_clusters[best_cluster_id]
            
            # Calculate direction to cluster center
            dx = center_lat - self.x_km
            dy = center_long - self.y_km
            angle = math.atan2(dy, dx)
            
            # Add some randomness to explore the cluster area
            angle += random.uniform(-math.pi/6, math.pi/6)  # ±30 degrees
            
            # Calculate step size - smaller steps when close to the cluster
            distance = math.sqrt(dx*dx + dy*dy)
            step_size = min(self.step_size, max(distance * 0.5, self.step_size * 0.5))
            
            # Set target position
            self.target_x = self.x_km + step_size * math.cos(angle)
            self.target_y = self.y_km + step_size * math.sin(angle)
            
            # Ensure target is within bounds
            self.target_x = max(self.min_x, min(self.max_x, self.target_x))
            self.target_y = max(self.min_y, min(self.max_y, self.target_y))
            
            # Update heading
            self.current_heading = angle
            
            # Reset consecutive steps counter to encourage exploration within the cluster
            self.consecutive_steps_same_direction = 0
            
            # Increment exploitation success counter
            self.exploitation_success_counter += 1
            
            # Adjust exploration weight based on success
            if self.exploitation_success_counter > 5:
                # Reduce exploration weight to focus more on exploitation
                self.exploration_weight = max(self.min_exploration_weight, self.exploration_weight - 0.05)
                self.exploitation_success_counter = 0
        else:
            # No good clusters to exploit, fall back to exploration
            self._plan_exploration()
            
            # Increase exploration weight
            self.exploration_weight = min(0.7, self.exploration_weight + 0.05)
    
    def _plan_forced_exploration(self):
        """
        Plan a move to force exploration away from current area.
        Used when the drone is stuck in a low-density area.
        """
        # Reset the consecutive low density counter
        self.consecutive_low_density_scans = 0
        
        # Choose a direction that's significantly different from current heading
        # but not completely opposite (to maintain some momentum)
        angle_change = random.uniform(math.pi/2, math.pi)  # 90 to 180 degrees
        if random.random() < 0.5:
            angle_change = -angle_change
        
        new_angle = self.current_heading + angle_change
        # Normalize to [0, 2π)
        new_angle = new_angle % (2 * math.pi)
        
        # Use a larger step size to escape the area quickly
        escape_step_size = self.step_size * 1.5
        
        # Set target position
        self.target_x = self.x_km + escape_step_size * math.cos(new_angle)
        self.target_y = self.y_km + escape_step_size * math.sin(new_angle)
        
        # Ensure target is within bounds
        self.target_x = max(self.min_x, min(self.max_x, self.target_x))
        self.target_y = max(self.min_y, min(self.max_y, self.target_y))
        
        # Update heading
        self.current_heading = new_angle
        
        # Set consecutive steps to encourage continued straight movement
        self.consecutive_steps_same_direction = 3
    
    def _plan_random_move(self):
        """
        Plan a random move within bounds.
        Used as a fallback when other planning methods fail.
        """
        # Choose a random angle
        angle = random.uniform(0, 2 * math.pi)
        
        # Set target position
        self.target_x = self.x_km + self.step_size * math.cos(angle)
        self.target_y = self.y_km + self.step_size * math.sin(angle)
        
        # Ensure target is within bounds
        self.target_x = max(self.min_x, min(self.max_x, self.target_x))
        self.target_y = max(self.min_y, min(self.max_y, self.target_y))
        
        # Update heading
        self.current_heading = angle
        
        # Reset consecutive steps counter
        self.consecutive_steps_same_direction = 0
    
    def _move_to_target(self):
        """
        Move the drone to the target position.
        """
        if self.target_x is not None and self.target_y is not None:
            self.x_km = self.target_x
            self.y_km = self.target_y
            
    def _create_scan_polygon(self):
        """
        Create a polygon representing the drone's scan area for visualization.
        
        Returns:
            list: List of (lat, long) tuples forming a polygon
        """
        polygon = []
        num_points = 16  # More points for smoother circle
        for i in range(num_points):
            angle = 2 * math.pi * i / num_points
            x = self.x_km + self.scan_radius * math.cos(angle)
            y = self.y_km + self.scan_radius * math.sin(angle)
            polygon.append((x, y))
        return polygon

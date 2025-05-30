import math
import numpy as np
from actor import Actor

class CatchingSystem(Actor):
    """
    Represents a mobile system for catching plastic in the ocean detected by drones.
    Can move slowly and uses a greedy algorithm to navigate toward high-density areas.
    """
    def __init__(self, dt=300.0, x_km=0.0, y_km=0.0, move_speed=2.78, max_turn_angle=15, 
                 system_span=1.4, retention_efficiency=0.5, strategy="drone"):
        """
        Initialize a CatchingSystem with position and movement capabilities.
        The system has unlimited capacity for plastic collection.
        
        Args:
            dt (float): total number seconds per step 
            x_km (float): X position in kilometers from the left edge
            y_km (float): Y position in kilometers from the bottom edge
            move_speed (float): Maximum movement speed over ground per step (km/h)
            max_turn_angle (float): Maximum turning angle per step in degrees (°/h) - 45 degrees per 3 hours
            system_span (float): Width of the system in kilometers for plastic collection (default: 1.4 km)
            retention_efficiency (float): Efficiency of the system in retaining plastic (0.0 to 1.0)
        """
        super().__init__(x_km, y_km)
        self.current_load = 0.0  # Plastic collected in current step
        self.total_collected = 0.0  # Total plastic collected over time
        
        # Movement parameters
        dt_step = dt/3600 
        self.move_speed = move_speed*dt_step  # Speed over ground (km/h)
        self.max_turn_angle = max_turn_angle*dt_step
        self.heading = 0.0  # Degrees, 0 = North, 90 = East, etc.
        
        # Plastic collection parameters
        self.system_span = system_span  # Width of the system in kilometers
        self.retention_efficiency = retention_efficiency  # Efficiency in retaining plastic
        
        # Historical data tracking
        self.historical_data = []  # Will store (x_km, y_km, density) tuples
        self.target_position = None  # Target position to move toward

        self.strategy = strategy  # NEW: movement strategy

        # FIXME 
        self._update_counter = 0  # Counter for controlling update frequency
        self._update_interval = 12  # Update every 12 steps (1 hour)
        
    def step(self, drones, ocean_map):
        """
        Update the catching system for one time step.
        Collects data from drones, calculates plastic collection, and moves toward high-density areas.
        
        Args:
            drones (list): List of Drone objects to interact with
            ocean_map (OceanMap): Ocean map with current information for ground truth data
            
        Returns:
            float: Amount of plastic collected in this step
        """
        # Store reference to ocean_map for use in other methods
        self.ocean_map = ocean_map
        
        # Reset current load for this step
        self.current_load = 0.0
        
        # Collect historical data from all drones for navigation purposes
        self._collect_historical_data(drones)
        
        # PLASTIC COLLECTION: Use ground truth data for accurate collection calculation
        # Calculate plastic collection based on the formula:
        # Plastic catch = (Speed Through Water) * (System Span) * (Retention Efficiency) * (Encountered Plastic Density)
        
        # Get the actual plastic density from ground truth data
        plastic_density = self._get_ground_truth_plastic_density(ocean_map)
        
        if plastic_density > 0:
            # Calculate speed through water (accounting for currents)
            # For simplicity, we'll assume currents are minimal and speed through water ≈ speed over ground
            # In a more complex simulation, we would calculate this based on current vectors
            speed_through_water = self.move_speed  # km/h
            
            # Calculate plastic catch using the formula
            # Units: (km/h) * (km) * (efficiency) * (density) = (km²/h) * density * efficiency
            plastic_collected = speed_through_water * self.system_span * self.retention_efficiency * plastic_density
            
            # Update collection totals
            self.current_load = plastic_collected
            self.total_collected += plastic_collected
        
        # STRATEGY-BASED MOVEMENT
        if self.strategy == "random":
            self._update_movement_target_random()
        elif self.strategy == "drone":
            # NAVIGATION: Use only drone-observed data for navigation decisions
            # This ensures the system only uses information it could realistically have access to
            # Determine where to move next using greedy algorithm based on observed data
            self._update_movement_target_greedy()
        elif self.strategy == "optimal":
            self._update_movement_target_optimal(ocean_map)
        else:
            raise ValueError(f"Unknown strategy: {self.strategy}")
        
        # Move toward the target
        self._move_toward_target()
                    
        return self.current_load
        
    def _get_current_plastic_density(self, drones, ocean_map):
        """
        Get the plastic density at the current location of the system.
        This is a dispatcher method that calls the appropriate specialized method.
        
        For plastic catch calculation: Uses ground truth data from ocean_map.
        For navigation decisions: Uses only data from drones or historical data.
        
        Args:
            drones (list): List of Drone objects to get data from
            ocean_map (OceanMap): Ocean map with ground truth data
            
        Returns:
            float: Plastic density at the current location (0.0 to 1.0)
        """
        # For plastic catch calculation, always use ground truth data
        return self._get_ground_truth_plastic_density(ocean_map)
    
    def _get_ground_truth_plastic_density(self, ocean_map):
        """
        Get the actual plastic density at the current location using ground truth data.
        This method is used for accurate plastic collection calculation.
        
        Args:
            ocean_map (OceanMap): Ocean map with ground truth data
            
        Returns:
            float: Actual plastic density at the current location (0.0 to 1.0)
        """
        # Create a single-point polygon at the system's position
        # This ensures we only check if the center point of particles is within the system span
        # The system span is still used in the plastic collection formula
        point = [(self.x_km, self.y_km)]
        
        # Since ocean_map.get_particles_in_area expects a polygon, we'll create a minimal polygon
        # with the system's position repeated four times
        polygon = [point[0], point[0], point[0], point[0]]
        
        # Get the actual density from the ocean map at this single point
        return ocean_map.get_particles_in_area(polygon)
    
    def _get_observed_plastic_density(self, drones):
        """
        Get the observed plastic density at the current location using only drone data.
        This method is used for navigation decisions to ensure the system only uses
        information it could realistically have access to.
        
        Args:
            drones (list): List of Drone objects to get data from
            
        Returns:
            float: Observed plastic density at the current location (0.0 to 1.0)
        """
        # First check if any drones are directly at our location
        for drone in drones:
            if self._is_in_range(drone, max_range=1.0) and drone.particle_data is not None:
                return drone.particle_data
        
        # If no drones are nearby, use historical data if available
        if self.historical_data:
            # Find the closest historical data point
            closest_distance = float('inf')
            closest_density = 0.0
            
            for x, y, density in self.historical_data:
                dx = self.x_km - x
                dy = self.y_km - y
                distance = math.sqrt(dx*dx + dy*dy)
                
                if distance < closest_distance:
                    closest_distance = distance
                    closest_density = density
            
            # Only use historical data if it's reasonably close
            if closest_distance < self._update_interval * self.move_speed:  # Within 1h reach distance
                return closest_density
        
        # Default to a low density if no data is available
        return 0.1  # Baseline plastic density
        
    def _is_in_range(self, drone, max_range=15.0):
        """
        Check if a drone is within range of the catching system.
        Range is set to 15 km to ensure drones flying in front of the system are detected.
        
        Args:
            drone (Drone): The drone to check
            max_range (float): Maximum range for interaction in km
            
        Returns:
            bool: True if the drone is within range, False otherwise
        """
        # Simple Euclidean distance check
        dx = self.x_km - drone.x_km
        dy = self.y_km - drone.y_km
        distance = (dx**2 + dy**2)**0.5
        return distance <= max_range
        
    def _collect_historical_data(self, drones):
        """
        Collect historical plastic density data from all drones.
        
        Args:
            drones (list): List of Drone objects to collect data from
        """
        for drone in drones:
            if drone.particle_data is not None:
                # Store the position and plastic density data
                self.historical_data.append((drone.x_km, drone.y_km, drone.particle_data))
                
        # No limit on historical data - retain all data points
        # This provides more comprehensive coverage for decision making
    
    def _update_movement_target_random(self):
        """Select a random direction and move."""
        # FIXME
        self._update_counter += 1
        if self._update_counter % self._update_interval != 0:
            return  # Skip update

        import random
        random.seed(0)
        angle = random.uniform(0, 360) 
        distance = self._update_counter * self.move_speed
        rad = math.radians(angle - 90)
        target_x = self.x_km + distance * math.cos(rad)
        target_y = self.y_km + distance * math.sin(rad)
        self.target_position = (max(0, min(100, target_x)), max(0, min(100, target_y)))
        print(f"random {self.target_position}")
    
    def _update_movement_target_greedy(self):
        """
        Use a smart algorithm to determine the best location to move toward.
        Analyzes historical data to find areas with high plastic density,
        while considering the system's current heading and turning limitations.
        Prefers targets that are in front of the system rather than behind it.
        """
        # FIXME
        self._update_counter += 1
        if self._update_counter % self._update_interval != 0:
            return  # Skip update
        
        if not self.historical_data:
            return  # No historical data to analyze
            
        # Create a grid of the area and aggregate plastic density data
        grid_size = 2  # Reduced from 10km to 2km for finer granularity
        grid = {}
        
        # Aggregate historical data into grid cells
        for x, y, density in self.historical_data:
            # Convert x/y to grid coordinates
            grid_x = int(x / grid_size)
            grid_y = int(y / grid_size)
            key = (grid_x, grid_y)
            
            # Update grid cell with plastic density data
            if key in grid:
                grid[key] = (grid[key] + density) / 2  # Average with existing data
            else:
                grid[key] = density
        
        # Calculate scores for each grid cell based on plastic density and direction
        scored_cells = []
        
        # Current heading in radians (adjusted for coordinate system)
        # Using consistent adjustment: 0° is East, 90° is North
        current_heading_rad = math.radians(self.heading - 90)
        
        # Unit vector representing current direction
        direction_x = math.cos(current_heading_rad)
        direction_y = math.sin(current_heading_rad)
        
        # FIXME
        # Maximum feasible turn 
        # This is approximately how far ahead we should plan
        max_turn_angle_hour = self.max_turn_angle # (1h plan)
        max_turn_rad = math.radians(max_turn_angle_hour)
        
        for (grid_x, grid_y), density in grid.items():
            # Convert grid cell to x/y coordinates (center of the cell)
            cell_x = (grid_x + 0.5) * grid_size
            cell_y = (grid_y + 0.5) * grid_size
            
            # Calculate vector from current position to grid cell
            dx = cell_x - self.x_km
            dy = cell_y - self.y_km
            distance = math.sqrt(dx*dx + dy*dy)
            
            if distance < 0.1:  # Skip cells that are too close
                continue
                
            # Normalize the vector
            if distance > 0:
                dx /= distance
                dy /= distance
            
            # Calculate dot product to determine if cell is in front of system
            # Dot product range: -1 (directly behind) to 1 (directly ahead)
            dot_product = dx * direction_x + dy * direction_y
            
            # Calculate angle between current heading and direction to cell
            # Using the dot product formula: cos(θ) = (a·b)/(|a|·|b|)
            angle_to_cell = math.acos(max(-1.0, min(1.0, dot_product)))
            
            # Calculate directional score
            # Prefer cells that are in front (dot_product > 0) and within turning capability
            if dot_product > 0 and angle_to_cell <= max_turn_rad:
                # Cell is in front and can be reached with normal turning
                direction_score = 1.0
            elif dot_product > 0:
                # Cell is in front but requires more turning
                # Score decreases as angle increases beyond max turning capability
                direction_score = max(0.1, 1.0 - (angle_to_cell - max_turn_rad) / math.pi)
            else:
                # Cell is behind, significant penalty
                direction_score = max(0.05, (dot_product + 1) / 2) * 0.1
            
            # Calculate distance score (prefer closer cells, but not too close)
            # Optimal distance is around 10-15 km (adjusted for 2km grid size)
            # distance_score = 1.0 / (1.0 + abs(distance - 12.5) / 12.5)
            distance_score = 1.0 / (1.0 + abs(distance - self._update_interval * self.move_speed) / (self._update_interval * self.move_speed))
            
            # Calculate final score (plastic density is most important, but direction matters)
            final_score = density * (0.7 * direction_score + 0.3 * distance_score)
            
            scored_cells.append(((grid_x, grid_y), final_score, (cell_x, cell_y)))
        
        if not scored_cells:  # No valid cells found
            return
        
        # Find the cell with the highest score
        best_cell = max(scored_cells, key=lambda x: x[1])
        target_x, target_y = best_cell[2]  # Get the x/y coordinates
        
        # Set the target position
        self.target_position = (target_x, target_y)
        print(f"greedy {self.target_position}")
    
    def _update_movement_target_optimal(self, ocean_map):
        """
        Optimal strategy that uses ground truth map data to find the best target.
        Features:
        1. Full 360-degree search around the system
        2. Higher resolution scanning (2km grid)
        3. Larger search radius (50km)
        4. Distance-weighted particle density scoring
        """
        # FIXME
        self._update_counter += 1
        if self._update_counter % self._update_interval != 0:
            return  # Skip update 
        # Initialize variables
        best_score = 0.0
        best_target = None
        search_radius = 50  # Large search radius to find the best areas
        step_km = 2  # High resolution for accurate targeting
        
        # Search in a full 360-degree radius around the system
        for dx in range(-int(search_radius), int(search_radius)+1, step_km):
            for dy in range(-int(search_radius), int(search_radius)+1, step_km):
                x = self.x_km + dx
                y = self.y_km + dy 

                # Check if within map bounds
                if not (0 <= x <= 100 and 0 <= y <= 100):
                    continue

                # Calculate distance
                distance = math.sqrt(dx*dx + dy*dy)
                if distance > search_radius:
                    continue
                
                # Get particle density at this location using ground truth data
                density = ocean_map.get_particles_in_area([
                    (x-1, y-1), (x+1, y-1), (x+1, y+1), (x-1, y+1)
                ])
                
                # Calculate score: density weighted by distance
                # We want high density and low distance
                # Use inverse square for distance to prioritize closer areas
                distance_factor = 1.0 / (1.0 + distance/15.0)**2
                score = density * distance_factor
                
                # Update best target if this location has a better score
                if score > best_score:
                    best_score = score
                    best_target = (x, y)
        
        # Set the target position if a good one was found
        if best_target:
            self.target_position = best_target
        print(f"optimal {self.target_position}")
            
    # The following code is commented out and no longer used:
    #         current_f_score, current = heapq.heappop(open_list)
    #         if current == self._find_best_target(ocean_map):
    #             # Reconstruct path
    #             self.target_position = current
    #             return
            
    #         closed_list.add(current)
            
    #         # Explore neighbors (moving in 8 directions: N, S, E, W, NE, NW, SE, SW)
    #         for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1)]:
    #             neighbor = (current[0] + dx, current[1] + dy)
                
    #             if neighbor in closed_list:
    #                 continue
                
    def _update_movement_target_optimal(self, ocean_map):
        """
        Optimal strategy that finds the path with the highest integrated density.
        Features:
        1. Full 360-degree radial path search
        2. Density integration along each path
        3. Distance-limited integration (50km max range)
        """
        import numpy as np

        self._update_counter += 1
        if self._update_counter % (self._update_interval*24) != 0:
            return  # Skip update 

        best_score = 0.0
        best_target = None
        max_radius = 50  # km
        path_resolution = 2  # km between points along the path
        angle_step_deg = 45  # search in 45-degree increments

        for angle_deg in range(0, 360, angle_step_deg):
            angle_rad = math.radians(angle_deg)
            total_score = 0.0
            num_steps = int(max_radius / path_resolution)

            for step in range(1, num_steps + 1):
                distance = step * path_resolution
                dx = distance * math.cos(angle_rad)
                dy = distance * math.sin(angle_rad)
                x = self.x_km + dx
                y = self.y_km + dy

                # Check map bounds
                if not (0 <= x <= 100 and 0 <= y <= 100):
                    break

                # Get particle density at this location
                density = ocean_map.get_particles_in_area([
                    (x-1, y-1), (x+1, y-1), (x+1, y+1), (x-1, y+1)
                ])
                
                # Optionally apply distance decay or weighting
                weight = 1.0 / (1.0 + distance / 15.0)**2
                total_score += density * weight

            # Use endpoint of the path as the target
            if total_score > best_score:
                best_score = total_score
                best_target = (self.x_km + max_radius * math.cos(angle_rad),
                            self.y_km + max_radius * math.sin(angle_rad))

        if best_target:
            self.target_position = best_target
        print(f"optimal {self.target_position}")

    def _find_best_target(self, ocean_map):
        """
        Find the best target location based on the highest plastic density from the ocean map.
        Returns the location with the highest density.
        """
        best_location = (self.x_km, self.y_km)
        max_density = 0
        
        # Search over a grid of possible locations (assumed grid size)
        for x in range(0, 100, 2):  # Assuming a 100 km x 100 km area with 1 km grid spacing
            for y in range(0, 100, 2):
                plastic_density = ocean_map.get_particles_in_area([(x, y), (x + 2, y), (x + 2, y + 2), (x, y + 2)])
                
                if plastic_density > max_density:
                    max_density = plastic_density
                    best_location = (x, y)
        
        return best_location
    
    def _move_toward_target(self):
        """
        Move the catching system toward the target position.
        Respects maximum speed and turning angle constraints.
        Always moves at constant speed, even when near the target.
        """
        if self.target_position is None:
            # If no target, create a default one to keep moving
            self._set_default_target()
            
        target_x, target_y = self.target_position
        
        # Calculate direction to target
        dx = target_x - self.x_km
        dy = target_y - self.y_km
        distance = (dx**2 + dy**2)**0.5
        
        # If we're close to the target, select a new one
        if distance < 0.5:  # Increased threshold to prevent frequent target changes
            self._select_new_target()
            target_x, target_y = self.target_position
            
            # Recalculate direction to new target
            dx = target_x - self.x_km
            dy = target_y - self.y_km
            distance = (dx**2 + dy**2)**0.5
        
        # Calculate target heading in degrees
        # Using consistent adjustment: 0° is East, 90° is North
        target_heading = math.degrees(math.atan2(dy, dx))
        # Convert to 0-360 range with consistent -90 adjustment
        target_heading = (target_heading - 90) % 360
        
        # Determine how much to turn (respecting max turn angle)
        heading_diff = (target_heading - self.heading + 180) % 360 - 180
        turn_angle = max(-self.max_turn_angle, min(self.max_turn_angle, heading_diff))
        
        # Update heading
        self.heading = (self.heading + turn_angle) % 360
        
        # Always move at constant speed
        move_distance = self.move_speed
        # Consistent adjustment: 0° is East, 90° is North
        move_angle_rad = math.radians(self.heading - 90)  # Convert to radians and adjust for coordinate system
        
        # Update position
        self.x_km += move_distance * math.cos(move_angle_rad)
        self.y_km += move_distance * math.sin(move_angle_rad)
        
    def _select_new_target(self):
        """
        Select a new target when the current one is reached.
        Uses historical data if available, otherwise selects a target
        in the current direction of travel.
        """
        # Try to update movement target based on strategy
        if self.strategy == "random":
            self._update_movement_target_random()
        elif self.strategy == "drone":
            self._update_movement_target_greedy()
        elif self.strategy == "optimal":
            self._update_movement_target_optimal(self.ocean_map)
        else:
            # Fallback to default target
            self._set_default_target()
        
        # If no target was set from historical data, create one in current direction
        if self.target_position is None:
            self._set_default_target()
            
    def _set_default_target(self):
        """
        Set a default target in the current direction of travel
        to ensure continuous movement for efficient plastic collection.
        """
        # Move in current heading direction
        # Consistent adjustment: 0° is East, 90° is North
        move_angle_rad = math.radians(self.heading - 90)
        
        # Set target 10 units away in current direction
        target_distance = self._update_interval * self.move_speed
        target_x = self.x_km + target_distance * math.cos(move_angle_rad)
        target_y = self.y_km + target_distance * math.sin(move_angle_rad)
        
        # Ensure target stays within map boundaries (assuming 0-100 range)
        target_x = max(0.0, min(100.0, target_x))
        target_y = max(0.0, min(100.0, target_y))
        
        self.target_position = (target_x, target_y)

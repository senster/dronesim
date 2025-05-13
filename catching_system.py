import math
import numpy as np
from actor import Actor

class CatchingSystem(Actor):
    """
    Represents a mobile system for catching plastic in the ocean detected by drones.
    Can move slowly and uses a greedy algorithm to navigate toward high-density areas.
    """
    def __init__(self, lat=0.0, long=0.0, move_speed=0.278, max_turn_angle=1.5, 
                 system_span=50.0, retention_efficiency=0.8):
        """
        Initialize a CatchingSystem with position and movement capabilities.
        The system has unlimited capacity for plastic collection.
        
        Args:
            lat (float): Latitude position
            long (float): Longitude position
            move_speed (float): Maximum movement speed over ground per step (km/h)
            max_turn_angle (float): Maximum turning angle per step in degrees (1.5 degrees per step = 45 degrees per 3 hours)
            system_span (float): Width of the system in meters for plastic collection
            retention_efficiency (float): Efficiency of the system in retaining plastic (0.0 to 1.0)
        """
        super().__init__(lat, long)
        self.current_load = 0.0  # Plastic collected in current step
        self.total_collected = 0.0  # Total plastic collected over time
        
        # Movement parameters
        self.move_speed = move_speed  # Speed over ground (km/h)
        self.max_turn_angle = max_turn_angle
        self.heading = 0.0  # Degrees, 0 = North, 90 = East, etc.
        
        # Plastic collection parameters
        self.system_span = system_span  # Width of the system in meters
        self.retention_efficiency = retention_efficiency  # Efficiency in retaining plastic
        
        # Historical data tracking
        self.historical_data = []  # Will store (lat, long, density) tuples
        self.target_position = None  # Target position to move toward
        
    def step(self, drones, ocean_map=None):
        """
        Update the catching system for one time step.
        Collects data from drones, calculates plastic collection, and moves toward high-density areas.
        
        Args:
            drones (list): List of Drone objects to interact with
            ocean_map (OceanMap, optional): Ocean map with current information
            
        Returns:
            float: Amount of plastic collected in this step
        """
        # Reset current load for this step
        self.current_load = 0.0
        
        # Collect historical data from all drones
        self._collect_historical_data(drones)
        
        # Calculate plastic collection based on the formula:
        # Plastic catch = (Speed Through Water) * (System Span) * (Retention Efficiency) * (Encountered Plastic Density)
        
        # Get the plastic density at the current location
        plastic_density = self._get_current_plastic_density(drones)
        
        if plastic_density > 0:
            # Calculate speed through water (accounting for currents)
            # For simplicity, we'll assume currents are minimal and speed through water ≈ speed over ground
            # In a more complex simulation, we would calculate this based on current vectors
            speed_through_water = self.move_speed  # km/h
            
            # Convert system span from meters to kilometers for consistent units
            system_span_km = self.system_span / 1000.0  # km
            
            # Calculate plastic catch using the formula
            # Units: (km/h) * (km) * (efficiency) * (density) = (km²/h) * density * efficiency
            plastic_collected = speed_through_water * system_span_km * self.retention_efficiency * plastic_density
            
            # Update collection totals
            self.current_load = plastic_collected
            self.total_collected += plastic_collected
        
        # Determine where to move next using greedy algorithm
        self._update_movement_target()
        
        # Move toward the target
        self._move_toward_target()
                    
        return self.current_load
        
    def _get_current_plastic_density(self, drones):
        """
        Get the plastic density at the current location of the system.
        Uses data from nearby drones or historical data if available.
        
        Args:
            drones (list): List of Drone objects to get data from
            
        Returns:
            float: Plastic density at the current location (0.0 to 1.0)
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
            
            for lat, long, density in self.historical_data:
                dx = self.lat - lat
                dy = self.long - long
                distance = math.sqrt(dx*dx + dy*dy)
                
                if distance < closest_distance:
                    closest_distance = distance
                    closest_density = density
            
            # Only use historical data if it's reasonably close
            if closest_distance < 5.0:  # Within 5 km
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
        dx = self.lat - drone.lat
        dy = self.long - drone.long
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
                self.historical_data.append((drone.lat, drone.long, drone.particle_data))
                
        # Limit the size of historical data to prevent memory issues
        max_history = 1000
        if len(self.historical_data) > max_history:
            self.historical_data = self.historical_data[-max_history:]
    
    def _update_movement_target(self):
        """
        Use a smart algorithm to determine the best location to move toward.
        Analyzes historical data to find areas with high plastic density,
        while considering the system's current heading and turning limitations.
        Prefers targets that are in front of the system rather than behind it.
        """
        if not self.historical_data:
            return  # No historical data to analyze
            
        # Create a grid of the area and aggregate plastic density data
        grid_size = 10
        grid = {}
        
        # Aggregate historical data into grid cells
        for lat, long, density in self.historical_data:
            # Convert position to grid cell
            grid_x = int(lat / grid_size)
            grid_y = int(long / grid_size)
            key = (grid_x, grid_y)
            
            # Update grid cell with plastic density data
            if key in grid:
                grid[key] = (grid[key] + density) / 2  # Average with existing data
            else:
                grid[key] = density
        
        # Calculate scores for each grid cell based on plastic density and direction
        scored_cells = []
        
        # Current heading in radians (adjusted for coordinate system)
        current_heading_rad = math.radians(self.heading - 90)
        
        # Unit vector representing current direction
        direction_x = math.cos(current_heading_rad)
        direction_y = math.sin(current_heading_rad)
        
        # Maximum feasible turn in 50 steps (about 5 hours)
        # This is approximately how far ahead we should plan
        max_turn_angle_50_steps = 50 * self.max_turn_angle
        max_turn_rad = math.radians(max_turn_angle_50_steps)
        
        for (grid_x, grid_y), density in grid.items():
            # Convert grid cell to lat/long coordinates (center of the cell)
            cell_lat = (grid_x + 0.5) * grid_size
            cell_long = (grid_y + 0.5) * grid_size
            
            # Calculate vector from current position to grid cell
            dx = cell_lat - self.lat
            dy = cell_long - self.long
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
            # Optimal distance is around 20-30 grid units
            distance_score = 1.0 / (1.0 + abs(distance - 25.0) / 25.0)
            
            # Calculate final score (plastic density is most important, but direction matters)
            final_score = density * (0.7 * direction_score + 0.3 * distance_score)
            
            scored_cells.append(((grid_x, grid_y), final_score, (cell_lat, cell_long)))
        
        if not scored_cells:  # No valid cells found
            return
        
        # Find the cell with the highest score
        best_cell = max(scored_cells, key=lambda x: x[1])
        target_lat, target_long = best_cell[2]  # Get the lat/long coordinates
        
        # Set the target position
        self.target_position = (target_lat, target_long)
    
    def _move_toward_target(self):
        """
        Move the catching system toward the target position.
        Respects maximum speed and turning angle constraints.
        Always moves at constant speed, even when near the target.
        """
        if self.target_position is None:
            # If no target, create a default one to keep moving
            self._set_default_target()
            
        target_lat, target_long = self.target_position
        
        # Calculate direction to target
        dx = target_lat - self.lat
        dy = target_long - self.long
        distance = (dx**2 + dy**2)**0.5
        
        # If we're close to the target, select a new one
        if distance < 0.5:  # Increased threshold to prevent frequent target changes
            self._select_new_target()
            target_lat, target_long = self.target_position
            
            # Recalculate direction to new target
            dx = target_lat - self.lat
            dy = target_long - self.long
            distance = (dx**2 + dy**2)**0.5
        
        # Calculate target heading in degrees
        target_heading = math.degrees(math.atan2(dy, dx))
        # Convert to 0-360 range
        target_heading = (target_heading + 90) % 360
        
        # Determine how much to turn (respecting max turn angle)
        heading_diff = (target_heading - self.heading + 180) % 360 - 180
        turn_angle = max(-self.max_turn_angle, min(self.max_turn_angle, heading_diff))
        
        # Update heading
        self.heading = (self.heading + turn_angle) % 360
        
        # Always move at constant speed
        move_distance = self.move_speed
        move_angle_rad = math.radians(self.heading - 90)  # Convert to radians and adjust for coordinate system
        
        # Update position
        self.lat += move_distance * math.cos(move_angle_rad)
        self.long += move_distance * math.sin(move_angle_rad)
        
    def _select_new_target(self):
        """
        Select a new target when the current one is reached.
        Uses historical data if available, otherwise selects a target
        in the current direction of travel.
        """
        # Try to update movement target based on historical data
        self._update_movement_target()
        
        # If no target was set from historical data, create one in current direction
        if self.target_position is None:
            self._set_default_target()
            
    def _set_default_target(self):
        """
        Set a default target in the current direction of travel
        to ensure continuous movement for efficient plastic collection.
        """
        # Move in current heading direction
        move_angle_rad = math.radians(self.heading - 90)
        
        # Set target 10 units away in current direction
        target_distance = 10.0
        target_lat = self.lat + target_distance * math.cos(move_angle_rad)
        target_long = self.long + target_distance * math.sin(move_angle_rad)
        
        # Ensure target stays within map boundaries (assuming 0-100 range)
        target_lat = max(0.0, min(100.0, target_lat))
        target_long = max(0.0, min(100.0, target_long))
        
        self.target_position = (target_lat, target_long)

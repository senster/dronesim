import math
import numpy as np
from actor import Actor

class CatchingSystem(Actor):
    """
    Represents a mobile system for catching or processing particles detected by drones.
    Can move slowly and uses a greedy algorithm to navigate toward high-density areas.
    """
    def __init__(self, lat=0.0, long=0.0, capacity=100.0, move_speed=0.278, max_turn_angle=1.5):
        """
        Initialize a CatchingSystem with position, capacity, and movement capabilities.
        
        Args:
            lat (float): Latitude position
            long (float): Longitude position
            capacity (float): Maximum processing capacity per step
            move_speed (float): Maximum movement speed per step
            max_turn_angle (float): Maximum turning angle per step in degrees (1.5 degrees per step = 45 degrees per 3 hours)
        """
        super().__init__(lat, long)
        self.capacity = capacity
        self.current_load = 0.0
        self.total_processed = 0.0
        
        # Movement parameters
        self.move_speed = move_speed
        self.max_turn_angle = max_turn_angle
        self.heading = 0.0  # Degrees, 0 = North, 90 = East, etc.
        
        # Historical data tracking
        self.historical_data = []  # Will store (lat, long, density) tuples
        self.target_position = None  # Target position to move toward
        
    def step(self, drones):
        """
        Update the catching system for one time step.
        Collects data from drones, processes particles, and moves toward high-density areas.
        
        Args:
            drones (list): List of Drone objects to interact with
            
        Returns:
            float: Amount of particles processed in this step
        """
        # Reset current load for this step
        self.current_load = 0.0
        
        # Collect historical data from all drones
        self._collect_historical_data(drones)
        
        # Process data from nearby drones
        for drone in drones:
            # Check if drone is within range
            if self._is_in_range(drone) and drone.particle_data is not None:
                # Process some of the particles detected by the drone
                processed = min(drone.particle_data * 10, self.capacity - self.current_load)
                self.current_load += processed
                self.total_processed += processed
                
                # If we've reached capacity, stop processing
                if self.current_load >= self.capacity:
                    break
        
        # Determine where to move next using greedy algorithm
        self._update_movement_target()
        
        # Move toward the target
        self._move_toward_target()
                    
        return self.current_load
        
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
        Collect historical data from all drones.
        
        Args:
            drones (list): List of Drone objects to collect data from
        """
        for drone in drones:
            if drone.particle_data is not None:
                # Store the position and density data
                self.historical_data.append((drone.lat, drone.long, drone.particle_data))
                
        # Limit the size of historical data to prevent memory issues
        max_history = 1000
        if len(self.historical_data) > max_history:
            self.historical_data = self.historical_data[-max_history:]
    
    def _update_movement_target(self):
        """
        Use a smart algorithm to determine the best location to move toward.
        Analyzes historical data to find areas with high particle density,
        while considering the system's current heading and turning limitations.
        Prefers targets that are in front of the system rather than behind it.
        """
        if not self.historical_data:
            return  # No historical data to analyze
            
        # Create a grid of the area and aggregate density data
        grid_size = 10
        grid = {}
        
        # Aggregate historical data into grid cells
        for lat, long, density in self.historical_data:
            # Convert position to grid cell
            grid_x = int(lat / grid_size)
            grid_y = int(long / grid_size)
            key = (grid_x, grid_y)
            
            # Update grid cell with density data
            if key in grid:
                grid[key] = (grid[key] + density) / 2  # Average with existing data
            else:
                grid[key] = density
        
        # Calculate scores for each grid cell based on density and direction
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
            
            # Calculate final score (density is most important, but direction matters)
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
        to ensure continuous movement.
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

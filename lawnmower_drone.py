from drone import Drone

class LawnmowerDrone(Drone):
    """
    A drone that follows a lawnmower pattern to scan the ocean map.
    """
    def __init__(self, x_km=0.0, y_km=0.0, scan_radius=1.0, 
                 min_x=0.0, max_x=100.0, min_y=0.0, max_y=100.0, step_size=2.0,
                 initial_direction=1, initial_vertical_direction=1):
        """
        Initialize a LawnmowerDrone with position and scanning capabilities.
        
        Args:
            x_km (float): Initial X position in kilometers from the left edge
            y_km (float): Initial Y position in kilometers from the bottom edge
            scan_radius (float): Radius of the drone's scanning area in kilometers
            min_x (float): Minimum X boundary in kilometers
            max_x (float): Maximum X boundary in kilometers
            min_y (float): Minimum Y boundary in kilometers
            max_y (float): Maximum Y boundary in kilometers
            step_size (float): Distance to move in each step in kilometers
            initial_direction (int): Initial horizontal direction (1 for east, -1 for west)
            initial_vertical_direction (int): Initial vertical direction (1 for north, -1 for south)
        """
        super().__init__(x_km, y_km, scan_radius)
        
        # Store boundaries
        self.min_x = min_x
        self.max_x = max_x
        self.min_y = min_y
        self.max_y = max_y
        self.step_size = step_size
        self.direction = initial_direction  # 1 for moving east, -1 for moving west
        self.vertical_direction = initial_vertical_direction  # 1 for moving north, -1 for moving south
        self.completed_rows = 0
        
    def step(self, ocean_map):
        """
        Move the drone in a lawnmower pattern and scan the area.
        
        Args:
            ocean_map (OceanMap): The ocean map to scan
            
        Returns:
            float: Density of particles in the scanned area
        """
        # Scan current position
        particle_density = self.scan_area(ocean_map)
        
        # Move according to lawnmower pattern
        self._move_lawnmower_pattern()
        
        return particle_density
        
    def _move_lawnmower_pattern(self):
        """
        Move the drone in a lawnmower pattern.
        Supports different initial directions and can move in any of the four cardinal directions.
        """
        # Move east or west (x direction)
        self.x_km += self.direction * self.step_size
        
        # Check if we've reached a boundary
        if self.x_km >= self.max_x:
            self.x_km = self.max_x
            self.y_km += self.vertical_direction * self.step_size  # Move north or south
            self.direction = -1  # Start moving west
            self.completed_rows += 1
            
        elif self.x_km <= self.min_x:
            self.x_km = self.min_x
            self.y_km += self.vertical_direction * self.step_size  # Move north or south
            self.direction = 1  # Start moving east
            self.completed_rows += 1
            
        # Check if we've reached the vertical boundaries
        # If so, reverse vertical direction
        if (self.vertical_direction > 0 and self.y_km >= self.max_y) or \
           (self.vertical_direction < 0 and self.y_km <= self.min_y):
            self.vertical_direction *= -1
            if self.vertical_direction > 0:
                self.y_km = self.min_y
            else:
                self.y_km = self.max_y
            # Optionally reset or implement some end-of-scan behavior

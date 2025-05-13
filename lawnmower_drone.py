from drone import Drone

class LawnmowerDrone(Drone):
    """
    A drone that follows a lawnmower pattern to scan the ocean map.
    """
    def __init__(self, lat=0.0, long=0.0, scan_radius=1.0, 
                 min_lat=0.0, max_lat=100.0, min_long=0.0, max_long=100.0, step_size=2.0,
                 initial_direction=1, initial_vertical_direction=1):
        """
        Initialize a LawnmowerDrone with position and scanning capabilities.
        
        Args:
            lat (float): Initial latitude position
            long (float): Initial longitude position
            scan_radius (float): Radius of the drone's scanning area
            min_lat (float): Minimum latitude boundary
            max_lat (float): Maximum latitude boundary
            min_long (float): Minimum longitude boundary
            max_long (float): Maximum longitude boundary
            step_size (float): Distance to move in each step
            initial_direction (int): Initial horizontal direction (1 for east, -1 for west)
            initial_vertical_direction (int): Initial vertical direction (1 for north, -1 for south)
        """
        super().__init__(lat, long, scan_radius)
        self.min_lat = min_lat
        self.max_lat = max_lat
        self.min_long = min_long
        self.max_long = max_long
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
        # Move horizontally (east or west)
        self.long += self.direction * self.step_size
        
        # Check if we've reached the horizontal boundary
        if self.long >= self.max_long:
            self.long = self.max_long
            self.lat += self.vertical_direction * self.step_size  # Move north or south
            self.direction = -1  # Start moving west
            self.completed_rows += 1
        elif self.long <= self.min_long:
            self.long = self.min_long
            self.lat += self.vertical_direction * self.step_size  # Move north or south
            self.direction = 1  # Start moving east
            self.completed_rows += 1
            
        # Check if we've reached the vertical boundary
        if (self.vertical_direction > 0 and self.lat >= self.max_lat) or \
           (self.vertical_direction < 0 and self.lat <= self.min_lat):
            # Reached boundary, reverse direction if needed or implement end behavior
            if self.vertical_direction > 0:
                self.lat = self.max_lat
            else:
                self.lat = self.min_lat
            # Optionally reset or implement some end-of-scan behavior

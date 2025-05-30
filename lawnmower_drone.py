from drone import Drone
from strategy_manager import StrategyManager

class LawnmowerDrone(Drone):
    """
    A drone that follows a lawnmower pattern to scan the ocean map.
    """
    def __init__(self, x_km=0.0, y_km=0.0, scan_radius=1.0, 
                 min_x=0.0, max_x=100.0, min_y=0.0, max_y=100.0, dt=300.0, speed=100, 
                 initial_direction=1, initial_vertical_direction=1, strategy_name=None):
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
            dt (float): total number seconds per step 
            speed (float): Distance the drone moves in km/h
            initial_direction (int): Initial horizontal direction (1 for east, -1 for west)
            initial_vertical_direction (int): Initial vertical direction (1 for north, -1 for south)
            strategy_name (str, optional): Name of the scanning strategy to use
        """
        super().__init__(x_km, y_km, scan_radius)
        
        # Store boundaries
        self.min_x = min_x
        self.max_x = max_x
        self.min_y = min_y
        self.max_y = max_y
        dt_step = dt/3600 
        self.step_size = speed*dt_step
        self.direction = initial_direction  # 1 for moving east, -1 for moving west
        self.vertical_direction = initial_vertical_direction  # 1 for moving north, -1 for moving south
        self.completed_rows = 0
        
        # Strategy parameters
        self.horizontal_step = self.step_size  # Horizontal step size (between columns)
        self.vertical_step = self.step_size   # Vertical step size (between rows)
        
        # Initialize strategy manager and apply strategy if provided
        self.strategy_manager = StrategyManager()
        self.strategy_name = strategy_name
        if strategy_name:
            self.apply_strategy(strategy_name)
        
    def apply_strategy(self, strategy_name=None):
        """
        Apply a scanning strategy to the drone.
        
        Args:
            strategy_name (str, optional): Name of the strategy to apply
        """
        strategy = self.strategy_manager.get_strategy(strategy_name)
        if strategy:
            self.strategy_name = strategy_name if strategy_name else self.strategy_manager.get_default_strategy_name()
            
            # Apply strategy parameters if available
            if "H (km)" in strategy and "V (km)" in strategy:
                # Get horizontal and vertical distances from strategy
                h_distance = strategy["H (km)"]
                v_distance = strategy["V (km)"]
                
                # Calculate the ratio between map dimensions and strategy dimensions
                map_width = self.max_x - self.min_x
                map_height = self.max_y - self.min_y
                
                # Scale the strategy parameters to the map size
                # For a 100x100 map, we want to scale the H and V values appropriately
                # Lower values create tighter bands (smaller step sizes)
                
                # Calculate horizontal step (distance between columns)
                # Use a scaling factor to convert from km to map units
                scaling_factor = 0.05  # Adjust this to get appropriate step sizes
                self.horizontal_step = max(0.5, min(10.0, h_distance * scaling_factor))
                
                # Calculate vertical step (distance between rows)
                # This determines how far apart the lawnmower rows are
                self.vertical_step = max(0.5, min(10.0, v_distance * scaling_factor))
                
                # Use the horizontal step for the main step size
                self.step_size = self.horizontal_step
                
                print(f"Applied strategy '{self.strategy_name}' with horizontal step {self.horizontal_step:.2f} and vertical step {self.vertical_step:.2f}")
            else:
                print(f"Strategy '{self.strategy_name}' does not contain required parameters")
        else:
            print("No valid strategy applied, using default parameters")
    
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
        Uses horizontal_step for movement along rows and vertical_step for movement between rows.
        """
        # Move horizontally (east or west) using the horizontal step size
        self.x_km += self.direction * self.horizontal_step
        
        # Check if we've reached the horizontal boundary
        if self.x_km >= self.max_x:
            self.x_km = self.max_x
            self.y_km += self.vertical_direction * self.vertical_step  # Move north or south using vertical step
            self.direction = -1  # Start moving west
            self.completed_rows += 1
        elif self.x_km <= self.min_x:
            self.x_km = self.min_x
            self.y_km += self.vertical_direction * self.vertical_step  # Move north or south using vertical step
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

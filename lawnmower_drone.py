from drone import Drone
from strategy_manager import StrategyManager

class LawnmowerDrone(Drone):
    """
    A drone that follows a lawnmower pattern to scan the ocean map.
    """
    def __init__(self, lat=0.0, long=0.0, scan_radius=1.0, 
                 min_lat=0.0, max_lat=100.0, min_long=0.0, max_long=100.0, step_size=2.0,
                 initial_direction=1, initial_vertical_direction=1, strategy_name=None):
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
            strategy_name (str, optional): Name of the scanning strategy to use
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
        
        # Strategy parameters
        self.horizontal_step = step_size  # Horizontal step size (between columns)
        self.vertical_step = step_size    # Vertical step size (between rows)
        
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
                map_width = self.max_long - self.min_long
                map_height = self.max_lat - self.min_lat
                
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
        self.long += self.direction * self.horizontal_step
        
        # Check if we've reached the horizontal boundary
        if self.long >= self.max_long:
            self.long = self.max_long
            self.lat += self.vertical_direction * self.vertical_step  # Move north or south using vertical step
            self.direction = -1  # Start moving west
            self.completed_rows += 1
        elif self.long <= self.min_long:
            self.long = self.min_long
            self.lat += self.vertical_direction * self.vertical_step  # Move north or south using vertical step
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

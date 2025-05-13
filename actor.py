class Actor:
    """
    Base class for all objects in the simulation.
    All objects on the map inherit from this class.
    
    The coordinate system uses kilometers with (0,0) at the bottom left corner.
    Movement speeds are defined in km/h and automatically adjusted based on the
    simulation time step.
    """
    def __init__(self, x_km=0.0, y_km=0.0, speed_km_h=0.0):
        """
        Initialize an Actor with a position in kilometers and speed in km/h.
        
        Args:
            x_km (float): X position in kilometers from the left edge
            y_km (float): Y position in kilometers from the bottom edge
            speed_km_h (float): Movement speed in kilometers per hour
        """
        self.x_km = x_km
        self.y_km = y_km
        self.speed_km_h = speed_km_h
        self.heading = 0.0  # Direction in degrees (0 = North, 90 = East, etc.)
        
    def step(self, seconds_elapsed=300.0):
        """
        Update the actor's state for one time step.
        This method should be overridden by subclasses.
        
        Args:
            seconds_elapsed (float): Number of seconds elapsed in this step
        """
        pass
        
    def calculate_movement_distance(self, seconds_elapsed):
        """
        Calculate the distance to move based on speed and time elapsed.
        
        Args:
            seconds_elapsed (float): Number of seconds elapsed in this step
            
        Returns:
            float: Distance to move in kilometers
        """
        # Convert km/h to km/s and multiply by seconds elapsed
        return (self.speed_km_h / 3600.0) * seconds_elapsed
        
    def move_by_heading(self, distance_km, heading_degrees=None):
        """
        Move the actor in a specific direction by a given distance.
        
        Args:
            distance_km (float): Distance to move in kilometers
            heading_degrees (float, optional): Direction in degrees (0 = North, 90 = East)
                                               If None, uses the actor's current heading
        """
        import math
        
        # Use provided heading or current heading if not specified
        heading = heading_degrees if heading_degrees is not None else self.heading
        
        # Convert heading to radians (adjusting for coordinate system)
        # In our system, 0 degrees = North (up), 90 degrees = East (right)
        heading_rad = math.radians(90 - heading)  # Adjust for standard math coordinates
        
        # Calculate movement components
        dx = distance_km * math.cos(heading_rad)
        dy = distance_km * math.sin(heading_rad)
        
        # Update position
        self.x_km += dx
        self.y_km += dy

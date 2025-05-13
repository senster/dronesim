class Actor:
    """
    Base class for all objects in the simulation.
    All objects on the map inherit from this class.
    
    The coordinate system uses kilometers with (0,0) at the bottom left corner.
    """
    def __init__(self, x_km=0.0, y_km=0.0):
        """
        Initialize an Actor with a position in kilometers.
        
        Args:
            x_km (float): X position in kilometers from the left edge
            y_km (float): Y position in kilometers from the bottom edge
        """
        self.x_km = x_km
        self.y_km = y_km
        
    def step(self):
        """
        Update the actor's state for one time step.
        This method should be overridden by subclasses.
        """
        pass

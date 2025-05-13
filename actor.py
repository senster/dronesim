class Actor:
    """
    Base class for all objects in the simulation.
    All objects on the map inherit from this class.
    """
    def __init__(self, lat=0.0, long=0.0):
        """
        Initialize an Actor with a latitude and longitude position.
        
        Args:
            lat (float): Latitude position
            long (float): Longitude position
        """
        self.lat = lat
        self.long = long
        
    def step(self):
        """
        Update the actor's state for one time step.
        This method should be overridden by subclasses.
        """
        pass

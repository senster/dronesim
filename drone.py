from actor import Actor

class Drone(Actor):
    """
    Base class for all drone objects in the simulation.
    """
    def __init__(self, lat=0.0, long=0.0, scan_radius=1.0):
        """
        Initialize a Drone with position and scanning capabilities.
        
        Args:
            lat (float): Latitude position
            long (float): Longitude position
            scan_radius (float): Radius of the drone's scanning area
        """
        super().__init__(lat, long)
        self.scan_radius = scan_radius
        self.particle_data = None
        
    def step(self):
        """
        Update the drone's state for one time step.
        This method should be overridden by specific drone implementations.
        """
        pass
        
    def scan_area(self, ocean_map):
        """
        Scan the ocean map for particles in the drone's vicinity.
        
        Args:
            ocean_map (OceanMap): The ocean map to scan
            
        Returns:
            float: Density of particles in the scanned area
        """
        # Create a simple circular polygon for scanning
        # In a real implementation, this could be more complex
        polygon = self._create_scan_polygon()
        self.particle_data = ocean_map.get_particles_in_area(polygon)
        return self.particle_data
        
    def _create_scan_polygon(self):
        """
        Create a polygon representing the drone's scan area.
        
        Returns:
            list: List of (lat, long) points representing the scan polygon
        """
        # Simple implementation - just return a bounding box
        # In a real implementation, this could be a more complex shape
        return [
            (self.lat - self.scan_radius, self.long - self.scan_radius),
            (self.lat + self.scan_radius, self.long - self.scan_radius),
            (self.lat + self.scan_radius, self.long + self.scan_radius),
            (self.lat - self.scan_radius, self.long + self.scan_radius)
        ]

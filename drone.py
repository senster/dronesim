from actor import Actor

class Drone(Actor):
    """
    Base class for all drone objects in the simulation.
    """
    def __init__(self, x_km=0.0, y_km=0.0, scan_radius=1.0):
        """
        Initialize a Drone with position and scanning capabilities.
        
        Args:
            x_km (float): X position in kilometers from the left edge
            y_km (float): Y position in kilometers from the bottom edge
            scan_radius (float): Radius of the drone's scanning area in kilometers
        """
        super().__init__(x_km, y_km)
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
            list: List of (x, y) points representing the scan polygon
        """
        # Simple implementation - just return a bounding box
        # Create a simple polygon around the drone's current position
        polygon = [
            (self.x_km - self.scan_radius, self.y_km - self.scan_radius),
            (self.x_km + self.scan_radius, self.y_km - self.scan_radius),
            (self.x_km + self.scan_radius, self.y_km + self.scan_radius),
            (self.x_km - self.scan_radius, self.y_km + self.scan_radius)
        ]
        return polygon

from drone import Drone
import math

class CircularDrone(Drone):
    """
    A drone that flies in circular patterns around a central point (the catching system).
    Multiple drones divide the circles between them to avoid path overlap.
    """
    def __init__(self, lat=0.0, long=0.0, scan_radius=1.0, 
                 center_lat=50.0, center_long=50.0, orbit_radius=5.0,
                 drone_id=0, total_drones=1, catching_system=None):
        """
        Initialize a CircularDrone with position and scanning capabilities.
        Drones fly in circles in front of the system rather than orbiting around it.
        
        Args:
            lat (float): Initial latitude position
            long (float): Initial longitude position
            scan_radius (float): Radius of the drone's scanning area
            center_lat (float): Initial latitude of the center point (catching system)
            center_long (float): Initial longitude of the center point (catching system)
            orbit_radius (float): Radius of the circular pattern
            drone_id (int): ID of this drone (0-indexed)
            total_drones (int): Total number of drones in the fleet
            catching_system (CatchingSystem): Reference to the catching system
        """
        super().__init__(lat, long, scan_radius)
        self.center_lat = center_lat
        self.center_long = center_long
        self.catching_system = catching_system
        
        # Fixed circle radius (different for each drone to avoid collisions)
        self.circle_radius = orbit_radius + (drone_id * 2.0)  # Stagger drones by 2 units
        
        # Distribute drones in a pattern that provides good coverage
        # For 5 drones, we'll create a formation with staggered distances and positions
        
        self.drone_id = drone_id
        self.total_drones = total_drones
        
        # Calculate forward distance based on drone ID
        # Drone 0: Closest to system
        # Drones 1-2: Medium distance (left and right)
        # Drones 3-4: Furthest (left and right)
        if drone_id == 0:
            # Lead drone - directly in front, closest to system
            self.forward_distance = 6.0
        elif drone_id in [1, 2]:
            # Middle row - medium distance
            self.forward_distance = 9.0
        else:
            # Back row - furthest from system
            self.forward_distance = 12.0
        
        # Calculate initial angle to distribute drones horizontally
        # This creates a formation where drones are spread out left-to-right
        if drone_id == 0:
            # Center drone starts at angle 0
            self.current_angle = 0
        elif drone_id == 1:
            # Left side, middle distance
            self.current_angle = math.pi / 2  # 90 degrees
        elif drone_id == 2:
            # Right side, middle distance
            self.current_angle = 3 * math.pi / 2  # 270 degrees
        elif drone_id == 3:
            # Left side, furthest
            self.current_angle = math.pi / 3  # 60 degrees
        else:  # drone_id == 4
            # Right side, furthest
            self.current_angle = 5 * math.pi / 3  # 300 degrees
        
        # Speed in radians per step
        self.base_angular_speed = 0.15  # radians per step
        
        # Initialize position
        self._update_position()
        
    def step(self, ocean_map):
        """
        Move the drone in a circular pattern and scan the area.
        Updates the center point based on the catching system's position.
        Ensures smooth transitions without teleporting.
        
        Args:
            ocean_map (OceanMap): The ocean map to scan
            
        Returns:
            float: Density of particles in the scanned area
        """
        # Store previous position for calculating movement distance
        prev_lat = self.lat
        prev_long = self.long
        
        # Update center point to match the catching system's position if available
        if self.catching_system is not None:
            # Calculate the offset from previous center to new center
            delta_lat = self.catching_system.lat - self.center_lat
            delta_long = self.catching_system.long - self.center_long
            
            # Update the center point gradually to avoid teleportation
            # Maximum center point movement per step (same as system's speed)
            max_center_movement = 0.3  # slightly higher than system's 0.278 to avoid falling behind
            
            # Calculate distance of center movement
            center_movement_distance = math.sqrt(delta_lat**2 + delta_long**2)
            
            if center_movement_distance > max_center_movement:
                # Scale down the movement to avoid teleportation
                scale_factor = max_center_movement / center_movement_distance
                delta_lat *= scale_factor
                delta_long *= scale_factor
            
            # Update center point gradually
            self.center_lat += delta_lat
            self.center_long += delta_long
            
            # Move the drone's position by the same offset to maintain relative position
            self.lat += delta_lat
            self.long += delta_long
        
        # Move according to circular pattern
        self._move_circular_pattern()
        
        # Ensure the drone doesn't move too far in a single step (prevent teleporting)
        current_movement = math.sqrt((self.lat - prev_lat)**2 + (self.long - prev_long)**2)
        max_drone_movement = 10.0  # Maximum distance a drone can move in one step (10 grid units)
        
        if current_movement > max_drone_movement:
            # Scale back the movement to the maximum allowed
            movement_ratio = max_drone_movement / current_movement
            
            # Calculate new position that doesn't exceed max movement
            new_lat = prev_lat + (self.lat - prev_lat) * movement_ratio
            new_long = prev_long + (self.long - prev_long) * movement_ratio
            
            # Update position with limited movement
            self.lat = new_lat
            self.long = new_long
        
        # Scan current position after movement
        particle_density = self.scan_area(ocean_map)
        
        return particle_density
        
    def _move_circular_pattern(self):
        """
        Move the drone in a circular pattern in front of the system.
        """
        # Use a constant angular speed for smooth circular motion
        angular_speed = self.base_angular_speed
        
        # Update angle
        self.current_angle += angular_speed
        
        # Keep angle in [0, 2π) range
        if self.current_angle >= 2 * math.pi:
            self.current_angle %= 2 * math.pi
        
        # Update position
        self._update_position()
    
    def _update_position(self):
        """
        Update the drone's position to fly in a circle in front of the system.
        """
        if self.catching_system is not None:
            # Get system's heading in radians
            system_heading_rad = math.radians(self.catching_system.heading - 90)
            
            # Calculate the center point of the circle in front of the system
            # This point is forward_distance units ahead of the system in its heading direction
            circle_center_lat = self.center_lat + self.forward_distance * math.cos(system_heading_rad)
            circle_center_long = self.center_long + self.forward_distance * math.sin(system_heading_rad)
            
            # Calculate position on the circle around this center point
            self.lat = circle_center_lat + self.circle_radius * math.sin(self.current_angle)
            self.long = circle_center_long + self.circle_radius * math.cos(self.current_angle)
        else:
            # If no system reference, just circle around the center point
            self.lat = self.center_lat + self.circle_radius * math.sin(self.current_angle)
            self.long = self.center_long + self.circle_radius * math.cos(self.current_angle)

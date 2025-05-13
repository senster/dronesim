from drone import Drone
import math

class CircularDrone(Drone):
    """
    A drone that flies in circular patterns around a central point (the catching system).
    Multiple drones divide the circles between them to avoid path overlap.
    """
    def __init__(self, x_km=0.0, y_km=0.0, scan_radius=1.0, 
                 center_x=50.0, center_y=50.0, orbit_radius=5.0,
                 drone_id=0, total_drones=1, catching_system=None):
        """
        Initialize a CircularDrone with position and scanning capabilities.
        Drones fly in circles in front of the system rather than orbiting around it.
        
        Args:
            x_km (float): Initial X position in kilometers from the left edge
            y_km (float): Initial Y position in kilometers from the bottom edge
            scan_radius (float): Radius of the drone's scanning area in kilometers
            center_x (float): Initial X position of the center point (catching system) in kilometers
            center_y (float): Initial Y position of the center point (catching system) in kilometers
            orbit_radius (float): Radius of the circular pattern
            drone_id (int): ID of this drone (0-indexed)
            total_drones (int): Total number of drones in the fleet
            catching_system (CatchingSystem): Reference to the catching system
        """
        super().__init__(x_km, y_km, scan_radius)
        
        # Store center point coordinates
        self.center_x = center_x
        self.center_y = center_y
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
        prev_x = self.x_km
        prev_y = self.y_km
        
        # Update center point to match the catching system's position if available
        if self.catching_system is not None:
            # Calculate the offset from previous center to new center
            delta_x = self.catching_system.x_km - self.center_x
            delta_y = self.catching_system.y_km - self.center_y
            
            # Update the center point gradually to avoid teleportation
            # Maximum center point movement per step (same as system's speed)
            max_center_movement = 0.3  # slightly higher than system's 0.278 to avoid falling behind
            
            # Calculate distance of center movement
            center_movement_distance = math.sqrt(delta_x**2 + delta_y**2)
            
            if center_movement_distance > max_center_movement:
                # Scale down the movement to avoid teleportation
                scale_factor = max_center_movement / center_movement_distance
                delta_x *= scale_factor
                delta_y *= scale_factor
            
            # Update center point gradually
            self.center_x += delta_x
            self.center_y += delta_y
            
            # Also move the drone to maintain relative position
            self.x_km += delta_x
            self.y_km += delta_y
        
        # Move according to circular pattern
        self._move_circular_pattern()
        
        # Ensure the drone doesn't move too far in a single step (prevent teleporting)
        current_movement = math.sqrt((self.x_km - prev_x)**2 + (self.y_km - prev_y)**2)
        max_drone_movement = 10.0  # Maximum distance a drone can move in one step (10 grid units)
        
        if current_movement > max_drone_movement:
            # Scale back the movement to the maximum allowed
            movement_ratio = max_drone_movement / current_movement
            
            # Calculate new position that doesn't exceed max movement
            new_x = prev_x + (self.x_km - prev_x) * movement_ratio
            new_y = prev_y + (self.y_km - prev_y) * movement_ratio
            
            # Update position
            self.x_km = new_x
            self.y_km = new_y
        
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
            # Using consistent adjustment: 0° is East, 90° is North
            system_heading_rad = math.radians(self.catching_system.heading - 90)
            
            # Calculate the center point of the circle in front of the system
            # This point is forward_distance units ahead of the system in its heading direction
            circle_center_x = self.center_x + self.forward_distance * math.cos(system_heading_rad)
            circle_center_y = self.center_y + self.forward_distance * math.sin(system_heading_rad)
            
            # Calculate new position on the circle
            # Using consistent coordinate system: sin for y and cos for x
            self.x_km = circle_center_x + self.circle_radius * math.cos(self.current_angle)
            self.y_km = circle_center_y + self.circle_radius * math.sin(self.current_angle)
        else:
            # If no system reference, just circle around the center point
            # Using consistent coordinate system: sin for y and cos for x
            self.x_km = self.center_x + self.circle_radius * math.cos(self.current_angle)
            self.y_km = self.center_y + self.circle_radius * math.sin(self.current_angle)

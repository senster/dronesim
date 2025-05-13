from actor import Actor
import math
import matplotlib.pyplot as plt
import numpy as np
import json

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
        self.current_heading = 20
        self.maximum_pixel_size_mm = 25

        self._current_altitude_in_m = 50

        self.camera_specs = self.load_camera("4k")

    def load_camera(self, camera_name):
        with open("./configs/cameras.json", 'r') as f:
            camera_specs = json.load(f)[camera_name]

        return camera_specs

    def change_height(self, new_height):
        """
        Change the drone's flight height.
        
        Args:
            height (float): New flight height in meters
        """

        if new_height < 0:
            raise ValueError("Height cannot be negative.")
        
        pixel_size_mm = self.get_coverage(self.camera_specs, new_height)["pixel_size_mm"]
        if pixel_size_mm < self.maximum_pixel_size_mm:
            print(f"WARNING - Altitude {new_height} is too high for the camera resolution.")
        
        self._current_altitude_in_m = new_height

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

        polygon = self._create_scan_polygon()
        self.particle_data = ocean_map.get_particles_in_area(polygon)
        return self.particle_data
        

    def _create_scan_polygon(self):
        """
        Create a rotated rectangle (FoV area) in local (x, y) KM frame,
        based on drone's heading and FoV dimensions in kilometers.

        Returns:
            list: List of (y, x) tuples representing the polygon corners
        """
        coverage = self.get_coverage(self.camera_specs, self._current_altitude_in_m)  # Assumes values in kilometers
        
        heading_rad = math.radians(self.current_heading)

        # Half-width and half-height of FoV (in kilometers)
        half_width = coverage["horizontal_fov_m"] / 2
        half_height = coverage["vertical_fov_m"] / 2

        # Rectangle corners before rotation (centered at origin)
        corners = [
            (-half_width, -half_height),  # bottom-left
            ( half_width, -half_height),  # bottom-right
            ( half_width,  half_height),  # top-right
            (-half_width,  half_height),  # top-left
        ]

        rotated_corners = []
        for dx, dy in corners:
            # Rotate point by heading angle
            rotated_x = dx * math.cos(heading_rad) - dy * math.sin(heading_rad)
            rotated_y = dx * math.sin(heading_rad) + dy * math.cos(heading_rad)

            # Translate to drone's position in local km frame
            x = self.x_km + rotated_x
            y = self.y_km + rotated_y

            rotated_corners.append((y, x))  # (y, x) to match plotting convention

        return rotated_corners


    def get_coverage(self, camera: dict, altitude_m: float) -> dict:
        """
        Ground coverage and field-of-view for a camera at a given altitude.

        Args:
            camera (dict): Camera specification (must contain
                        'focal_length_mm', 'sensor_width_mm',
                        'sensor_height_mm', 'resolution_px').
            altitude_m (float): Height above the target plane, in metres.

        Returns:
            dict: {
                "horizontal_fov_m": float,
                "vertical_fov_m":   float,
                "h_fov_deg":        float,
                "v_fov_deg":        float,
                "pixel_size_mm":    float
            }
        """
        focal_length_mm  = camera["focal_length_mm"]
        sensor_width_mm  = camera["sensor_width_mm"]
        sensor_height_mm = camera["sensor_height_mm"]
        res_x, _         = camera["resolution_px"]

        h_fov_deg = 2 * math.degrees(math.atan(sensor_width_mm  / (2 * focal_length_mm)))
        v_fov_deg = 2 * math.degrees(math.atan(sensor_height_mm / (2 * focal_length_mm)))

        horizontal_fov_m = 2 * altitude_m * math.tan(math.radians(h_fov_deg / 2))
        vertical_fov_m   = 2 * altitude_m * math.tan(math.radians(v_fov_deg / 2))

        pixel_size_mm = (horizontal_fov_m * 1_000) / res_x  # m ➜ mm

        return {
            "horizontal_fov_m": horizontal_fov_m,
            "vertical_fov_m":   vertical_fov_m,
            "h_fov_deg":        h_fov_deg,
            "v_fov_deg":        v_fov_deg,
            "pixel_size_mm":    pixel_size_mm
        }


    # Visualize the scan area in a local (x, y) coordinate frame
    def _visualize_scan_area_km(self, polygon_points, heading_deg):
        """
        Visualize the drone scan area in a local (x, y) coordinate frame in kilometers.


        Args:
            polygon_points (list): List of (y, x) tuples forming the polygon in kilometers.
            heading_deg (float): Heading in degrees (0° = up, 90° = right, etc.).
        """
        # Unpack the points
        ys = [pt[0] for pt in polygon_points] + [polygon_points[0][0]]
        xs = [pt[1] for pt in polygon_points] + [polygon_points[0][1]]

        # Compute centroid for heading arrow origin
        centroid_y = np.mean([pt[0] for pt in polygon_points])
        centroid_x = np.mean([pt[1] for pt in polygon_points])

        # Arrow direction from heading
        heading_rad = math.radians(heading_deg)
        arrow_length = 0.05  # km = 50 meters
        dx = arrow_length * math.sin(heading_rad)
        dy = arrow_length * math.cos(heading_rad)

        # Plot
        plt.figure(figsize=(6, 6))
        plt.plot(xs, ys, 'b-', linewidth=2, label='Scan Area')
        plt.fill(xs, ys, color='lightblue', alpha=0.4)
        plt.arrow(
            centroid_x, centroid_y, dx, dy,
            head_width=0.01, head_length=0.015,
            fc='red', ec='red', label='Heading'
        )
        plt.axis('equal')
        plt.xlabel('X (km)')
        plt.ylabel('Y (km)')
        plt.title(f'Drone Scan Area (Heading: {heading_deg:.1f}°)')
        plt.legend()
        plt.grid(True)
        plt.show()



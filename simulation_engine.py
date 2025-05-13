class SimulationEngine:
    """
    Main simulation engine that coordinates all actors and runs the simulation.
    """
    def __init__(self, ocean_map, drones, catching_system, time_step_seconds=300.0):
        """
        Initialize the simulation engine with all necessary components.
        
        Args:
            ocean_map (OceanMap): The ocean map for the simulation
            drones (list): List of Drone objects
            catching_system (CatchingSystem): The system for catching particles
        """
        self.ocean_map = ocean_map
        self.drones = drones
        self.catching_system = catching_system
        self.current_step = 0
        self.stats = {
            'total_steps': 0,
            'total_particles_detected': 0,
            'total_particles_processed': 0
        }
        
        # Track drone positions and trajectories for visualization
        self.drone_trajectories = {i: [(drone.x_km, drone.y_km)] for i, drone in enumerate(drones)}
        
        # Track catching system trajectory
        self.catching_system_trajectory = [(catching_system.x_km, catching_system.y_km)]
        
        # Track time series data for plotting
        self.time_series_data = {
            'steps': [],
            'cumulative_caught': [0],  # Cumulative particles caught by the system
            'current_caught': [],      # Particles caught in each step
            'drone_densities': {i: [] for i in range(len(drones))},  # Particle density for each drone
            'system_density': []       # Current particle density at system location
        }

        self.time_step_seconds = time_step_seconds  # Time step in seconds
        self.elapsed_time_in_seconds = 0.0  # Simulation time in seconds
        
    def step(self):
        """
        Run a single step of the simulation.
        
        Returns:
            dict: Statistics for this step
        """

        # Update elapsed time
        self.elapsed_time_in_seconds += self.time_step_seconds
        # Update the ocean map
        self.ocean_map.step()
        
        # Update all drones
        particles_detected = 0
        drone_densities = {}
        
        for i, drone in enumerate(self.drones):
            # Pass the ocean map to the drone's step method
            density = drone.step(self.ocean_map)
            if density is not None:
                particles_detected += density
                drone_densities[i] = density
            else:
                drone_densities[i] = 0.0
                
            # Track drone position for trajectory visualization
            self.drone_trajectories[i].append((drone.x_km, drone.y_km))
                
        # Update the catching system
        # Pass all drones and the ocean map to the system's step method
        particles_processed = self.catching_system.step(self.drones, self.ocean_map)
        
        # Update the ocean map to show particles being removed where the system processed them
        if particles_processed > 0:
            # Process particles at the catching system's location
            # The amount is normalized to a 0-1 scale for the density map
            normalized_amount = min(1.0, particles_processed / 50.0)  # 50.0 is the typical capacity
            self.ocean_map.process_particles_at_location(
                self.catching_system.x_km, 
                self.catching_system.y_km, 
                normalized_amount
            )
        
        # Update the catching system trajectory
        self.catching_system_trajectory.append((self.catching_system.x_km, self.catching_system.y_km))
        
        # Get the current density at the system's location
        system_density = self._get_density_at_location(self.catching_system.x_km, self.catching_system.y_km)
        
        # Update time series data
        self.time_series_data['steps'].append(self.current_step)
        self.time_series_data['current_caught'].append(particles_processed)
        self.time_series_data['cumulative_caught'].append(
            self.time_series_data['cumulative_caught'][-1] + particles_processed)
        
        for i in range(len(self.drones)):
            if i in drone_densities:
                self.time_series_data['drone_densities'][i].append(drone_densities[i])
            else:
                self.time_series_data['drone_densities'][i].append(0.0)
                
        self.time_series_data['system_density'].append(system_density)
        
        # Update statistics
        self.current_step += 1
        self.stats['total_steps'] = self.current_step
        self.stats['total_particles_detected'] += particles_detected
        self.stats['total_particles_processed'] += particles_processed
        
        # Return statistics for this step
        step_stats = {
            'step': self.current_step,
            'particles_detected': particles_detected,
            'particles_processed': particles_processed
        }
        
        return step_stats
        
    def run(self, num_steps):
        """
        Run the simulation for a specified number of steps.
        
        Args:
            num_steps (int): Number of steps to run
            
        Returns:
            dict: Final statistics for the simulation
        """
        for _ in range(num_steps):
            self.step()
            
        return self.stats
        
    def _get_density_at_location(self, x_km, y_km):
        """
        Get the particle density at a specific location.
        
        Args:
            x_km (float): X position in kilometers from the left edge
            y_km (float): Y position in kilometers from the bottom edge
            
        Returns:
            float: Particle density at the location (0.0 to 1.0)
        """
        # Create a simple polygon around the position
        polygon = [
            (x_km - 0.5, y_km - 0.5),
            (x_km + 0.5, y_km - 0.5),
            (x_km + 0.5, y_km + 0.5),
            (x_km - 0.5, y_km + 0.5)
        ]
        
        # Get the density from the ocean map
        return self.ocean_map.get_particles_in_area(polygon)

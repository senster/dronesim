class SimulationEngine:
    """
    Main simulation engine that coordinates all actors and runs the simulation.
    """
    def __init__(self, ocean_map, drones, catching_system):
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
        self.drone_trajectories = {i: [(drone.long, drone.lat)] for i, drone in enumerate(drones)}
        
        # Track catching system trajectory
        self.catching_system_trajectory = [(catching_system.long, catching_system.lat)]
        
        # Track time series data for plotting
        self.time_series_data = {
            'steps': [],
            'cumulative_caught': [0],  # Cumulative particles caught by the system
            'current_caught': [],      # Particles caught in each step
            'drone_densities': {i: [] for i in range(len(drones))},  # Particle density for each drone
            'system_density': []       # Current particle density at system location
        }
        
    def step(self):
        """
        Run a single step of the simulation.
        
        Returns:
            dict: Statistics for this step
        """
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
            self.drone_trajectories[i].append((drone.long, drone.lat))
                
        # Update the catching system
        # Pass all drones to the system's step method
        particles_processed = self.catching_system.step(self.drones)
        
        # Update the ocean map to show particles being removed where the system processed them
        if particles_processed > 0:
            # Process particles at the catching system's location
            # The amount is normalized to a 0-1 scale for the density map
            normalized_amount = min(1.0, particles_processed / 50.0)  # 50.0 is the typical capacity
            self.ocean_map.process_particles_at_location(
                self.catching_system.lat, 
                self.catching_system.long, 
                normalized_amount
            )
        
        # Update the catching system trajectory
        self.catching_system_trajectory.append((self.catching_system.long, self.catching_system.lat))
        
        # Get the current density at the system's location
        system_density = self._get_density_at_location(self.catching_system.lat, self.catching_system.long)
        
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
        
    def _get_density_at_location(self, lat, long):
        """
        Get the particle density at a specific location.
        
        Args:
            lat (float): Latitude position
            long (float): Longitude position
            
        Returns:
            float: Particle density at the specified location
        """
        # Create a simple polygon around the point
        polygon = [
            (lat - 0.5, long - 0.5),
            (lat + 0.5, long - 0.5),
            (lat + 0.5, long + 0.5),
            (lat - 0.5, long + 0.5)
        ]
        
        # Get the density from the ocean map
        return self.ocean_map.get_particles_in_area(polygon)

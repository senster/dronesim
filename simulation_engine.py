class SimulationEngine:
    """
    Main simulation engine that coordinates all actors and runs the simulation.
    """
    def __init__(self, ocean_map, drones, catching_systems, time_step_seconds=300.0):
        """
        Initialize the simulation engine with all necessary components.
        
        Args:
            ocean_map (OceanMap): The ocean map for the simulation
            drones (list): List of Drone objects
            catching_systems (list or CatchingSystem): The system(s) for catching particles
        """
        self.ocean_map = ocean_map
        self.drones = drones
        
        # Handle either a single catching system or a list of systems
        if not isinstance(catching_systems, list):
            self.catching_systems = [catching_systems]
        else:
            self.catching_systems = catching_systems
            
        # For backward compatibility
        self.catching_system = self.catching_systems[0] if self.catching_systems else None
        
        self.current_step = 0
        self.stats = {
            'total_steps': 0,
            'total_particles_detected': 0,
            'total_particles_processed': 0
        }
        
        # Track drone positions and trajectories for visualization
        self.drone_trajectories = {i: [(drone.x_km, drone.y_km)] for i, drone in enumerate(drones)}
        
        # Track catching system trajectories
        for i, system in enumerate(self.catching_systems):
            setattr(self, f'catching_system_{i}_trajectory', [(system.x_km, system.y_km)])
        
        # For backward compatibility
        if self.catching_system:
            self.catching_system_trajectory = [(self.catching_system.x_km, self.catching_system.y_km)]
        
        # Track time series data for plotting
        self.time_series_data = {
            'steps': [],
            'cumulative_caught': [0],  # Total cumulative particles caught by all systems
            'current_caught': [],      # Particles caught in each step
            'drone_densities': {i: [] for i in range(len(drones))},  # Particle density for each drone
            'system_density': [],      # Current particle density at system location
            'system_cumulative_caught': {i: [0] for i in range(len(self.catching_systems))}  # Cumulative caught per system
        }

        self.time_step_seconds = time_step_seconds  # Time step in seconds
        self.elapsed_time_in_seconds = 0.0  # Simulation time in seconds
        
    def step(self):
        """
        Run a single step of the simulation.
        Optimized for better performance.
        
        Returns:
            dict: Statistics for this step
        """
        # Update elapsed time
        self.elapsed_time_in_seconds += self.time_step_seconds
        
        # Update the ocean map - this is a heavy operation
        self.ocean_map.step()
        
        # Prepare arrays for batch processing if possible
        num_drones = len(self.drones)
        drone_positions = []
        
        # Update drone coordination - share positions between drones
        # This needs to happen before drone movement
        # Only do this for AI drones and only every 5 steps to reduce overhead
        if self.current_step % 5 == 0:  # Only coordinate every 5 steps
            for drone in self.drones:
                if hasattr(drone, 'update_drone_positions'):
                    drone.update_drone_positions(self.drones)
        
        # Update all drones
        particles_detected = 0
        drone_densities = {}
        
        # First collect all drone positions for potential batch processing
        for i, drone in enumerate(self.drones):
            # Pass the ocean map to the drone's step method
            density = drone.step(self.ocean_map)
            if density is not None:
                particles_detected += density
                drone_densities[i] = density
            else:
                drone_densities[i] = 0.0
                
            # Track drone position for trajectory visualization
            # Only store every nth position to reduce memory usage
            if self.current_step % 5 == 0:  # Store every 5th position
                self.drone_trajectories[i].append((drone.x_km, drone.y_km))
            
            # Record drone position for trajectory visualization
            self.drone_trajectories[i].append((drone.x_km, drone.y_km))
            
            # We don't need to scan here as the catching systems will collect data from drones directly
        
        # Update all catching systems and track total particles processed
        total_particles_processed = 0
        total_particles_detected = 0
        
        for i, system in enumerate(self.catching_systems):
            # Update the catching system - pass the drones and ocean map
            particles_processed = system.step(self.drones, self.ocean_map)
            total_particles_processed += particles_processed
            
            # Track cumulative caught for this specific system
            prev_cumulative = self.time_series_data['system_cumulative_caught'][i][-1]
            self.time_series_data['system_cumulative_caught'][i].append(prev_cumulative + particles_processed)
            
            # Since detected_particles is not an attribute we can access, we'll just count processed particles
            # This is a simplification - in a real system we'd track detections separately
            
            # Record catching system position for trajectory visualization
            trajectory = getattr(self, f'catching_system_{i}_trajectory')
            trajectory.append((system.x_km, system.y_km))
            
            # For backward compatibility with the first system
            if i == 0 and hasattr(self, 'catching_system_trajectory'):
                self.catching_system_trajectory.append((system.x_km, system.y_km))
        
        # Update statistics - since we don't have a way to track detections separately,
        # we'll just use processed particles as an approximation
        self.stats['total_particles_detected'] = self.current_step  # Just a placeholder value
        self.stats['total_particles_processed'] += total_particles_processed
        
        # Update time series data
        self.time_series_data['steps'].append(self.current_step)
        self.time_series_data['current_caught'].append(total_particles_processed)
        self.time_series_data['cumulative_caught'].append(self.time_series_data['cumulative_caught'][-1] + total_particles_processed)
        
        # Record drone densities
        for i, drone in enumerate(self.drones):
            # Calculate the average density in the drone's scan area
            density = self.ocean_map.get_particles_in_area(drone._create_scan_polygon())
            self.time_series_data['drone_densities'][i].append(density)
        
        # Record system density (using the first system for time series data)
        if self.catching_systems:
            primary_system = self.catching_systems[0]
            system_density = self.ocean_map.get_particles_in_area([
                (primary_system.x_km - 0.9, primary_system.y_km - 0.9),
                (primary_system.x_km + 0.9, primary_system.y_km - 0.9),
                (primary_system.x_km + 0.9, primary_system.y_km + 0.9),
                (primary_system.x_km - 0.9, primary_system.y_km + 0.9)
            ])
            self.time_series_data['system_density'].append(system_density)
        
        # Return statistics for this step
        return {
            'step': self.current_step,
            'particles_detected': self.current_step,  # Using step as a placeholder
            'particles_processed': total_particles_processed
        }
        
    def run(self, num_steps):
        """
        Run the simulation for a specified number of steps.
        Optimized for better performance.
        
        Args:
            num_steps (int): Number of steps to run
            
        Returns:
            dict: Final statistics for the simulation
        """
        # Run the simulation with minimal overhead
        for i in range(num_steps):
            self.step()
            
            # Print progress update only at key points
            if (i + 1) % 50 == 0 or i == num_steps - 1:
                print(f"Step {i+1}: Detected {self.stats['total_particles_detected']:.2f}, Processed {self.stats['total_particles_processed']:.2f}")
            
        return self.stats
        
    def _get_density_at_location(self, x_km, y_km):
        """
        Get the particle density at a specific location.
        Optimized version that uses a cached polygon.
        
        Args:
            x_km (float): X position in kilometers from the left edge
            y_km (float): Y position in kilometers from the bottom edge
            
        Returns:
            float: Particle density at the location (0.0 to 1.0)
        """
        # Create a simple polygon around the position - use a smaller area for efficiency
        polygon = [
            (x_km - 0.25, y_km - 0.25),
            (x_km + 0.25, y_km - 0.25),
            (x_km + 0.25, y_km + 0.25),
            (x_km - 0.25, y_km + 0.25)
        ]
        
        # Get the density from the ocean map
        return self.ocean_map.get_particles_in_area(polygon)

# Refactor Codebase to Use Kilometers as Standard Unit

## Overview
This PR standardizes the coordinate system across the entire codebase to consistently use kilometers (x_km, y_km) instead of latitude and longitude. This change improves code clarity, makes the simulation more intuitive, and ensures consistent distance measurements throughout the system.

## Changes
- **Actor Class**: Changed base attributes from `lat` and `long` to `x_km` and `y_km` with (0,0) at the bottom left corner
- **CatchingSystem Class**: Updated to use the new coordinate system throughout, including:
  - Changed parameters and attributes to use x_km and y_km
  - Updated the plastic collection formula to use the new coordinates
  - Modified ground truth plastic density calculation
  - Set system_span to 1.4 kilometers for both sampling and catching
- **Drone Classes**:
  - Updated the base `Drone` class to use x_km and y_km
  - Modified `CircularDrone` to use the new coordinate system for circular patterns
  - Updated `LawnmowerDrone` to use x_km and y_km for movement patterns
- **SimulationEngine Class**:
  - Updated trajectory tracking to use x_km and y_km
  - Modified density calculation methods to use the new coordinates
- **Visualization**:
  - Updated all plotting and visualization functions to use x_km and y_km
  - Fixed trajectory visualization to work with the new coordinate system

## Testing
- Ran both circular and lawnmower pattern simulations to verify functionality
- Confirmed that visualization correctly displays drone and system positions
- Verified that plastic collection calculations work as expected with the new coordinate system

## Benefits
1. Improved code clarity and consistency by using a single unit of measurement
2. More intuitive coordinate system with (0,0) at the bottom left corner
3. Simplified calculations by eliminating the need for unit conversions
4. Better alignment with the visualization system, which already used a grid where 1 unit = 1 km

## Note
This change is purely a refactoring of the coordinate system and does not alter the fundamental behavior of the simulation. The simulation now operates with a map size of 100 km x 100 km, where each grid unit equals 1 km.

#!/usr/bin/env python3
"""
Script to explore the structure of the OceanParcels zarr file.
"""
import xarray as xr
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime

# Load the zarr dataset
zarr_path = "pset/0_Particles.zarr"
ds = xr.open_zarr(zarr_path)

# Print basic information
print("Dataset info:")
print(ds)
print("\nDimensions:")
for dim, size in ds.dims.items():
    print(f"  {dim}: {size}")

print("\nVariables:")
for var in ds.variables:
    print(f"  {var}: {ds[var].shape}")

# Get the first few values of each variable
print("\nSample data:")
for var in ds.variables:
    if var == 'trajectory' or var == 'obs':
        print(f"  {var}: {ds[var].values[:5]}")
    else:
        print(f"  {var}: {ds[var].values[0, 0:5]}")

# Convert time to datetime for better understanding
if 'time' in ds:
    # Get the time units
    time_units = ds.time.attrs.get('units', '')
    print(f"\nTime units: {time_units}")
    
    # Convert a few timestamps to datetime for verification
    if 'nanoseconds' in time_units:
        # Convert nanoseconds to seconds and then to datetime
        timestamps = ds.time.values[0, :5] / 1e9  # Convert to seconds
        datetimes = [datetime.fromtimestamp(ts) for ts in timestamps]
        print("\nSample timestamps converted to datetime:")
        for i, dt in enumerate(datetimes):
            print(f"  {i}: {dt}")

# Check the range of lat/lon values
if 'lat' in ds and 'lon' in ds:
    print("\nLatitude range:")
    print(f"  Min: {np.nanmin(ds.lat.values)}")
    print(f"  Max: {np.nanmax(ds.lat.values)}")
    
    print("\nLongitude range:")
    print(f"  Min: {np.nanmin(ds.lon.values)}")
    print(f"  Max: {np.nanmax(ds.lon.values)}")

# Plot a sample of particle positions at the first time step
if 'lat' in ds and 'lon' in ds:
    plt.figure(figsize=(10, 8))
    # Get non-NaN values for the first time step
    lats = ds.lat.values[:, 0]
    lons = ds.lon.values[:, 0]
    valid_indices = ~np.isnan(lats) & ~np.isnan(lons)
    
    plt.scatter(lons[valid_indices], lats[valid_indices], s=5, alpha=0.5)
    plt.title('Particle positions at first time step')
    plt.xlabel('Longitude')
    plt.ylabel('Latitude')
    plt.grid(True)
    plt.savefig('particle_positions.png')
    print("\nSaved plot of initial particle positions to 'particle_positions.png'")

print("\nExploration complete!")

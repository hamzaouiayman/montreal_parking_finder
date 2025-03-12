"""
Module for loading and preprocessing parking data.
"""

import pandas as pd
from multiprocessing import Pool
from functools import partial
import time
import os

from montreal_parking_finder.config import BATCH_SIZE, NUM_PROCESSES
from montreal_parking_finder.geo.distance import haversine_distance


def load_parking_data(file_path):
    """
    Load the parking data from CSV file.
    
    Args:
        file_path: Path to the CSV file
        
    Returns:
        DataFrame containing the parking data
    """
    print(f"Loading data from {file_path}...")
    try:
        df = pd.read_csv(file_path, encoding='utf-8')
        print(f"Loaded {len(df)} rows of data.")
        return df
    except Exception as e:
        print(f"Error loading data: {e}")
        return pd.DataFrame()


def _calculate_distance_for_row(row, center_lat, center_lon):
    """
    Calculate distance from center for a single row.
    
    Args:
        row: DataFrame row
        center_lat, center_lon: Center coordinates
    
    Returns:
        Row with distance_to_center added
    """
    if pd.notna(row['Latitude']) and pd.notna(row['Longitude']):
        row['distance_to_center'] = haversine_distance(
            center_lat, center_lon, row['Latitude'], row['Longitude']
        )
    else:
        row['distance_to_center'] = float('inf')
    return row


def _process_batch(batch_df, center_lat, center_lon):
    """
    Process a batch of rows to add distance calculations.
    
    Args:
        batch_df: DataFrame batch
        center_lat, center_lon: Center coordinates
    
    Returns:
        Processed batch with distances
    """
    return batch_df.apply(
        lambda row: _calculate_distance_for_row(row, center_lat, center_lon),
        axis=1
    )


def filter_by_distance(df, center_lat, center_lon, radius_km):
    """
    Filter signs to include only those within the specified radius using multiprocessing.
    
    Args:
        df: DataFrame containing parking data
        center_lat, center_lon: Center coordinates
        radius_km: Radius in kilometers
        
    Returns:
        DataFrame filtered by distance
    """
    print(f"Filtering signs within {radius_km}km of ({center_lat}, {center_lon})...")
    start_time = time.time()
    
    # Split the dataframe into batches
    batch_size = min(BATCH_SIZE, max(1000, len(df) // (NUM_PROCESSES * 2)))
    df_batches = [df[i:i+batch_size] for i in range(0, len(df), batch_size)]
    
    print(f"Processing {len(df_batches)} batches with {NUM_PROCESSES} processes...")
    
    # Create a partial function with fixed center coordinates
    process_func = partial(_process_batch, center_lat=center_lat, center_lon=center_lon)
    
    # Process batches in parallel
    with Pool(processes=NUM_PROCESSES) as pool:
        processed_batches = pool.map(process_func, df_batches)
    
    # Combine results
    df_with_distance = pd.concat(processed_batches)
    
    # Filter by distance
    df_filtered = df_with_distance[df_with_distance['distance_to_center'] <= radius_km]
    
    end_time = time.time()
    print(f"Filtered to {len(df_filtered)} signs within {radius_km}km radius in {end_time - start_time:.2f} seconds.")
    
    return df_filtered

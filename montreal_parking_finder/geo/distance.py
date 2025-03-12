"""
Module for geographic distance calculations.
"""

import math


def haversine_distance(lat1, lon1, lat2, lon2):
    """
    Calculate the distance between two points on earth given by latitude/longitude.
    Returns distance in kilometers.
    
    Args:
        lat1, lon1: Coordinates of first point
        lat2, lon2: Coordinates of second point
        
    Returns:
        Distance in kilometers
    """
    # Convert decimal degrees to radians
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    
    # Haversine formula
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    r = 6371  # Radius of Earth in kilometers
    
    return c * r


def filter_coordinates_by_distance(coordinates, center_lat, center_lon, radius_km):
    """
    Filter a list of coordinate pairs to include only those within the specified radius.
    
    Args:
        coordinates: List of (lat, lon) pairs
        center_lat, center_lon: Center coordinates
        radius_km: Radius in kilometers
        
    Returns:
        List of (lat, lon) pairs within the radius
    """
    return [
        (lat, lon) for lat, lon in coordinates
        if haversine_distance(center_lat, center_lon, lat, lon) <= radius_km
    ]

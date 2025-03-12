"""
Module for OpenStreetMap integration.
"""

import requests
import time
from shapely.geometry import Point, LineString
import multiprocessing
import json
from tqdm import tqdm

from montreal_parking_finder.config import OVERPASS_API_URL, OVERPASS_API_DELAY


def get_nearest_street(lat, lon, radius=100, retry_count=3, retry_delay=2):
    """
    Query OpenStreetMap to find the nearest street to the given coordinates.
    
    Args:
        lat: Latitude of the point
        lon: Longitude of the point
        radius: Search radius in meters (default: 100)
        retry_count: Number of retries on failure
        retry_delay: Delay between retries in seconds
        
    Returns:
        Dictionary containing street information or None if no street found
    """
    # Overpass API query to find the nearest highway/road
    overpass_query = f"""
    [out:json];
    way(around:{radius},{lat},{lon})["highway"];
    out geom;
    """
    
    for attempt in range(retry_count):
        try:
            # Add a small delay to avoid overloading the API
            time.sleep(OVERPASS_API_DELAY)
            
            response = requests.post(OVERPASS_API_URL, data=overpass_query, timeout=10)
            response.raise_for_status()  # Raise exception for 4XX/5XX responses
            data = response.json()
            
            if 'elements' in data and len(data['elements']) > 0:
                # Sort by distance to get the nearest street
                streets = []
                for element in data['elements']:
                    if 'geometry' in element and len(element['geometry']) >= 2:
                        # Create a LineString from the street geometry
                        coords = [(node['lon'], node['lat']) for node in element['geometry']]
                        street_line = LineString(coords)
                        
                        # Calculate distance from the point to the street
                        point = Point(lon, lat)
                        distance = point.distance(street_line)
                        
                        streets.append({
                            'id': element['id'],
                            'name': element.get('tags', {}).get('name', 'Unknown'),
                            'highway': element.get('tags', {}).get('highway', 'Unknown'),
                            'geometry': street_line,
                            'distance': distance
                        })
                
                if streets:
                    # Return the nearest street
                    return min(streets, key=lambda x: x['distance'])
            
            return None
        
        except (requests.RequestException, json.JSONDecodeError) as e:
            if attempt < retry_count - 1:
                print(f"Error fetching street data (attempt {attempt+1}/{retry_count}): {e}")
                time.sleep(retry_delay)
            else:
                print(f"Failed to fetch street data after {retry_count} attempts: {e}")
                return None


def get_streets_batch(coordinates, radius=100):
    """
    Process a batch of coordinates to get nearest streets.
    
    Args:
        coordinates: List of (lat, lon, id) tuples
        radius: Search radius in meters
    
    Returns:
        List of (id, street) tuples where street is the result from get_nearest_street
    """
    results = []
    for lat, lon, id in coordinates:
        street = get_nearest_street(lat, lon, radius)
        results.append((id, street))
    return results


def get_streets_parallel(df, radius=100, batch_size=20):
    """
    Get nearest streets for multiple coordinates in parallel.
    
    Args:
        df: DataFrame with Latitude and Longitude columns
        radius: Search radius in meters
        batch_size: Number of coordinates per batch
    
    Returns:
        Dictionary mapping row indices to street information
    """
    # Prepare coordinate batches
    coords = [(row['Latitude'], row['Longitude'], idx) 
              for idx, row in df.iterrows() 
              if not (pd.isna(row['Latitude']) or pd.isna(row['Longitude']))]
    
    batches = [coords[i:i+batch_size] for i in range(0, len(coords), batch_size)]
    
    # Setup multiprocessing
    num_processes = min(multiprocessing.cpu_count(), 4)  # Limit to avoid API rate limits
    print(f"Getting street data for {len(coords)} coordinates using {num_processes} processes...")
    
    # Process batches
    results = {}
    with multiprocessing.Pool(processes=num_processes) as pool:
        batch_results = []
        for batch in tqdm(batches):
            batch_results.extend(pool.apply(get_streets_batch, args=(batch, radius)))
    
    # Convert results to dictionary
    for id, street in batch_results:
        results[id] = street
    
    print(f"Got street data for {len(results)} coordinates.")
    return results


def create_street_interval(street_line, sign_point, direction, interval_length=50):
    """
    Create an interval along the street based on the sign location and arrow direction.
    
    Args:
        street_line: LineString geometry of the street
        sign_point: Point geometry of the sign
        direction: Direction of the arrow ('left', 'right', 'both_sides', 'up')
        interval_length: Length of the interval in meters (default: 50)
        
    Returns:
        List of LineString objects representing intervals
    """
    # Find the closest point on the street to the sign
    nearest_point = street_line.interpolate(street_line.project(sign_point))
    
    # Get coordinates of the nearest point
    nearest_x, nearest_y = nearest_point.x, nearest_point.y
    
    # Find which segment of the street contains or is closest to the nearest_point
    min_distance = float('inf')
    segment_index = 0
    
    coords = list(street_line.coords)
    
    for i in range(len(coords) - 1):
        segment = LineString([coords[i], coords[i+1]])
        distance = nearest_point.distance(segment)
        
        if distance < min_distance:
            min_distance = distance
            segment_index = i
    
    # Calculate the bearing/direction of the street segment
    start_x, start_y = coords[segment_index]
    end_x, end_y = coords[segment_index + 1]
    
    # Create intervals based on direction
    if direction == 'both_sides':
        # Create interval extending in both directions
        interval_before = LineString([
            (start_x, start_y),
            (nearest_x, nearest_y)
        ])
        
        interval_after = LineString([
            (nearest_x, nearest_y),
            (end_x, end_y)
        ])
        
        return [interval_before, interval_after]
    
    elif direction == 'left':
        # Create interval extending to the left of the sign
        return [LineString([
            (start_x, start_y),
            (nearest_x, nearest_y)
        ])]
    
    elif direction == 'right':
        # Create interval extending to the right of the sign
        return [LineString([
            (nearest_x, nearest_y),
            (end_x, end_y)
        ])]
    
    elif direction == 'up':
        # Create a small interval centered on the sign
        midpoint = street_line.interpolate(street_line.project(sign_point) + interval_length/2)
        midpoint_neg = street_line.interpolate(max(0, street_line.project(sign_point) - interval_length/2))
        
        return [LineString([
            (midpoint_neg.x, midpoint_neg.y),
            (midpoint.x, midpoint.y)
        ])]
    
    # Default: return a simple point buffer around the nearest point
    return [LineString([
        (nearest_x - 0.0001, nearest_y),
        (nearest_x + 0.0001, nearest_y)
    ])]

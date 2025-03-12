"""
Database operations for the Montreal Parking Finder.
"""

import json
import pandas as pd
from sqlalchemy import func
from shapely.geometry import LineString, Point
from tqdm import tqdm
import time
from multiprocessing import Pool, cpu_count

from montreal_parking_finder.db.models import (
    ParkingSign, ParkingInterval, CachedStreetData, 
    AreaSummary, get_session, init_db
)
from montreal_parking_finder.config import BATCH_SIZE, NUM_PROCESSES
from montreal_parking_finder.geo.osm import get_nearest_street, create_street_interval


def create_database():
    """
    Create the database and all tables.
    """
    print("Creating database...")
    engine = init_db()
    print("Database created successfully.")
    return engine


def store_signs(df, batch_size=1000):
    """
    Store parking signs from DataFrame to database.
    
    Args:
        df: DataFrame containing processed parking sign data
        batch_size: Number of signs to insert in each batch
    
    Returns:
        Number of signs stored
    """
    print(f"Storing {len(df)} parking signs to database...")
    session = get_session()
    
    try:
        count = 0
        total_batches = (len(df) + batch_size - 1) // batch_size
        
        for i in tqdm(range(0, len(df), batch_size), total=total_batches, desc="Storing signs"):
            batch_df = df.iloc[i:i+batch_size]
            
            signs = []
            for _, row in batch_df.iterrows():
                # Skip if missing coordinates
                if pd.isna(row['Latitude']) or pd.isna(row['Longitude']):
                    continue
                
                # Create sign object
                sign = ParkingSign.from_dataframe_row(row)
                signs.append(sign)
            
            if signs:
                session.bulk_save_objects(signs)
                session.commit()
                count += len(signs)
        
        print(f"Stored {count} parking signs.")
        return count
    
    except Exception as e:
        session.rollback()
        print(f"Error storing signs: {e}")
        raise
    
    finally:
        session.close()


def _process_sign_intervals(sign_data):
    """
    Process intervals for a single sign (for parallel processing).
    
    Args:
        sign_data: Tuple of (sign_id, lat, lon, direction)
    
    Returns:
        List of intervals as dictionaries
    """
    sign_id, lat, lon, direction = sign_data
    
    # Get nearest street
    street = get_nearest_street(lat, lon)
    if not street:
        return []
    
    # Create intervals
    sign_point = Point(lon, lat)
    intervals = create_street_interval(street['geometry'], sign_point, direction)
    
    result = []
    for interval in intervals:
        coords = list(interval.coords)
        if len(coords) < 2:
            continue
            
        start_lon, start_lat = coords[0]
        end_lon, end_lat = coords[-1]
        
        result.append({
            'sign_id': sign_id,
            'street_name': street['name'],
            'geometry': json.dumps({
                'type': 'LineString',
                'coordinates': coords
            }),
            'start_lat': start_lat,
            'start_lon': start_lon,
            'end_lat': end_lat,
            'end_lon': end_lon
        })
    
    return result


def generate_intervals_parallel(batch_size=100):
    """
    Generate parking intervals for all signs in parallel.
    
    Args:
        batch_size: Number of signs to process in each batch
    
    Returns:
        Number of intervals created
    """
    print("Generating parking intervals...")
    session = get_session()
    
    try:
        # Get all signs without intervals
        signs = session.query(
            ParkingSign.id, ParkingSign.latitude, ParkingSign.longitude, ParkingSign.arrow_direction
        ).outerjoin(
            ParkingInterval
        ).filter(
            ParkingInterval.id == None
        ).all()
        
        if not signs:
            print("No signs found without intervals.")
            return 0
        
        print(f"Processing intervals for {len(signs)} signs...")
        
        # Prepare sign data for parallel processing
        sign_data = [(sign[0], sign[1], sign[2], sign[3]) for sign in signs]
        
        # Process in batches to avoid memory issues
        all_intervals = []
        for i in tqdm(range(0, len(sign_data), batch_size), desc="Processing sign batches"):
            batch = sign_data[i:i+batch_size]
            
            # Process batch in parallel
            with Pool(processes=min(NUM_PROCESSES, len(batch))) as pool:
                batch_results = pool.map(_process_sign_intervals, batch)
            
            # Flatten results
            for intervals in batch_results:
                all_intervals.extend(intervals)
        
        print(f"Generated {len(all_intervals)} intervals. Storing to database...")
        
        # Store intervals in batches
        interval_count = 0
        interval_batches = [all_intervals[i:i+1000] for i in range(0, len(all_intervals), 1000)]
        
        for batch in tqdm(interval_batches, desc="Storing intervals"):
            intervals = []
            for interval_data in batch:
                interval = ParkingInterval(
                    sign_id=interval_data['sign_id'],
                    street_name=interval_data['street_name'],
                    geometry=interval_data['geometry'],
                    start_lat=interval_data['start_lat'],
                    start_lon=interval_data['start_lon'],
                    end_lat=interval_data['end_lat'],
                    end_lon=interval_data['end_lon']
                )
                intervals.append(interval)
            
            if intervals:
                session.bulk_save_objects(intervals)
                session.commit()
                interval_count += len(intervals)
        
        print(f"Created {interval_count} parking intervals.")
        return interval_count
    
    except Exception as e:
        session.rollback()
        print(f"Error generating intervals: {e}")
        raise
    
    finally:
        session.close()


def get_area_parking_data(center_lat, center_lon, radius_km):
    """
    Get all parking data for a specific area.
    
    Args:
        center_lat, center_lon: Center coordinates
        radius_km: Radius in kilometers
    
    Returns:
        DataFrame containing signs and intervals for the area
    """
    print(f"Getting parking data for area: ({center_lat}, {center_lon}) with {radius_km}km radius...")
    session = get_session()
    
    try:
        # Convert radius from km to degrees (approximate)
        # 1 degree of latitude is approximately 111 km
        radius_deg = radius_km / 111.0
        
        # Query for signs within the radius
        sign_data = (
            session.query(
                ParkingSign.id,
                ParkingSign.latitude,
                ParkingSign.longitude,
                ParkingSign.description,
                ParkingSign.arrow_direction,
                ParkingSign.is_restricted,
                ParkingSign.is_all_time,
                ParkingSign.is_paid,
                ParkingSign.raw_restriction
            )
            .filter(
                ParkingSign.latitude.between(center_lat - radius_deg, center_lat + radius_deg),
                ParkingSign.longitude.between(center_lon - radius_deg, center_lon + radius_deg)
            )
            .all()
        )
        
        # Calculate exact distances and filter
        sign_ids = []
        signs_list = []
        
        for sign in sign_data:
            # Calculate Euclidean distance (simplified)
            # For more accurate filtering, could use the haversine function
            distance = (
                ((sign.latitude - center_lat) * 111.0) ** 2 +
                ((sign.longitude - center_lon) * 85.0) ** 2
            ) ** 0.5
            
            if distance <= radius_km:
                sign_ids.append(sign.id)
                signs_list.append({
                    'id': sign.id,
                    'latitude': sign.latitude,
                    'longitude': sign.longitude,
                    'description': sign.description,
                    'arrow_direction': sign.arrow_direction,
                    'is_restricted': sign.is_restricted,
                    'is_all_time': sign.is_all_time,
                    'is_paid': sign.is_paid,
                    'parsed_restriction': json.loads(sign.raw_restriction) if sign.raw_restriction else {}
                })
        
        # Query for intervals associated with these signs
        if sign_ids:
            interval_data = (
                session.query(
                    ParkingInterval.id,
                    ParkingInterval.sign_id,
                    ParkingInterval.street_name,
                    ParkingInterval.geometry,
                    ParkingInterval.start_lat,
                    ParkingInterval.start_lon,
                    ParkingInterval.end_lat,
                    ParkingInterval.end_lon
                )
                .filter(ParkingInterval.sign_id.in_(sign_ids))
                .all()
            )
            
            intervals_list = [{
                'id': interval.id,
                'sign_id': interval.sign_id,
                'street_name': interval.street_name,
                'geometry': json.loads(interval.geometry) if interval.geometry else None,
                'start_lat': interval.start_lat,
                'start_lon': interval.start_lon,
                'end_lat': interval.end_lat,
                'end_lon': interval.end_lon
            } for interval in interval_data]
        else:
            intervals_list = []
        
        # Create DataFrames
        signs_df = pd.DataFrame(signs_list)
        intervals_df = pd.DataFrame(intervals_list)
        
        print(f"Retrieved {len(signs_df)} signs and {len(intervals_df)} intervals for the area.")
        
        return signs_df, intervals_df
    
    finally:
        session.close()


def create_area_summary(name, center_lat, center_lon, radius_km, total_signs, 
                        total_intervals, free_intervals, restricted_intervals):
    """
    Create or update an area summary.
    
    Args:
        name: Name of the area
        center_lat, center_lon: Center coordinates
        radius_km: Radius in kilometers
        total_signs: Number of signs in the area
        total_intervals: Total number of intervals
        free_intervals: Number of free parking intervals
        restricted_intervals: Number of restricted parking intervals
    
    Returns:
        The area summary object
    """
    session = get_session()
    
    try:
        # Check if summary already exists
        summary = session.query(AreaSummary).filter_by(
            name=name,
            center_lat=center_lat,
            center_lon=center_lon,
            radius_km=radius_km
        ).first()
        
        if summary:
            # Update existing summary
            summary.total_signs = total_signs
            summary.total_intervals = total_intervals
            summary.free_intervals = free_intervals
            summary.restricted_intervals = restricted_intervals
            summary.last_analyzed = func.now()
        else:
            # Create new summary
            summary = AreaSummary(
                name=name,
                center_lat=center_lat,
                center_lon=center_lon,
                radius_km=radius_km,
                total_signs=total_signs,
                total_intervals=total_intervals,
                free_intervals=free_intervals,
                restricted_intervals=restricted_intervals
            )
            session.add(summary)
        
        session.commit()
        return summary
    
    except Exception as e:
        session.rollback()
        print(f"Error creating area summary: {e}")
        raise
    
    finally:
        session.close()


def get_cached_street(lat, lon, radius=100):
    """
    Get cached street data for a location.
    
    Args:
        lat, lon: Coordinates
        radius: Search radius in meters
    
    Returns:
        Cached street data or None if not found
    """
    session = get_session()
    
    try:
        # Allow small variation in coordinates to increase cache hits
        tolerance = 0.0001  # Approximately 10 meters
        
        cached = session.query(CachedStreetData).filter(
            CachedStreetData.latitude.between(lat - tolerance, lat + tolerance),
            CachedStreetData.longitude.between(lon - tolerance, lon + tolerance),
            CachedStreetData.radius >= radius
        ).first()
        
        if cached:
            # Convert to dictionary with LineString geometry
            return {
                'id': cached.street_id,
                'name': cached.street_name,
                'highway': cached.highway_type,
                'geometry': LineString(json.loads(cached.geometry)['coordinates'])
            }
        
        return None
    
    finally:
        session.close()


def cache_street_data(lat, lon, radius, street_data):
    """
    Cache street data for future use.
    
    Args:
        lat, lon: Coordinates
        radius: Search radius in meters
        street_data: Street data to cache
    """
    if not street_data:
        return
    
    session = get_session()
    
    try:
        # Create geometry JSON
        geometry_json = json.dumps({
            'type': 'LineString',
            'coordinates': list(street_data['geometry'].coords)
        })
        
        # Create cache entry
        cached = CachedStreetData(
            latitude=lat,
            longitude=lon,
            radius=radius,
            street_id=str(street_data['id']),
            street_name=street_data['name'],
            highway_type=street_data['highway'],
            geometry=geometry_json
        )
        
        session.add(cached)
        session.commit()
    
    except Exception as e:
        session.rollback()
        print(f"Error caching street data: {e}")
    
    finally:
        session.close()

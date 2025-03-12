"""
Visualization utilities for creating parking maps.
"""

import folium
from folium.plugins import MarkerCluster
from shapely.geometry import LineString, Point
import pandas as pd
import json
import os
from datetime import datetime
import time

from montreal_parking_finder.config import OUTPUT_DIR
from montreal_parking_finder.data.parser import is_parking_allowed


def create_area_map(signs_df, intervals_df, center_lat, center_lon, radius_km, 
                    area_name="Selected Area", current_time=None):
    """
    Create a Folium map for a specific area showing parking restrictions.
    
    Args:
        signs_df: DataFrame containing processed parking signs
        intervals_df: DataFrame containing parking intervals
        center_lat, center_lon: Center coordinates
        radius_km: Radius in kilometers
        area_name: Name of the area
        current_time: Datetime to check restrictions against (default: now)
        
    Returns:
        Folium map object and summary information
    """
    # Default to current time if not specified
    if current_time is None:
        current_time = datetime.now()
    
    print(f"Creating map for {area_name} with {len(signs_df)} signs...")
    
    # Initialize map centered on the specified coordinates
    m = folium.Map(location=[center_lat, center_lon], zoom_start=15)
    
    # Add a marker cluster for the signs
    marker_cluster = MarkerCluster().add_to(m)
    
    # Add a circle to show the radius
    folium.Circle(
        location=[center_lat, center_lon],
        radius=radius_km * 1000,  # Convert km to meters
        fill=True,
        fill_opacity=0.1,
        color="blue",
        popup=f"{radius_km}km Radius"
    ).add_to(m)
    
    # Add center marker
    folium.Marker(
        location=[center_lat, center_lon],
        popup="Center",
        icon=folium.Icon(color='blue', icon='info-sign')
    ).add_to(m)
    
    # Add area name as a title
    title_html = f'''
    <h3 align="center" style="font-size:20px"><b>{area_name}</b></h3>
    <h4 align="center" style="font-size:16px">Parking Status as of {current_time.strftime('%Y-%m-%d %H:%M')}</h4>
    <h5 align="center" style="font-size:14px">{radius_km}km Radius around ({center_lat:.6f}, {center_lon:.6f})</h5>
    '''
    m.get_root().html.add_child(folium.Element(title_html))
    
    # Count for summary
    free_intervals = 0
    restricted_intervals = 0
    
    # Process intervals
    if not intervals_df.empty and not signs_df.empty:
        # Join signs and intervals for complete information
        merged_df = pd.merge(
            intervals_df, 
            signs_df,
            left_on='sign_id', 
            right_on='id', 
            suffixes=('_interval', '_sign')
        )
        
        print(f"Processing {len(merged_df)} merged intervals and signs...")
        
        for _, row in merged_df.iterrows():
            # Determine parking status based on current time
            is_allowed = is_parking_allowed(row['parsed_restriction'], current_time)
            
            # Pick color based on parking status
            color = 'green' if is_allowed else 'red'
            
            # Update counters
            if is_allowed:
                free_intervals += 1
            else:
                restricted_intervals += 1
            
            # Create tooltip with parking info
            tooltip = f"""
            <b>{row['street_name']}</b><br>
            Restriction: {row['description']}<br>
            Parking {'Allowed' if is_allowed else 'Restricted'} at {current_time.strftime('%Y-%m-%d %H:%M')}
            """
            
            # Add marker for the sign
            folium.Marker(
                [row['latitude'], row['longitude']],
                popup=tooltip,
                icon=folium.Icon(color=color, icon='info-sign')
            ).add_to(marker_cluster)
            
            # Process interval geometry
            if isinstance(row['geometry'], dict) and 'coordinates' in row['geometry']:
                # Convert coordinates to [lat, lon] pairs for Folium
                interval_coords = [(y, x) for x, y in row['geometry']['coordinates']]
                
                # Add the line to the map
                folium.PolyLine(
                    interval_coords,
                    color=color,
                    weight=5,
                    opacity=0.7,
                    tooltip=tooltip
                ).add_to(m)
    
    # Add a legend
    legend_html = '''
    <div style="position: fixed; 
        bottom: 50px; left: 50px; width: 180px; height: 90px; 
        border:2px solid grey; z-index:9999; font-size:14px;
        background-color: white; padding: 10px;">
        
        <p><i class="fa fa-map-marker fa-2x" style="color:green"></i> Free Parking</p>
        <p><i class="fa fa-map-marker fa-2x" style="color:red"></i> No Parking / Paid</p>
    </div>
    '''
    m.get_root().html.add_child(folium.Element(legend_html))
    
    print(f"Finished creating map for {area_name}.")
    
    # Summary information
    summary = {
        'name': area_name,
        'center_lat': center_lat,
        'center_lon': center_lon,
        'radius_km': radius_km,
        'total_signs': len(signs_df),
        'total_intervals': free_intervals + restricted_intervals,
        'free_intervals': free_intervals,
        'restricted_intervals': restricted_intervals,
        'timestamp': current_time.strftime('%Y-%m-%d %H:%M'),
    }
    
    return m, summary


def save_map(folium_map, area_name, output_dir=OUTPUT_DIR):
    """
    Save a Folium map to an HTML file.
    
    Args:
        folium_map: Folium map object
        area_name: Name of the area
        output_dir: Directory to save the map
        
    Returns:
        Path to the saved map file
    """
    # Create output directory if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"Created output directory: {output_dir}")
    
    # Clean area name for file naming
    clean_area_name = area_name.replace(' ', '_')
    
    # Add timestamp to filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    map_file = os.path.join(output_dir, f"{clean_area_name}_parking_map_{timestamp}.html")
    
    # Save the map to an HTML file
    folium_map.save(map_file)
    print(f"Saved map to {map_file}")
    
    return map_file


def save_area_summary(summary, output_dir=OUTPUT_DIR):
    """
    Save area summary information to a text file.
    
    Args:
        summary: Dictionary with summary information
        output_dir: Directory to save the summary
        
    Returns:
        Path to the saved summary file
    """
    # Create output directory if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Clean area name for file naming
    clean_area_name = summary['name'].replace(' ', '_')
    
    # Add timestamp to filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    summary_file = os.path.join(output_dir, f"{clean_area_name}_summary_{timestamp}.txt")
    
    # Write summary to file
    with open(summary_file, 'w') as f:
        f.write(f"Parking Summary for {summary['name']}\n")
        f.write(f"Date/Time: {summary['timestamp']}\n")
        f.write(f"Center: {summary['center_lat']}, {summary['center_lon']}\n")
        f.write(f"Radius: {summary['radius_km']}km\n\n")
        f.write(f"Total signs: {summary['total_signs']}\n")
        f.write(f"Total intervals: {summary['total_intervals']}\n")
        f.write(f"Free parking intervals: {summary['free_intervals']}\n")
        f.write(f"Restricted/Paid parking intervals: {summary['restricted_intervals']}\n")
    
    print(f"Saved summary to {summary_file}")
    return summary_file

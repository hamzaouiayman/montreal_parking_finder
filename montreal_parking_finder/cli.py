"""
Command-line interface for the Montreal Parking Finder.
"""

import argparse
import sys
import os
import time
from datetime import datetime
import pandas as pd
import webbrowser

from montreal_parking_finder.config import (
    DB_URI, PARKING_DATA_FILE, 
    DEFAULT_CENTER_LAT, DEFAULT_CENTER_LON, DEFAULT_RADIUS_KM
)
from montreal_parking_finder.data.loader import load_parking_data, filter_by_distance
from montreal_parking_finder.data.parser import parse_restrictions_parallel
from montreal_parking_finder.db.operations import (
    create_database, store_signs, generate_intervals_parallel,
    get_area_parking_data, create_area_summary
)
from montreal_parking_finder.utils.visualization import create_area_map, save_map, save_area_summary


def create_db_command(args):
    """
    Create the database and tables.
    """
    print(f"Creating database at {DB_URI}")
    create_database()
    print("Database created successfully!")


def import_data_command(args):
    """
    Import parking data from CSV file.
    """
    file_path = args.file or PARKING_DATA_FILE
    
    if not os.path.exists(file_path):
        print(f"Error: File not found: {file_path}")
        return
    
    print(f"Importing data from {file_path}...")
    start_time = time.time()
    
    # Load data
    df = load_parking_data(file_path)
    
    if df.empty:
        print("No data loaded.")
        return
    
    # Parse restrictions
    df = parse_restrictions_parallel(df)
    
    # Store signs in database
    count = store_signs(df)
    
    end_time = time.time()
    print(f"Imported {count} signs in {end_time - start_time:.2f} seconds!")


def process_intervals_command(args):
    """
    Generate intervals for all signs.
    """
    batch_size = args.batch_size
    
    print(f"Processing intervals with batch size {batch_size}...")
    start_time = time.time()
    
    # Generate intervals
    count = generate_intervals_parallel(batch_size=batch_size)
    
    end_time = time.time()
    print(f"Processed {count} intervals in {end_time - start_time:.2f} seconds!")


def analyze_area_command(args):
    """
    Analyze parking for a specific area.
    """
    lat = args.lat
    lon = args.lon
    radius = args.radius
    name = args.name or f"Area_{lat}_{lon}"
    
    print(f"Analyzing parking for {name}...")
    start_time = time.time()
    
    # Get data for area
    signs_df, intervals_df = get_area_parking_data(lat, lon, radius)
    
    if signs_df.empty:
        print("No signs found in this area.")
        return
    
    # Create map
    area_map, summary = create_area_map(
        signs_df, intervals_df, lat, lon, radius, area_name=name
    )
    
    # Save outputs
    map_file = save_map(area_map, name)
    summary_file = save_area_summary(summary)
    
    # Store summary in database
    create_area_summary(
        name, lat, lon, radius,
        summary['total_signs'], summary['total_intervals'],
        summary['free_intervals'], summary['restricted_intervals']
    )
    
    end_time = time.time()
    print(f"Analysis completed in {end_time - start_time:.2f} seconds!")
    
    # Open map in browser if requested
    if args.view:
        print(f"Opening map in browser...")
        webbrowser.open('file://' + os.path.realpath(map_file))


def init_parser():
    """
    Initialize argument parser.
    """
    parser = argparse.ArgumentParser(
        description='Montreal Parking Finder - Find free parking spots in Montreal'
    )
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # createdb command
    createdb_parser = subparsers.add_parser('createdb', help='Create the database')
    
    # import command
    import_parser = subparsers.add_parser('import', help='Import parking data')
    import_parser.add_argument('--file', help='Path to CSV file')
    
    # process command
    process_parser = subparsers.add_parser('process', help='Process parking intervals')
    process_parser.add_argument('--batch-size', type=int, default=100, help='Batch size for processing')
    
    # analyze command
    analyze_parser = subparsers.add_parser('analyze', help='Analyze parking for an area')
    analyze_parser.add_argument('--lat', type=float, default=DEFAULT_CENTER_LAT, help='Center latitude')
    analyze_parser.add_argument('--lon', type=float, default=DEFAULT_CENTER_LON, help='Center longitude')
    analyze_parser.add_argument('--radius', type=float, default=DEFAULT_RADIUS_KM, help='Radius in kilometers')
    analyze_parser.add_argument('--name', help='Name for the area')
    analyze_parser.add_argument('--view', action='store_true', help='Open map in browser')
    
    return parser


def main():
    """
    Main entry point for the command-line interface.
    """
    parser = init_parser()
    args = parser.parse_args()
    
    if args.command == 'createdb':
        create_db_command(args)
    elif args.command == 'import':
        import_data_command(args)
    elif args.command == 'process':
        process_intervals_command(args)
    elif args.command == 'analyze':
        analyze_area_command(args)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()

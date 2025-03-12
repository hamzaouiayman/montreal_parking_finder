#!/usr/bin/env python3
"""
Script to run the Montreal Parking Finder application.
"""

import argparse
import os
import sys

# Add the project directory to the path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))


def main():
    """
    Main entry point.
    """
    parser = argparse.ArgumentParser(
        description='Montreal Parking Finder - Run the application'
    )
    
    parser.add_argument(
        '--mode', choices=['web', 'cli'], default='web',
        help='Application mode: web or cli'
    )
    
    parser.add_argument('--port', type=int, default=5000, help='Port for web server')
    parser.add_argument('--debug', action='store_true', help='Run in debug mode')
    
    args = parser.parse_args()
    
    if args.mode == 'web':
        print(f"Starting web application on port {args.port}...")
        from montreal_parking_finder.web.app import start_app
        start_app(debug=args.debug, port=args.port)
    
    elif args.mode == 'cli':
        print("Running command-line interface...")
        from montreal_parking_finder.cli import main as cli_main
        cli_main()


if __name__ == '__main__':
    main()

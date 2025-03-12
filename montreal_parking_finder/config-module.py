"""
Configuration settings for the Montreal Parking Finder application.
"""

import os
from pathlib import Path

# Base directory
BASE_DIR = Path(__file__).resolve().parent.parent

# Data files
PARKING_DATA_FILE = os.environ.get('MPF_PARKING_DATA', 'signalisation_stationnement.csv')

# Database settings
DB_URI = os.environ.get('MPF_DB_URI', 'sqlite:///' + str(BASE_DIR / 'parking.db'))

# Geo settings
DEFAULT_RADIUS_KM = 0.5
DEFAULT_CENTER_LAT = 45.4767  # Downtown Montreal
DEFAULT_CENTER_LON = -73.6387

# API settings
OVERPASS_API_URL = "https://overpass-api.de/api/interpreter"
OVERPASS_API_DELAY = 0.1  # Seconds delay between API calls

# Processing settings
BATCH_SIZE = 5000  # Number of rows to process in a batch
NUM_PROCESSES = os.cpu_count() or 4  # Number of processes to use

# Output settings
OUTPUT_DIR = "montreal_parking_maps"

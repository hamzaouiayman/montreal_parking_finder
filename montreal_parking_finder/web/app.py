"""
Web application for the Montreal Parking Finder.
"""

from flask import Flask, render_template, request, redirect, url_for, jsonify, send_from_directory
import os
import time
from datetime import datetime
import pandas as pd
import json
import folium
from folium.plugins import MarkerCluster
import threading

from montreal_parking_finder.config import OUTPUT_DIR, DEFAULT_CENTER_LAT, DEFAULT_CENTER_LON, DEFAULT_RADIUS_KM
from montreal_parking_finder.db.operations import get_area_parking_data, create_area_summary
from montreal_parking_finder.utils.visualization import create_area_map, save_map, save_area_summary
from montreal_parking_finder.data.parser import is_parking_allowed
from montreal_parking_finder.api.endpoints import register_api_endpoints

# Create Flask app
app = Flask(__name__)

# Register API endpoints
register_api_endpoints(app)

# Store background tasks
background_tasks = {}
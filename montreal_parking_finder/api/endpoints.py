"""
API endpoints for the Montreal Parking Finder mobile application.
"""

from flask import Blueprint, request, jsonify
from datetime import datetime
import json
import pandas as pd
import time
import uuid

from montreal_parking_finder.config import DEFAULT_CENTER_LAT, DEFAULT_CENTER_LON, DEFAULT_RADIUS_KM
from montreal_parking_finder.db.operations import get_area_parking_data, create_area_summary
from montreal_parking_finder.data.parser import is_parking_allowed

# Create API blueprint
api_blueprint = Blueprint('api', __name__)

# Store active analysis tasks
analysis_tasks = {}


@api_blueprint.route('/version', methods=['GET'])
def api_version():
    """
    Get API version information.
    """
    return jsonify({
        'name': 'Montreal Parking Finder API',
        'version': '1.0.0',
        'timestamp': datetime.now().isoformat()
    })


@api_blueprint.route('/search', methods=['POST'])
def search_parking():
    """
    Search for parking around a location.
    
    Expected JSON body:
    {
        "latitude": 45.5017,
        "longitude": -73.5673,
        "radius": 0.2,
        "timestamp": "2023-03-15T14:30:00" (optional - use specific time)
    }
    """
    try:
        # Get request data
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'Missing request data'
            }), 400
        
        # Extract and validate parameters
        try:
            lat = float(data.get('latitude', DEFAULT_CENTER_LAT))
            lon = float(data.get('longitude', DEFAULT_CENTER_LON))
            radius = float(data.get('radius', 0.2))  # Smaller default radius for search
            
            # Optional timestamp parameter
            timestamp_str = data.get('timestamp')
            if timestamp_str:
                current_time = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            else:
                current_time = datetime.now()
        
        except (ValueError, TypeError) as e:
            return jsonify({
                'success': False,
                'error': f'Invalid parameters: {str(e)}'
            }), 400
        
        # Limit radius for performance
        if radius > 2:
            radius = 2
            
        # Get data for area
        signs_df, intervals_df = get_area_parking_data(lat, lon, radius)
        
        if signs_df.empty:
            return jsonify({
                'success': False,
                'message': 'No parking data found in this area.'
            })
        
        # Process parking availability
        if not intervals_df.empty and not signs_df.empty:
            # Join signs and intervals
            merged_df = pd.merge(
                intervals_df, 
                signs_df,
                left_on='sign_id', 
                right_on='id', 
                suffixes=('_interval', '_sign')
            )
            
            # Calculate availability
            results = []
            for _, row in merged_df.iterrows():
                is_allowed = is_parking_allowed(row['parsed_restriction'], current_time)
                
                results.append({
                    'street_name': row['street_name'],
                    'latitude': row['latitude'],
                    'longitude': row['longitude'],
                    'is_allowed': is_allowed,
                    'description': row['description'],
                    'start_lat': row['start_lat'],
                    'start_lon': row['start_lon'],
                    'end_lat': row['end_lat'],
                    'end_lon': row['end_lon']
                })
            
            return jsonify({
                'success': True,
                'count': len(results),
                'results': results,
                'timestamp': current_time.isoformat(),
                'center': {
                    'latitude': lat,
                    'longitude': lon,
                    'radius': radius
                }
            })
        
        return jsonify({
            'success': False,
            'message': 'No parking intervals found in this area.'
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Server error: {str(e)}'
        }), 500


@api_blueprint.route('/analyze', methods=['POST'])
def start_analysis():
    """
    Start an analysis of an area.
    
    Expected JSON body:
    {
        "latitude": 45.5017,
        "longitude": -73.5673,
        "radius": 0.5,
        "name": "Downtown"
    }
    
    Returns a task ID that can be used to check the status.
    """
    try:
        # Get request data
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'Missing request data'
            }), 400
        
        # Extract and validate parameters
        try:
            lat = float(data.get('latitude', DEFAULT_CENTER_LAT))
            lon = float(data.get('longitude', DEFAULT_CENTER_LON))
            radius = float(data.get('radius', DEFAULT_RADIUS_KM))
            name = data.get('name', f"Area_{lat}_{lon}")
        
        except (ValueError, TypeError) as e:
            return jsonify({
                'success': False,
                'error': f'Invalid parameters: {str(e)}'
            }), 400
        
        # Create task ID
        task_id = str(uuid.uuid4())
        
        # Initialize task
        analysis_tasks[task_id] = {
            'id': task_id,
            'name': name,
            'latitude': lat,
            'longitude': lon,
            'radius': radius,
            'status': 'pending',
            'progress': 0,
            'created_at': datetime.now().isoformat(),
            'results': None
        }
        
        # Start analysis in the background
        # In a real implementation, this would use a task queue like Celery
        # For simplicity, we'll simulate background processing
        def background_analysis():
            try:
                # Update task status
                analysis_tasks[task_id]['status'] = 'running'
                analysis_tasks[task_id]['progress'] = 10
                
                # Get data for area
                signs_df, intervals_df = get_area_parking_data(lat, lon, radius)
                analysis_tasks[task_id]['progress'] = 50
                
                if signs_df.empty:
                    analysis_tasks[task_id]['status'] = 'failed'
                    analysis_tasks[task_id]['message'] = 'No signs found in this area.'
                    return
                
                # Calculate statistics
                free_intervals = 0
                restricted_intervals = 0
                
                # Current time for availability check
                current_time = datetime.now()
                
                # Process intervals
                processed_intervals = []
                
                if not intervals_df.empty:
                    # Join signs and intervals
                    merged_df = pd.merge(
                        intervals_df, 
                        signs_df,
                        left_on='sign_id', 
                        right_on='id', 
                        suffixes=('_interval', '_sign')
                    )
                    
                    for _, row in merged_df.iterrows():
                        # Determine parking status
                        is_available = is_parking_allowed(row['parsed_restriction'], current_time)
                        
                        # Update counts
                        if is_available:
                            free_intervals += 1
                        else:
                            restricted_intervals += 1
                        
                        # Add to processed intervals
                        processed_intervals.append({
                            'street_name': row['street_name'],
                            'is_available': is_available,
                            'description': row['description'],
                            'coordinates': [
                                [row['start_lat'], row['start_lon']],
                                [row['end_lat'], row['end_lon']]
                            ]
                        })
                
                analysis_tasks[task_id]['progress'] = 80
                
                # Create summary
                summary = {
                    'name': name,
                    'center_lat': lat,
                    'center_lon': lon,
                    'radius_km': radius,
                    'total_signs': len(signs_df),
                    'total_intervals': free_intervals + restricted_intervals,
                    'free_intervals': free_intervals,
                    'restricted_intervals': restricted_intervals,
                    'timestamp': current_time.isoformat()
                }
                
                # Store summary in database
                create_area_summary(
                    name, lat, lon, radius,
                    len(signs_df), free_intervals + restricted_intervals,
                    free_intervals, restricted_intervals
                )
                
                # Update task with results
                analysis_tasks[task_id]['status'] = 'completed'
                analysis_tasks[task_id]['progress'] = 100
                analysis_tasks[task_id]['results'] = {
                    'summary': summary,
                    'intervals': processed_intervals
                }
                analysis_tasks[task_id]['completed_at'] = datetime.now().isoformat()
            
            except Exception as e:
                analysis_tasks[task_id]['status'] = 'failed'
                analysis_tasks[task_id]['message'] = f'Error: {str(e)}'
        
        # Start background thread for analysis
        import threading
        thread = threading.Thread(target=background_analysis)
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'success': True,
            'task_id': task_id,
            'message': 'Analysis started'
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Server error: {str(e)}'
        }), 500


@api_blueprint.route('/task/<task_id>', methods=['GET'])
def get_task_status(task_id):
    """
    Get the status of an analysis task.
    """
    if task_id in analysis_tasks:
        # For completed tasks, include summary but limit intervals to reduce payload size
        task = analysis_tasks[task_id].copy()
        
        if task['status'] == 'completed' and task['results'] and 'intervals' in task['results']:
            # Limit to first 100 intervals
            task['results']['intervals'] = task['results']['intervals'][:100]
            task['results']['intervals_truncated'] = len(analysis_tasks[task_id]['results']['intervals']) > 100
            
        return jsonify({
            'success': True,
            'task': task
        })
    else:
        return jsonify({
            'success': False,
            'error': 'Task not found'
        }), 404


@api_blueprint.route('/task/<task_id>/intervals', methods=['GET'])
def get_task_intervals(task_id):
    """
    Get all intervals for a completed task, with pagination.
    """
    if task_id not in analysis_tasks:
        return jsonify({
            'success': False,
            'error': 'Task not found'
        }), 404
    
    task = analysis_tasks[task_id]
    
    if task['status'] != 'completed' or not task['results'] or 'intervals' not in task['results']:
        return jsonify({
            'success': False,
            'error': 'Task results not available'
        }), 400
    
    # Get pagination parameters
    page = int(request.args.get('page', 1))
    page_size = int(request.args.get('page_size', 100))
    
    # Validate pagination
    if page < 1:
        page = 1
    if page_size < 1 or page_size > 1000:
        page_size = 100
    
    # Get intervals with pagination
    all_intervals = task['results']['intervals']
    total_intervals = len(all_intervals)
    
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    
    paginated_intervals = all_intervals[start_idx:end_idx]
    
    return jsonify({
        'success': True,
        'task_id': task_id,
        'page': page,
        'page_size': page_size,
        'total_intervals': total_intervals,
        'total_pages': (total_intervals + page_size - 1) // page_size,
        'intervals': paginated_intervals
    })


def register_api_endpoints(app):
    """
    Register API endpoints with the Flask application.
    """
    app.register_blueprint(api_blueprint, url_prefix='/api')

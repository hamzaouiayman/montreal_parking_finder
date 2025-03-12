"""
Module for parsing parking restriction descriptions.
"""

import re
import pandas as pd
import time
from datetime import datetime, time as dt_time
from multiprocessing import Pool

from montreal_parking_finder.config import BATCH_SIZE, NUM_PROCESSES


def parse_restriction(desc):
    """
    Parse the parking restriction description.
    
    Args:
        desc: Description of the parking restriction
        
    Returns:
        Dictionary containing parsed restriction details
    """
    result = {
        'type': None,           # P (parking), A (arrêt/stopping), $ (paid)
        'is_restricted': False, # True if parking/stopping is restricted
        'time_ranges': [],      # List of time ranges when restriction applies
        'days': [],             # List of days when restriction applies  
        'date_ranges': [],      # List of date ranges when restriction applies
        'special': None,        # Special conditions (e.g., RESERVE TAXIS)
        'all_time': False,      # Whether restriction applies all the time
        'raw_description': desc # Original description
    }
    
    # Skip empty descriptions
    if not desc or pd.isna(desc):
        return result
    
    # Determine restriction type
    if desc.startswith('\\P'):
        result['type'] = 'P'  # Parking restriction
        result['is_restricted'] = True
    elif desc.startswith('\\A'):
        result['type'] = 'A'  # No stopping/arrêt
        result['is_restricted'] = True
    elif 'PARCOMETRE' in desc or re.search(r'P\s+(\d+)\s+min', desc) or re.search(r'P\s+(\d+)h', desc):
        result['type'] = '$'  # Paid parking
        result['is_restricted'] = False  # Not restricted, but paid
    
    # Check for all-time restrictions
    if 'EN TOUT TEMPS' in desc:
        result['all_time'] = True
    
    # Extract time ranges (e.g., 09h30-10h30)
    time_pattern = re.compile(r'(\d{1,2}h\d{0,2})-(\d{1,2}h\d{0,2})')
    time_matches = time_pattern.findall(desc)
    for start, end in time_matches:
        result['time_ranges'].append((start.replace('24','00'), end.replace('24','00')))
    
    # Extract days - more comprehensive approach
    # Map French day names and abbreviations to English
    day_mapping = {
        'LUN': 'Monday', 'LUNDI': 'Monday',
        'MAR': 'Tuesday', 'MARDI': 'Tuesday',
        'MER': 'Wednesday', 'MERCREDI': 'Wednesday',
        'JEU': 'Thursday', 'JEUDI': 'Thursday',
        'VEN': 'Friday', 'VENDREDI': 'Friday',
        'SAM': 'Saturday', 'SAMEDI': 'Saturday',
        'DIM': 'Sunday', 'DIMANCHE': 'Sunday'
    }
    
    # Check for individual days
    for fr_day, en_day in day_mapping.items():
        if re.search(r'\b' + fr_day + r'\.?(?!\w)', desc):
            if en_day not in result['days']:
                result['days'].append(en_day)
    
    # Handle day ranges with various connectors
    if re.search(r'LUN\.?\s+(AU|A|ET)\s+VEN\.?', desc) or 'LUN A VEN' in desc:
        result['days'] = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
    elif re.search(r'LUN\.?\s+(AU|A|ET)\s+SAM\.?', desc) or 'LUN A SAM' in desc:
        result['days'] = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
    elif re.search(r'LUN\.?\s+(AU|A|ET)\s+DIM\.?', desc) or 'LUN A DIM' in desc:
        result['days'] = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    
    # Extract date ranges (e.g., 1 MARS AU 1 DEC)
    # Mapping French month names to numbers
    month_mapping = {
        'JANVIER': 1, 'JAN': 1, 'FEVRIER': 2, 'FEV': 2, 'MARS': 3, 'MAR': 3,
        'AVRIL': 4, 'AVR': 4, 'MAI': 5, 'JUIN': 6, 'JUILLET': 7, 'JUIL': 7,
        'AOUT': 8, 'SEPTEMBRE': 9, 'SEPT': 9, 'OCTOBRE': 10, 'OCT': 10,
        'NOVEMBRE': 11, 'NOV': 11, 'DECEMBRE': 12, 'DEC': 12
    }
    
    # Pattern to find date ranges
    date_pattern = re.compile(r'(\d{1,2})(?:ER|er|)?\s+(JANVIER|JAN|FEVRIER|FEV|MARS|AVRIL|AVR|MAI|JUIN|JUILLET|JUIL|AOUT|SEPTEMBRE|SEPT|OCTOBRE|OCT|NOVEMBRE|NOV|DECEMBRE|DEC)\.?\s+(AU|A|ET)\s+(\d{1,2})(?:ER|er|)?\s+(JANVIER|JAN|FEVRIER|FEV|MARS|AVRIL|AVR|MAI|JUIN|JUILLET|JUIL|AOUT|SEPTEMBRE|SEPT|OCTOBRE|OCT|NOVEMBRE|NOV|DECEMBRE|DEC)', re.IGNORECASE)
    
    date_matches = date_pattern.findall(desc)
    if date_matches:
        for match in date_matches:
            start_day, start_month_name, connector, end_day, end_month_name = match
            start_month = 0
            end_month = 0
            
            # Find the correct month number for start and end months
            for month_name, month_num in month_mapping.items():
                if month_name.lower() in start_month_name.lower():
                    start_month = month_num
                if month_name.lower() in end_month_name.lower():
                    end_month = month_num
            
            if start_month > 0 and end_month > 0:
                result['date_ranges'].append({
                    'start_day': int(start_day), 
                    'start_month': start_month, 
                    'end_day': int(end_day), 
                    'end_month': end_month
                })
    
    # Check for special conditions
    special_conditions = [
        'RESERVE', 'HANDICAP', 'TAXI', 'LIVRAISON', 'AUTOBUS', 
        'DEBARCADERE', 'S3R', 'MOTOS', 'CORPS DIPLOMATIQUES', 'SERVICE D\'INCENDIE',
        'VEHICULES DE LA VILLE', 'VEHICULES MILITAIRES'
    ]
    
    for condition in special_conditions:
        if condition in desc:
            result['special'] = condition
            break
    
    return result


def parse_batch_restrictions(batch_df):
    """
    Parse restrictions for a batch of signs.
    
    Args:
        batch_df: DataFrame batch containing signs to process
        
    Returns:
        DataFrame with parsed restrictions
    """
    batch_df['parsed_restriction'] = batch_df['DESCRIPTION_RPA'].apply(parse_restriction)
    
    # Add simplified classifications
    batch_df['is_restricted'] = batch_df['parsed_restriction'].apply(lambda x: x['is_restricted'])
    batch_df['is_all_time'] = batch_df['parsed_restriction'].apply(lambda x: x['all_time'])
    batch_df['is_paid'] = batch_df['parsed_restriction'].apply(lambda x: x['type'] == '$')
    
    # Interpret the FLECHE_PAN values
    batch_df['arrow_direction'] = batch_df['FLECHE_PAN'].map({
        0: 'both_sides',  # No arrow or applies to both sides
        1: 'up',          # Arrow pointing up
        2: 'left',        # Arrow pointing left
        3: 'right'        # Arrow pointing right
    }).fillna('both_sides')
    
    return batch_df


def parse_restrictions_parallel(df):
    """
    Parse parking restrictions for all signs in parallel.
    
    Args:
        df: DataFrame containing parking data
        
    Returns:
        DataFrame with parsed restrictions
    """
    print("Parsing parking restrictions in parallel...")
    start_time = time.time()
    
    # Split the dataframe into batches
    batch_size = min(BATCH_SIZE, max(1000, len(df) // (NUM_PROCESSES * 2)))
    df_batches = [df[i:i+batch_size] for i in range(0, len(df), batch_size)]
    
    print(f"Processing {len(df_batches)} batches with {NUM_PROCESSES} processes...")
    
    # Process batches in parallel
    with Pool(processes=NUM_PROCESSES) as pool:
        processed_batches = pool.map(parse_batch_restrictions, df_batches)
    
    # Combine results
    df_parsed = pd.concat(processed_batches)
    
    end_time = time.time()
    print(f"Parsed parking restrictions for {len(df_parsed)} signs in {end_time - start_time:.2f} seconds.")
    
    return df_parsed


def is_parking_allowed(parsed_restriction, current_datetime=None):
    """
    Determine if parking is allowed based on parsed restriction and time.
    
    Args:
        parsed_restriction: Dictionary containing parsed restriction details
        current_datetime: Datetime to check against (default: now)
        
    Returns:
        Boolean indicating if parking is allowed
    """
    if current_datetime is None:
        current_datetime = datetime.now()
    
    # Get current day, time, and date
    current_day = current_datetime.strftime('%A')  # Monday, Tuesday, etc.
    current_time = current_datetime.time()
    current_month = current_datetime.month
    current_day_of_month = current_datetime.day
    
    # If it's restricted at all times, parking is not allowed
    if parsed_restriction['all_time']:
        return False
    
    # Check if the current day is in restricted days
    day_match = len(parsed_restriction['days']) == 0 or current_day in parsed_restriction['days']
    
    # Check if current time is in restricted time ranges
    time_match = True
    if parsed_restriction['time_ranges']:
        time_match = False
        for start_time_str, end_time_str in parsed_restriction['time_ranges']:
            # Parse time strings (e.g., "09h30" -> 9:30)
            start_hours = int(start_time_str.split('h')[0])
            start_minutes = 0
            if 'h' in start_time_str and len(start_time_str.split('h')[1]) > 0:
                start_minutes = int(start_time_str.split('h')[1])
            
            end_hours = int(end_time_str.split('h')[0])
            end_minutes = 0
            if 'h' in end_time_str and len(end_time_str.split('h')[1]) > 0:
                end_minutes = int(end_time_str.split('h')[1])
            
            start_time = dt_time(start_hours, start_minutes)
            end_time = dt_time(end_hours, end_minutes)
            
            if start_time <= current_time <= end_time:
                time_match = True
                break
    
    # Check if current date is in restricted date ranges
    date_match = True
    if parsed_restriction['date_ranges']:
        date_match = False
        for date_range in parsed_restriction['date_ranges']:
            start_day = date_range['start_day']
            start_month = date_range['start_month']
            end_day = date_range['end_day']
            end_month = date_range['end_month']
            
            # Handle crossing year boundary (e.g., NOV to MAR)
            if start_month > end_month:
                # Current date is between start and end of year
                if (current_month > start_month or 
                    (current_month == start_month and current_day_of_month >= start_day)) or \
                   (current_month < end_month or 
                    (current_month == end_month and current_day_of_month <= end_day)):
                    date_match = True
                    break
            else:
                # Standard date range within a year
                if ((current_month > start_month or 
                     (current_month == start_month and current_day_of_month >= start_day)) and
                    (current_month < end_month or 
                     (current_month == end_month and current_day_of_month <= end_day))):
                    date_match = True
                    break
    
    # Parking is not allowed if all conditions match the restriction
    restriction_applies = day_match and time_match and date_match
    
    # Return the opposite of restriction_applies for is_parking_allowed
    # (if the restriction applies, parking is not allowed)
    return not (restriction_applies and parsed_restriction['is_restricted'])

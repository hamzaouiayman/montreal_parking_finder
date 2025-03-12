# Montreal Parking Finder

An application to help users find free parking spots in Montreal.

## Features
- Analyzes Montreal parking signalization data
- Displays free parking spots on an interactive map
- Considers time-based parking restrictions

## Project Structure
- `montreal_parking_finder/` - Main package
  - `data/` - Data handling modules
  - `db/` - Database models and operations
  - `geo/` - Geographic utilities
  - `api/` - API for the web and mobile app
  - `web/` - Web application
  - `utils/` - Utility functions

## Installation
```bash
pip install -r requirements.txt
```

## Usage
```bash
# Create the database
python -m montreal_parking_finder.cli createdb

# Import parking data
python -m montreal_parking_finder.cli import --file signalisation_stationnement.csv

# Analyze an area
python -m montreal_parking_finder.cli analyze --lat 45.4767 --lon -73.6387 --radius 0.5
```

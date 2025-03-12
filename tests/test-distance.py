"""
Tests for distance calculation functions.
"""

import unittest
from montreal_parking_finder.geo.distance import haversine_distance, filter_coordinates_by_distance


class TestDistance(unittest.TestCase):
    """
    Test the distance calculation functions.
    """
    
    def test_haversine_distance_same_point(self):
        """
        Test distance between the same point is zero.
        """
        lat, lon = 45.5017, -73.5673  # Montreal
        distance = haversine_distance(lat, lon, lat, lon)
        self.assertAlmostEqual(distance, 0, places=10)
    
    def test_haversine_distance_known_points(self):
        """
        Test distance between known points.
        """
        # Montreal to Quebec City (approximately 233 km)
        montreal_lat, montreal_lon = 45.5017, -73.5673
        quebec_lat, quebec_lon = 46.8139, -71.2080
        
        distance = haversine_distance(montreal_lat, montreal_lon, quebec_lat, quebec_lon)
        
        # Allow for some error in the calculation
        self.assertGreater(distance, 230)
        self.assertLess(distance, 240)
    
    def test_filter_coordinates_empty(self):
        """
        Test filtering empty coordinates.
        """
        result = filter_coordinates_by_distance([], 45.5017, -73.5673, 1.0)
        self.assertEqual(result, [])
    
    def test_filter_coordinates(self):
        """
        Test filtering coordinates by distance.
        """
        center_lat, center_lon = 45.5017, -73.5673
        radius_km = 1.0
        
        # Create test coordinates
        coordinates = [
            (45.5017, -73.5673),  # Same as center (0 km)
            (45.5117, -73.5773),  # Close to center (< 1 km)
            (45.6017, -73.6673)   # Far from center (> 1 km)
        ]
        
        result = filter_coordinates_by_distance(coordinates, center_lat, center_lon, radius_km)
        
        # Should include only the first two coordinates
        self.assertEqual(len(result), 2)
        self.assertIn((45.5017, -73.5673), result)
        self.assertIn((45.5117, -73.5773), result)
        self.assertNotIn((45.6017, -73.6673), result)


if __name__ == '__main__':
    unittest.main()

"""
Tests for configuration module.
"""

import unittest
import os
from montreal_parking_finder import config


class TestConfig(unittest.TestCase):
    """
    Test the configuration module.
    """
    
    def test_base_dir(self):
        """
        Test that BASE_DIR is a valid directory.
        """
        self.assertTrue(os.path.exists(config.BASE_DIR))
        self.assertTrue(os.path.isdir(config.BASE_DIR))
    
    def test_default_coordinates(self):
        """
        Test that default coordinates are valid.
        """
        # Default center should be in Montreal
        self.assertAlmostEqual(config.DEFAULT_CENTER_LAT, 45.4767, places=4)
        self.assertAlmostEqual(config.DEFAULT_CENTER_LON, -73.6387, places=4)
    
    def test_default_radius(self):
        """
        Test that default radius is valid.
        """
        self.assertGreater(config.DEFAULT_RADIUS_KM, 0)
        self.assertLessEqual(config.DEFAULT_RADIUS_KM, 5)  # Reasonable upper limit
    
    def test_processing_settings(self):
        """
        Test processing settings.
        """
        self.assertGreater(config.BATCH_SIZE, 0)
        self.assertGreater(config.NUM_PROCESSES, 0)
    
    def test_api_settings(self):
        """
        Test API settings.
        """
        self.assertTrue(config.OVERPASS_API_URL.startswith('http'))
        self.assertGreater(config.OVERPASS_API_DELAY, 0)


if __name__ == '__main__':
    unittest.main()

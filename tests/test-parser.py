"""
Tests for parking restriction parser.
"""

import unittest
from datetime import datetime
from montreal_parking_finder.data.parser import parse_restriction, is_parking_allowed


class TestParser(unittest.TestCase):
    """
    Test the parking restriction parser.
    """
    
    def test_parse_no_parking(self):
        """
        Test parsing a no parking restriction.
        """
        desc = r"\P LUN AU VEN 9h00-10h00"
        result = parse_restriction(desc)
        
        self.assertEqual(result['type'], 'P')
        self.assertTrue(result['is_restricted'])
        self.assertEqual(len(result['time_ranges']), 1)
        self.assertEqual(result['time_ranges'][0], ('9h00', '10h00'))
        self.assertEqual(result['days'], ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'])
        self.assertFalse(result['all_time'])
    
    def test_parse_no_stopping(self):
        """
        Test parsing a no stopping restriction.
        """
        desc = r"\A EN TOUT TEMPS"
        result = parse_restriction(desc)
        
        self.assertEqual(result['type'], 'A')
        self.assertTrue(result['is_restricted'])
        self.assertTrue(result['all_time'])
        self.assertEqual(len(result['days']), 0)
        self.assertEqual(len(result['time_ranges']), 0)
    
    def test_parse_paid_parking(self):
        """
        Test parsing a paid parking restriction.
        """
        desc = "PARCOMETRE 9h-21h LUN A SAM"
        result = parse_restriction(desc)
        
        self.assertEqual(result['type'], '$')
        self.assertFalse(result['is_restricted'])  # Paid parking is not restricted, just paid
        self.assertEqual(len(result['time_ranges']), 1)
        self.assertEqual(result['time_ranges'][0], ('9h', '21h'))
        self.assertEqual(len(result['days']), 6)  # Monday through Saturday
    
    def test_parse_date_range(self):
        """
        Test parsing a date range restriction.
        """
        desc = r"\P 1 AVRIL AU 1 NOV LUN AU VEN 9h00-18h00"
        result = parse_restriction(desc)
        
        self.assertEqual(result['type'], 'P')
        self.assertTrue(result['is_restricted'])
        self.assertEqual(len(result['date_ranges']), 1)
        self.assertEqual(result['date_ranges'][0]['start_day'], 1)
        self.assertEqual(result['date_ranges'][0]['start_month'], 4)  # April
        self.assertEqual(result['date_ranges'][0]['end_day'], 1)
        self.assertEqual(result['date_ranges'][0]['end_month'], 11)  # November
    
    def test_is_parking_allowed(self):
        """
        Test determining if parking is allowed.
        """
        # Create a restriction: No parking Monday to Friday, 9am-6pm
        restriction = parse_restriction(r"\P LUN AU VEN 9h00-18h00")
        
        # Tuesday at 12pm (restricted)
        tuesday_noon = datetime(2023, 10, 10, 12, 0)  # A Tuesday
        self.assertFalse(is_parking_allowed(restriction, tuesday_noon))
        
        # Tuesday at 8am (allowed)
        tuesday_morning = datetime(2023, 10, 10, 8, 0)  # A Tuesday
        self.assertTrue(is_parking_allowed(restriction, tuesday_morning))
        
        # Saturday at 12pm (allowed)
        saturday_noon = datetime(2023, 10, 14, 12, 0)  # A Saturday
        self.assertTrue(is_parking_allowed(restriction, saturday_noon))
    
    def test_is_parking_allowed_all_time(self):
        """
        Test all-time restriction.
        """
        # Create a restriction: No stopping at any time
        restriction = parse_restriction(r"\A EN TOUT TEMPS")
        
        # Any time should be restricted
        self.assertFalse(is_parking_allowed(restriction, datetime(2023, 10, 10, 12, 0)))
        self.assertFalse(is_parking_allowed(restriction, datetime(2023, 10, 14, 2, 0)))
    
    def test_is_parking_allowed_date_range(self):
        """
        Test date range restriction.
        """
        # Create a restriction: No parking April to November, Monday to Friday, 9am-6pm
        restriction = parse_restriction(r"\P 1 AVRIL AU 1 NOV LUN AU VEN 9h00-18h00")
        
        # October Tuesday at 12pm (restricted)
        oct_tuesday = datetime(2023, 10, 10, 12, 0)
        self.assertFalse(is_parking_allowed(restriction, oct_tuesday))
        
        # January Tuesday at 12pm (allowed, outside date range)
        jan_tuesday = datetime(2023, 1, 10, 12, 0)
        self.assertTrue(is_parking_allowed(restriction, jan_tuesday))


if __name__ == '__main__':
    unittest.main()

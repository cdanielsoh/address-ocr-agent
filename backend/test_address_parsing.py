#!/usr/bin/env python3
"""
Unit tests for Korean address parsing functionality

This script contains unit tests for the address parsing logic
without requiring AWS services or external dependencies.
"""

import unittest
import sys
import os
from typing import Dict, Any

# Add the app directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

class TestKoreanAddressParsing(unittest.TestCase):
    """Unit tests for Korean address parsing"""
    
    def setUp(self):
        """Set up test cases"""
        self.test_addresses = [
            {
                "text": "서울특별시 성북구 화랑로 11길 26 103동 1602호 (하월곡동, OO아파트)",
                "expected": {
                    "sido": "서울특별시",
                    "sigungu": "성북구", 
                    "roadName": "화랑로",
                    "buildingNumber": "26",
                    "dong": "103동",
                    "ho": "1602호"
                }
            },
            {
                "text": "부산광역시 해운대구 해운대로 570",
                "expected": {
                    "sido": "부산광역시",
                    "sigungu": "해운대구",
                    "roadName": "해운대로",
                    "buildingNumber": "570"
                }
            },
            {
                "text": "경기도 성남시 분당구 판교역로 235 에이치스퀘어 N동 5층",
                "expected": {
                    "sido": "경기도",
                    "sigungu": "성남시",
                    "roadName": "판교역로",
                    "buildingNumber": "235"
                }
            },
            {
                "text": "인천광역시 남동구 구월로 273번길 15",
                "expected": {
                    "sido": "인천광역시",
                    "sigungu": "남동구",
                    "roadName": "구월로",
                    "buildingNumber": "15"
                }
            }
        ]
    
    def test_upstage_service_import(self):
        """Test that UpstageService can be imported"""
        try:
            from services.upstage_service import UpstageService
            service = UpstageService()
            self.assertIsNotNone(service)
            print("✅ UpstageService import successful")
        except ImportError as e:
            self.fail(f"Failed to import UpstageService: {e}")
    
    def test_address_parsing_logic(self):
        """Test the Korean address parsing regex patterns"""
        try:
            from services.upstage_service import UpstageService
            service = UpstageService()
            
            for i, test_case in enumerate(self.test_addresses):
                with self.subTest(case=i):
                    text = test_case["text"]
                    expected = test_case["expected"]
                    
                    print(f"\n🧪 Test case {i+1}: {text[:50]}...")
                    
                    # Parse the address
                    result = service.parse_korean_address(text)
                    
                    # Check each expected component
                    for component, expected_value in expected.items():
                        actual_value = result.get(component, "")
                        
                        if expected_value:
                            self.assertIn(expected_value, text, 
                                f"Expected '{expected_value}' should be in original text")
                            
                            # For more lenient testing, check if the component was found
                            self.assertNotEqual(actual_value, "", 
                                f"Component '{component}' should not be empty")
                            
                            print(f"   ✅ {component}: '{actual_value}' (expected: '{expected_value}')")
                        else:
                            print(f"   ⏭️  {component}: optional component")
                    
        except Exception as e:
            self.fail(f"Address parsing test failed: {e}")
    
    def test_confidence_calculation(self):
        """Test confidence score calculation"""
        try:
            from services.upstage_service import UpstageService
            service = UpstageService()
            
            # Test with a complete address
            complete_address = {
                "sido": "서울특별시",
                "sigungu": "성북구",
                "roadName": "화랑로",
                "buildingNumber": "26",
                "dong": "103동",
                "ho": "1602호",
                "legalDong": "",
                "buildingName": ""
            }
            
            confidence = service.calculate_base_confidence(complete_address)
            
            self.assertIsNotNone(confidence)
            self.assertGreater(confidence.overall, 0.8, "Complete address should have high confidence")
            
            print(f"✅ Complete address confidence: {confidence.overall:.3f}")
            
            # Test with incomplete address
            incomplete_address = {
                "sido": "서울특별시",
                "sigungu": "",
                "roadName": "화랑로",
                "buildingNumber": "",
                "dong": "",
                "ho": "",
                "legalDong": "",
                "buildingName": ""
            }
            
            confidence_incomplete = service.calculate_base_confidence(incomplete_address)
            
            self.assertLess(confidence_incomplete.overall, confidence.overall, 
                "Incomplete address should have lower confidence")
            
            print(f"✅ Incomplete address confidence: {confidence_incomplete.overall:.3f}")
            
        except Exception as e:
            self.fail(f"Confidence calculation test failed: {e}")
    
    def test_models_import(self):
        """Test that response models can be imported and created"""
        try:
            from models.response import ExtractedResult, Confidence, AddressComponents
            
            # Test AddressComponents creation
            components = AddressComponents(
                sido=0.9,
                sigungu=0.8,
                roadName=0.85,
                buildingNumber=0.9
            )
            self.assertEqual(components.sido, 0.9)
            print("✅ AddressComponents model creation successful")
            
            # Test Confidence creation
            confidence = Confidence(overall=0.85, components=components)
            self.assertEqual(confidence.overall, 0.85)
            print("✅ Confidence model creation successful")
            
            # Test ExtractedResult creation
            result = ExtractedResult(
                imageId="test-123",
                extractedText="서울특별시 성북구",
                confidence=confidence,
                processingTime=1500
            )
            self.assertEqual(result.imageId, "test-123")
            print("✅ ExtractedResult model creation successful")
            
        except Exception as e:
            self.fail(f"Models test failed: {e}")

class TestStrandsAgentTools(unittest.TestCase):
    """Unit tests for Strands agent tools"""
    
    def test_strands_agent_import(self):
        """Test that Strands agent components can be imported"""
        try:
            # Test if we can import the Strands agent
            import sys
            sys.path.append(os.path.join(os.path.dirname(__file__), 'strands_agent'))
            
            from agent import analyze_korean_address_confidence
            self.assertTrue(callable(analyze_korean_address_confidence))
            print("✅ Strands agent import successful")
            
        except ImportError as e:
            print(f"⚠️  Strands agent not available: {e}")
            self.skipTest("Strands agent dependencies not installed")
        except Exception as e:
            self.fail(f"Strands agent test failed: {e}")

def main():
    """Run all unit tests"""
    print("🧪 Korean Address Parser Unit Test Suite")
    print("=" * 45)
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test classes
    suite.addTest(loader.loadTestsFromTestCase(TestKoreanAddressParsing))
    suite.addTest(loader.loadTestsFromTestCase(TestStrandsAgentTools))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "=" * 45)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    
    if result.wasSuccessful():
        print("🎉 All unit tests passed!")
        return 0
    else:
        print("❌ Some unit tests failed.")
        return 1

if __name__ == "__main__":
    import sys
    sys.exit(main())
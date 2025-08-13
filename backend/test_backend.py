#!/usr/bin/env python3
"""
Test script for Korean Address Extractor Backend API

This script tests the FastAPI backend endpoints using the sample.jpeg file.
It can be run with or without the actual AWS services (mock mode).

Usage:
    python test_backend.py                    # Test with mock services
    python test_backend.py --real-services   # Test with real AWS services
    python test_backend.py --help            # Show help
"""

import asyncio
import argparse
import sys
import os
import time
import json
from pathlib import Path
from typing import Dict, Any

# Add the app directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

# Test configuration
TEST_IMAGE_PATH = "../sample.jpeg"
BASE_URL = "http://localhost:3001"
MOCK_MODE = True

class BackendTester:
    def __init__(self, use_real_services: bool = False):
        self.use_real_services = use_real_services
        self.test_results = []
        
    def log_test(self, test_name: str, success: bool, message: str, data: Dict[Any, Any] = None):
        """Log test results"""
        result = {
            "test": test_name,
            "success": success,
            "message": message,
            "timestamp": time.time()
        }
        if data:
            result["data"] = data
        
        self.test_results.append(result)
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status}: {test_name} - {message}")
        if data:
            print(f"    Data: {json.dumps(data, indent=2)[:200]}...")
    
    def test_image_file_exists(self) -> bool:
        """Test that the sample image file exists"""
        try:
            image_path = Path(__file__).parent / TEST_IMAGE_PATH
            exists = image_path.exists()
            
            if exists:
                size = image_path.stat().st_size
                self.log_test(
                    "Image File Check",
                    True,
                    f"Sample image found at {image_path} ({size} bytes)",
                    {"path": str(image_path), "size": size}
                )
                return True
            else:
                self.log_test(
                    "Image File Check",
                    False,
                    f"Sample image not found at {image_path}"
                )
                return False
                
        except Exception as e:
            self.log_test("Image File Check", False, f"Error checking image file: {e}")
            return False
    
    
    def test_strands_service(self) -> bool:
        """Test Strands service directly"""
        try:
            from services.strands_service import StrandsService
            from models.response import Confidence, AddressComponents
            
            # Create mock confidence data
            mock_components = AddressComponents(
                sido=0.9,
                sigungu=0.8,
                roadName=0.85,
                buildingNumber=0.9,
                dong=0.8,
                ho=0.75
            )
            mock_confidence = Confidence(overall=0.85, components=mock_components)
            
            service = StrandsService()
            
            # Set environment for test
            original_env = os.environ.get('USE_STRANDS_AGENT')
            os.environ['USE_STRANDS_AGENT'] = 'true' if self.use_real_services else 'false'
            
            try:
                # Test confidence analysis
                enhanced_confidence = asyncio.run(
                    service.analyze_confidence(
                        "서울특별시 성북구 화랑로 11길 26",
                        mock_confidence
                    )
                )
                
                self.log_test(
                    f"Strands Service ({'Real' if self.use_real_services else 'Mock'})",
                    True,
                    f"Confidence analysis completed (overall: {enhanced_confidence.overall:.3f})",
                    {
                        "overall_confidence": enhanced_confidence.overall,
                        "component_count": len([c for c in enhanced_confidence.components.model_dump().values() if c is not None])
                    }
                )
                return True
                
            finally:
                # Restore environment
                if original_env is not None:
                    os.environ['USE_STRANDS_AGENT'] = original_env
                else:
                    os.environ.pop('USE_STRANDS_AGENT', None)
                    
        except Exception as e:
            self.log_test("Strands Service", False, f"Error: {e}")
            return False
    
    def test_upstage_service(self) -> bool:
        """Test Upstage service directly"""
        try:
            from services.upstage_service import UpstageService
            
            # Read test image
            image_path = Path(__file__).parent / TEST_IMAGE_PATH
            if not image_path.exists():
                self.log_test("Upstage Service", False, f"Sample image not found at {image_path}")
                return False
            
            try:
                service = UpstageService()
                
                # Test OCR processing
                result = service.process_image_with_upstage(str(image_path))
                
                extracted_text = result["extracted_text"]
                metadata = result["upstage_metadata"]
                
                self.log_test(
                    "Upstage Service",
                    True,
                    f"Upstage OCR successful (confidence: {metadata.get('overall_confidence', 0):.3f})",
                    {
                        "extracted_text": extracted_text[:50] + "..." if len(extracted_text) > 50 else extracted_text,
                        "text_length": result["text_length"],
                        "endpoint": result["endpoint_name"],
                        "api_version": metadata.get("api_version"),
                        "model_version": metadata.get("model_version"),
                        "overall_confidence": metadata.get("overall_confidence"),
                        "total_words": metadata.get("total_words"),
                        "num_billed_pages": metadata.get("num_billed_pages")
                    }
                )
                return True
                
            except Exception as e:
                self.log_test("Upstage Service", False, f"Upstage OCR failed: {e}")
                return False
                
        except ImportError as e:
            self.log_test("Upstage Service", False, f"Import error: {e}")
            return False
        except Exception as e:
            self.log_test("Upstage Service", False, f"Unexpected error: {e}")
            return False
    
    async def test_api_health_endpoint(self) -> bool:
        """Test the health check endpoint"""
        try:
            import httpx
            
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{BASE_URL}/api/health", timeout=10.0)
                
                if response.status_code == 200:
                    data = response.json()
                    self.log_test(
                        "Health Endpoint",
                        True,
                        f"Health check passed (status: {data.get('status')})",
                        data
                    )
                    return True
                else:
                    self.log_test(
                        "Health Endpoint",
                        False,
                        f"Health check failed (status: {response.status_code})"
                    )
                    return False
                    
        except Exception as e:
            self.log_test("Health Endpoint", False, f"Connection error: {e}")
            return False
    
    async def test_api_extract_endpoint(self) -> bool:
        """Test the extract address endpoint"""
        try:
            import httpx
            
            # Read test image
            image_path = Path(__file__).parent / TEST_IMAGE_PATH
            with open(image_path, 'rb') as f:
                image_data = f.read()
            
            files = {"image": ("sample.jpeg", image_data, "image/jpeg")}
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{BASE_URL}/api/extract-address",
                    files=files,
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    self.log_test(
                        "Extract Address Endpoint",
                        True,
                        f"Address extraction successful (confidence: {data.get('confidence', {}).get('overall', 0):.3f})",
                        {
                            "image_id": data.get('imageId'),
                            "text_length": len(data.get('extractedText', '')),
                            "processing_time": data.get('processingTime'),
                            "overall_confidence": data.get('confidence', {}).get('overall')
                        }
                    )
                    return True
                else:
                    self.log_test(
                        "Extract Address Endpoint",
                        False,
                        f"Extraction failed (status: {response.status_code}): {response.text[:100]}"
                    )
                    return False
                    
        except Exception as e:
            self.log_test("Extract Address Endpoint", False, f"Request error: {e}")
            return False
    
    async def test_api_upstage_endpoint(self) -> bool:
        """Test the Upstage OCR endpoint"""
        try:
            import httpx
            
            # Read test image
            image_path = Path(__file__).parent / TEST_IMAGE_PATH
            with open(image_path, 'rb') as f:
                image_data = f.read()
            
            files = {"image": ("sample.jpeg", image_data, "image/jpeg")}
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{BASE_URL}/api/extract-address-upstage",
                    files=files,
                    timeout=45.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    upstage_metadata = data.get('upstage_metadata', {})
                    self.log_test(
                        "Upstage OCR Endpoint",
                        True,
                        f"Upstage extraction successful (confidence: {upstage_metadata.get('overall_confidence', 0):.3f})",
                        {
                            "image_id": data.get('imageId'),
                            "extracted_text": data.get('extractedText', '')[:50] + "..." if len(data.get('extractedText', '')) > 50 else data.get('extractedText', ''),
                            "text_length": len(data.get('extractedText', '')),
                            "processing_time": data.get('processingTime'),
                            "endpoint_name": data.get('endpoint_name'),
                            "ocr_provider": data.get('ocr_provider'),
                            "api_version": upstage_metadata.get('api_version'),
                            "model_version": upstage_metadata.get('model_version'),
                            "overall_confidence": upstage_metadata.get('overall_confidence'),
                            "total_words": upstage_metadata.get('total_words'),
                            "average_word_confidence": upstage_metadata.get('average_word_confidence')
                        }
                    )
                    return True
                else:
                    self.log_test(
                        "Upstage OCR Endpoint",
                        False,
                        f"Upstage extraction failed (status: {response.status_code}): {response.text[:100]}"
                    )
                    return False
                    
        except Exception as e:
            self.log_test("Upstage OCR Endpoint", False, f"Request error: {e}")
            return False
    
    
    async def test_complete_workflow(self) -> bool:
        """Test the complete address extraction workflow"""
        try:
            print("\n🔄 Running Complete Workflow Test...")
            
            # Step 1: Check if FastAPI server is running
            health_ok = await self.test_api_health_endpoint()
            if not health_ok:
                print("⚠️  FastAPI server not running. Starting component tests only...")
                return False
            
            # Step 2: Test address extraction API
            extract_ok = await self.test_api_extract_endpoint()
            
            # Step 3: Test Upstage OCR 
            upstage_ok = await self.test_api_upstage_endpoint()
            
            if extract_ok:
                workflow_status = "End-to-end workflow completed successfully"
                if upstage_ok:
                    workflow_status += " (Upstage OCR working)"
                else:
                    workflow_status += " (main endpoint working, Upstage-specific endpoint failed)"
                    
                self.log_test(
                    "Complete Workflow",
                    True,
                    workflow_status
                )
                return True
            else:
                self.log_test(
                    "Complete Workflow",
                    False,
                    "End-to-end workflow failed at extraction step"
                )
                return False
                
        except Exception as e:
            self.log_test("Complete Workflow", False, f"Workflow error: {e}")
            return False
    
    def run_all_tests(self):
        """Run all tests and generate report"""
        print("🧪 Korean Address Extractor Backend Test Suite")
        print("=" * 50)
        print(f"Test Mode: {'Real Services' if self.use_real_services else 'Mock Services'}")
        print(f"Sample Image: {TEST_IMAGE_PATH}")
        print()
        
        # Component Tests
        print("📦 Component Tests:")
        image_ok = self.test_image_file_exists()
        strands_ok = self.test_strands_service()
        upstage_ok = self.test_upstage_service()
        
        # API Tests (async)
        print("\n🌐 API Tests:")
        api_results = asyncio.run(self.test_complete_workflow())
        
        # Generate Report
        print("\n📊 Test Summary:")
        print("=" * 30)
        
        passed = sum(1 for result in self.test_results if result['success'])
        total = len(self.test_results)
        
        print(f"Tests Passed: {passed}/{total}")
        print(f"Success Rate: {(passed/total*100):.1f}%")
        
        if passed == total:
            print("🎉 All tests passed!")
            return 0
        else:
            print("❌ Some tests failed. Check the logs above.")
            return 1

def main():
    global TEST_IMAGE_PATH

    parser = argparse.ArgumentParser(description="Test Korean Address Extractor Backend")
    parser.add_argument(
        '--real-services', 
        action='store_true',
        help='Use real AWS services (requires credentials and setup)'
    )
    parser.add_argument(
        '--image-path',
        default=TEST_IMAGE_PATH,
        help='Path to test image file'
    )
    
    args = parser.parse_args()
    
    # Update global test image path if specified
    if args.image_path:
        TEST_IMAGE_PATH = args.image_path
    
    # Create tester and run tests
    tester = BackendTester(use_real_services=args.real_services)
    exit_code = tester.run_all_tests()
    
    sys.exit(exit_code)

if __name__ == "__main__":
    main()
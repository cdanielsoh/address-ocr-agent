import re
import json
import logging
import sys
import os
from strands import Agent, tool
from botocore.config import Config
from strands.models import BedrockModel
from typing import Dict, Any, List, Optional

# Add the app directory to path to import the correct AddressResult
sys.path.append(os.path.join(os.path.dirname(__file__), '../app'))
from models.response import AddressResult

# Set up logging for the agent
logger = logging.getLogger(__name__)

boto_config = Config(
    retries={"max_attempts": 3, "mode": "standard"},
    connect_timeout=5,
    read_timeout=1000
)

claude_model = BedrockModel(
    model_id="us.anthropic.claude-sonnet-4-20250514-v1:0",
    config=boto_config
)

@tool
def validate_korean_address_format(extracted_text: str) -> Dict[str, Any]:
    """
    Validate if extracted text follows Korean address format and identify components.
    
    Args:
        extracted_text (str): The text extracted from the image
        
    Returns:
        Dict: Validation results with component identification
    """
    # Korean address format patterns
    patterns = {
        "sido": r'(서울특별시|부산광역시|대구광역시|인천광역시|광주광역시|대전광역시|울산광역시|세종특별자치시|경기도|강원특별자치도|충청북도|충청남도|전북특별자치도|전라남도|경상북도|경상남도|제주특별자치도)',
        "sigungu": r'([가-힣]+구|[가-힣]+시|[가-힣]+군)',
        "road_name": r'([가-힣]+로\s*\d*길?|[가-힣]+길)',
        "building_number": r'(\d+(?:-\d+)?)',
        "dong": r'(\d+동)',
        "ho": r'(\d+호)',
        "legal_dong": r'\(([가-힣]+동)',
        "building_name": r'([가-힣]+아파트|[가-힣]+빌딩|[가-힣]+타워|[가-힣]+맨션)'
    }
    
    results = {}
    for component, pattern in patterns.items():
        match = re.search(pattern, extracted_text)
        results[component] = {
            "found": bool(match),
            "value": match.group(1) if match else None,
            "confidence": 0.9 if match else 0.1
        }
    
    return results


@tool
def lookup_address_components(sido: Optional[str] = None, sigungu: Optional[str] = None, road_name: Optional[str] = None, building_number: Optional[str] = None) -> Dict[str, Any]:
    """
    Lookup and validate address components using a mock database of known Korean addresses.
    This tool helps correct OCR errors and standardize address formats.
    
    Args:
        sido (Optional[str]): The province/city name (e.g., "서울특별시")
        sigungu (Optional[str]): The district name (e.g., "강남구")
        road_name (Optional[str]): The road name (e.g., "테헤란로")
        building_number (Optional[str]): The building number (e.g., "123")

    Returns:
        Dict: Validated and corrected address components with suggestions
    """
    
    # Mock database of Korean addresses with corrections
    address_database = {
        "서울특별시": {
            "standardized_name": "서울특별시",
            "aliases": ["서울시", "서울"],
            "districts": {
                "강남구": {
                    "standardized_name": "강남구",
                    "aliases": ["강남"],
                    "roads": {
                        "테헤란로": {"standardized_name": "테헤란로", "aliases": ["테헤란", "테헤란길"]},
                        "강남대로": {"standardized_name": "강남대로", "aliases": ["강남로"]},
                        "논현로": {"standardized_name": "논현로", "aliases": ["논현길"]},
                        "언주로": {"standardized_name": "언주로", "aliases": ["언주길"]},
                        "자곡로": {"standardized_name": "자곡로", "aliases": ["자곡길"]},
                        "압구정로": {"standardized_name": "압구정로", "aliases": ["압구정길"]},
                        "도산대로": {"standardized_name": "도산대로", "aliases": ["도산길"]},
                        "학동로": {"standardized_name": "학동로", "aliases": ["학동길"]},
                        "봉은사로": {"standardized_name": "봉은사로", "aliases": ["봉은사길"]},
                        "헌릉로": {"standardized_name": "헌릉로", "aliases": ["헌릉길"]},
                        "일원로": {"standardized_name": "일원로", "aliases": ["일원길"]},
                        "밤고개로": {"standardized_name": "밤고개로", "aliases": ["밤고개길"]},
                        "남부순환로": {"standardized_name": "남부순환로", "aliases": ["남부순환길"]},
                        "개포로": {"standardized_name": "개포로", "aliases": ["개포길"]},
                        "양재대로": {"standardized_name": "양재대로", "aliases": ["양재길"]},
                        "광평로": {"standardized_name": "광평로", "aliases": ["광평길"]},
                        "자곡로": {"standardized_name": "자곡로", "aliases": ["자곡길"]},
                        "압구정로": {"standardized_name": "압구정로", "aliases": ["압구정길"]},
                        "도산대로": {"standardized_name": "도산대로", "aliases": ["도산길"]},
                    }
                }
            }
        }
    }
    
    return address_database
    

# Create the Korean Address Confidence Analysis agent
korean_address_agent = Agent(
    model=claude_model,
    tools=[validate_korean_address_format, lookup_address_components],
    system_prompt="""You are a specialized AI agent for analyzing and correcting Korean address extraction from OCR results.

Your role is to:
1. Validate if extracted text follows Korean address format patterns
2. Analyze the quality of the extracted text
3. Use the lookup_address_components tool to validate and correct address components against a database
4. Calculate confidence scores for each address component
5. Return a structured AddressResult with standardized, corrected address components

When processing Korean addresses:
- Standard format: 시·도 + 시·군·구 + 도로명 + 건물번호 [동] [호수] (법정동명, 건물명)
- Required components: sido (시·도), sigungu (시·군·구), road_name (도로명), building_number (건물번호)
- Optional components: dong (동), ho (호), legal_dong (법정동), building_name (건물명)

Process workflow:
1. First validate the address format and extract components
2. Use lookup_address_components to check and standardize sido, sigungu, and road_name component against the database
3. Apply any corrections suggested by the database lookup
4. Calculate final confidence scores considering database validation
5. If results are validated by the database, the confidence score is 1.0
6. If you make any changes that cannot be validated by the database, the confidence score must be lower than 0.3 which will be flagged for human review.
7. Return the corrected and standardized address components

Confidence score examples:
자극로 -> 자곡로 (If validated by the database, the confidence score is 1.0)
20이동 -> 20동 (Changes are not validated by the database hence maximum confidence score is 0.3)

Required human review:
- If the confidence score is lower than 0.3 for any component
- If sigungu, road_name is not validated by the database
- If there is only one of dong, ho. (e.g. 303호 found only but no dong or 209동 found only but no ho)

Always use all provided tools to perform thorough analysis and correction."""
)

def extract_and_correct_korean_address(extracted_text: str) -> AddressResult:
    """
    Extract and correct Korean address using Strands agent with structured output.
    
    Args:
        extracted_text (str): Text extracted from OCR
        
    Returns:
        AddressResult: Structured and corrected address components
    """
    logger.info(f"🤖 [AGENT] Starting Korean address extraction and correction")
    logger.debug(f"📝 [AGENT] Input text: '{extracted_text}'")
    
    try:
        prompt = f"""
        Please analyze and correct this Korean address extracted from OCR: "{extracted_text}"
        
        Follow these steps:
        1. Use validate_korean_address_format to identify address components
        2. Use lookup_address_components to validate and correct each component against the database
        3. Apply any corrections suggested by the database lookup
        4. Return the standardized address components with confidence score for each component

        
        The response should contain the corrected and standardized address components.
        """

        structured_output_prompt = """The confidence field should be a dictionary of each address component with a confidence score between 0 and 1
        Example: {'sido': 1.0, 'sigungu': 1.0, 'road_name': 1.0, 'building_number': 1.0, 'dong': 1.0, 'ho': 1.0, 'legal_dong': 0.0, 'building_name': 0.0}"""
        
        logger.info(f"🔄 [AGENT] Invoking Strands agent with structured output")
        # Use structured_output to get AddressResult
        agent_results = korean_address_agent(prompt)
        result = korean_address_agent.structured_output(AddressResult)
        logger.info(f"✅ [AGENT] Agent processing completed successfully")
        logger.info(f"Response Type: {type(result)}")
        logger.info(f"Response Module: {result.__class__.__module__}")
        return result
        
    except Exception as e:
        logger.error(f"❌ [AGENT] Agent processing failed: {str(e)}")
        logger.warning(f"⚠️ [AGENT] Returning fallback result")
        # Return a fallback result if structured output fails
        fallback = AddressResult(
            sido=None,
            sigungu=None,
            road_name=None,
            building_number=None,
            dong=None,
            ho=None,
            legal_dong=None,
            building_name=None,
            confidence={},
            human_review=True  # Always require human review for fallback cases
        )
        return fallback


if __name__ == "__main__":
    extracted_text = "서울시 강남구 자극로 21 20이동 303 호"
    result = extract_and_correct_korean_address(extracted_text)
    print(result)
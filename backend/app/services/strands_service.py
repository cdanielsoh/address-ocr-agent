import logging
import sys
import os
from app.models.response import AddressResult

# Add the strands_agent to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '../../strands_agent'))

logger = logging.getLogger(__name__)

class StrandsService:
    def __init__(self):
        self.use_real_agent = os.getenv('USE_STRANDS_AGENT', 'true').lower() == 'true'
    
    async def get_corrected_address(self, extracted_text: str) -> AddressResult:
        """Get corrected and standardized address using Strands agent structured output"""
        logger.info(f"🧠 [STRANDS] Starting address correction - Agent enabled: {self.use_real_agent}")
        logger.debug(f"📝 [STRANDS] Input text: '{extracted_text}'")
        
        if self.use_real_agent:
            try:
                logger.info(f"🤖 [STRANDS] Using real Strands agent for address correction")
                # Import and use the new structured output function
                from agent import extract_and_correct_korean_address
                
                # Get corrected address using structured output
                logger.info(f"🔄 [STRANDS] Invoking agent with structured output")
                result = extract_and_correct_korean_address(extracted_text)
                logger.debug(f"🏠 [STRANDS] Corrected address: sido='{result.sido}', sigungu='{result.sigungu}', road_name='{result.road_name}', building_number='{result.building_number}'")
                return result
                    
            except Exception as e:
                logger.error(f"❌ [STRANDS] Agent address correction failed: {str(e)}")
                logger.warning(f"⚠️ [STRANDS] Falling back to empty result")
                # Fall back to empty result
                return AddressResult(
                    sido=None,
                    sigungu=None,
                    road_name=None,
                    building_number=None,
                    dong=None,
                    ho=None,
                    legal_dong=None,
                    building_name=None,
                    confidence={},
                    human_review=True
                )
        else:
            logger.info(f"🎭 [STRANDS] Agent disabled - returning empty result")
            # Return empty result when agent is disabled
            return AddressResult(
                sido=None,
                sigungu=None,
                road_name=None,
                building_number=None,
                dong=None,
                ho=None,
                legal_dong=None,
                building_name=None,
                confidence={},
                human_review=True
            )
    

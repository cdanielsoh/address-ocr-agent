import re
import json
import logging
import sys
import os
import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed
from strands import Agent, tool
from botocore.config import Config
from strands.models import BedrockModel
from typing import Dict, Any, List, Optional

# Add the app directory to path to import the correct models
sys.path.append(os.path.join(os.path.dirname(__file__), '../app'))
from models.response import AddressResult, ContactInfo, MultiEntryResult, InitialExtractionResult

# Set up logging for the agent
logger = logging.getLogger(__name__)

def repair_json(json_str: str) -> str:
    """
    Attempt to repair common JSON syntax errors from LLM outputs.
    
    Args:
        json_str: Potentially malformed JSON string
        
    Returns:
        Repaired JSON string
    """
    # Remove any leading/trailing whitespace and non-JSON content
    json_str = json_str.strip()
    
    # Common repairs for LLM-generated JSON
    repairs = [
        # Fix missing commas between objects/arrays
        (r'}\s*{', '},\n{'),
        (r'}\s*\[', '},\n['),
        (r']\s*{', '],\n{'),
        (r']\s*\[', '],\n['),
        
        # Fix missing commas between key-value pairs
        (r'"\s*\n\s*"', '",\n"'),
        (r'(["\]\}])\s*\n\s*"([^"]*)":', r'\1,\n"\2":'),
        
        # Fix missing commas after values
        (r'(["\d\]\}])\s*\n\s*(["\[\{])', r'\1,\n\2'),
        
        # Fix trailing commas (remove them)
        (r',\s*([}\]])', r'\1'),
        
        # Fix unquoted keys (basic cases)
        (r'([{\s,])\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*:', r'\1"\2":'),
        
        # Fix single quotes to double quotes
        (r"'([^']*)'", r'"\1"'),
        
        # Fix missing quotes around string values (basic heuristic)
        (r':\s*([a-zA-Z가-힣][^,}\]\n]*[^,}\]\s\n])\s*([,}\]])', r': "\1"\2'),
        
        # Fix null values
        (r':\s*null\s*', ': null'),
        (r':\s*None\s*', ': null'),
        
        # Fix boolean values
        (r':\s*True\s*', ': true'),
        (r':\s*False\s*', ': false'),
    ]
    
    # Apply repairs
    for pattern, replacement in repairs:
        json_str = re.sub(pattern, replacement, json_str, flags=re.MULTILINE)
    
    return json_str

def try_parse_json_with_repair(json_str: str, max_attempts: int = 3) -> tuple[bool, Any, str]:
    """
    Try to parse JSON with progressive repair attempts.
    
    Returns:
        (success: bool, parsed_data: Any, method_used: str)
    """
    # Attempt 1: Parse as-is
    try:
        data = json.loads(json_str)
        return True, data, "direct_parse"
    except json.JSONDecodeError as e:
        logger.debug(f"Direct JSON parse failed: {str(e)}")
    
    # Attempt 2: Basic repair
    try:
        repaired = repair_json(json_str)
        data = json.loads(repaired)
        logger.info("✅ JSON repaired successfully with basic fixes")
        return True, data, "basic_repair"
    except json.JSONDecodeError as e:
        logger.debug(f"Basic repair failed: {str(e)}")
    
    # Attempt 3: More aggressive repair - try to extract valid JSON portions
    try:
        # Try to find the largest valid JSON structure
        json_patterns = [
            r'\[.*\]',  # Array
            r'\{.*\}',  # Object
        ]
        
        for pattern in json_patterns:
            matches = re.finditer(pattern, json_str, re.DOTALL)
            for match in matches:
                candidate = match.group()
                try:
                    repaired_candidate = repair_json(candidate)
                    data = json.loads(repaired_candidate)
                    logger.info("✅ JSON repaired with aggressive extraction")
                    return True, data, "aggressive_repair"
                except json.JSONDecodeError:
                    continue
        
        return False, None, "repair_failed"
        
    except Exception as e:
        logger.error(f"JSON repair completely failed: {str(e)}")
        return False, None, "repair_error"

boto_config = Config(
    retries={"max_attempts": 3, "mode": "adaptive"},
    connect_timeout=1000,
    read_timeout=1000
)

claude_model = BedrockModel(
    model_id="us.anthropic.claude-sonnet-4-20250514-v1:0",
    boto_client_config=boto_config
)

claude_haiku_3_5_model = BedrockModel(
    model_id="anthropic.claude-3-5-haiku-20241022-v1:0",
    boto_client_config=boto_config
)

claude_sonnet_3_7_model = BedrockModel(
    model_id="us.anthropic.claude-3-7-sonnet-20250219-v1:0",
    boto_client_config=boto_config
)

nova_pro_model = BedrockModel(
    model_id="us.amazon.nova-pro-v1:0",
    boto_client_config=boto_config,
    max_tokens=8192
)

nova_lite_model = BedrockModel(
    model_id="us.amazon.nova-lite-v1:0",
    boto_client_config=boto_config,
    max_tokens=8192
)

nova_micro_model = BedrockModel(
    model_id="us.amazon.nova-micro-v1:0",
    boto_client_config=boto_config,
    max_tokens=8192
)

openai_oss_model = BedrockModel(
    model_id="openai.gpt-oss-120b-1:0",
    boto_client_config=boto_config,
    max_tokens=8192
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
        "sido": r'(서울*|부산*|대구*|인천*|광주*|대전*|울산*|세종*|경기*|강원*|충청|전라*|경상|제주*)',
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


def process_single_batch(batch_info: Dict, batch_idx: int, total_batches: int, entry_counter_start: int) -> Dict[str, Any]:
    """
    Process a single geographical batch and return results.
    
    Args:
        batch_info: Batch information dictionary
        batch_idx: Batch index (0-based)
        total_batches: Total number of batches
        entry_counter_start: Starting entry number for this batch
        
    Returns:
        Dict with batch results, entries, and metadata
    """
    batch_num = batch_idx + 1
    region = batch_info["region"]
    batch_contacts = batch_info["contacts"]
    batch_type = batch_info["batch_type"]
    
    logger.info(f"🏙️ [AGENT] Processing batch {batch_num}/{total_batches} - Region: {region} ({len(batch_contacts)} contacts)")
    
    # Create region-aware batch prompt with geographical context
    batch_text = "\n\n".join([f"Contact {entry_counter_start + j + 1}: {contact}" for j, contact in enumerate(batch_contacts)])
    
    # Get regional context for better address processing
    regional_context = ""
    if batch_type in ["large_region_full", "large_region_remainder", "small_region_complete"]:
        base_region = region.split(" (")[0]  # Remove any suffix
        if base_region != "기타":
            regional_context = f"""
            
            REGIONAL CONTEXT: All contacts in this batch are from {base_region}.
            Use this regional knowledge to improve address component extraction and validation.
            Common address patterns for {base_region} should be prioritized.
            """
    elif batch_type == "mixed_regions_optimized":
        # Parse combined regions from format like "서울(5) + 부산(3) + 기타(2)"
        regions_in_batch = []
        if " + " in region:
            for part in region.split(" + "):
                region_name = part.split("(")[0]
                regions_in_batch.append(region_name)
        else:
            regions_in_batch = [region]
        
        unique_regions = list(set(regions_in_batch))
        if len(unique_regions) == 1 and unique_regions[0] != "기타":
            # All contacts from same region, even though it was optimized
            regional_context = f"""
            
            REGIONAL CONTEXT: All contacts in this batch are from {unique_regions[0]}.
            Use this regional knowledge to improve address component extraction and validation.
            """
        else:
            # Mixed regions
            regional_context = f"""
            
            MIXED REGIONAL CONTEXT: This batch contains contacts from multiple regions: {', '.join(unique_regions)}.
            Pay attention to regional address patterns for each contact based on their location.
            """
    
    batch_prompt = f"""
    Please analyze and extract contact entries from this Korean document batch ({batch_num}/{total_batches}) - Region: {region}:
    
    {batch_text}{regional_context}
    
    Follow these steps for each contact:
    1. Extract phone number using validate_phone_number_format (prioritize cellphones)
    2. Extract address using validate_korean_address_format and lookup_address_components
    3. Leverage regional context to improve address component accuracy
    4. Calculate confidence scores for each component
    5. Determine if human review is needed
    
    Process ALL {len(batch_contacts)} contacts in this batch. Do not skip any entries.
    Return complete structured contact information for each entry.
    """

    try:
        logger.info(f"🚀 [AGENT] Invoking agent for geographical batch {batch_num} with JSON-first approach")
        korean_address_agent = get_korean_address_agent()
        
        # Step 1: Try fast JSON parsing first
        batch_entries = []
        batch_method = "unknown"
        
        try:
            agent_results = korean_address_agent(batch_prompt)
            
            # Try to extract JSON object from the response
            json_pattern = r'\{.*"entries".*\}'
            json_match = re.search(json_pattern, str(agent_results), re.DOTALL)
            
            if json_match:
                json_string = json_match.group()
                success, batch_json, parse_method = try_parse_json_with_repair(json_string)
                
                if success and "entries" in batch_json and isinstance(batch_json["entries"], list):
                    logger.info(f"✅ [AGENT] JSON parsing successful for batch {batch_num} using {parse_method}")
                    # Convert JSON entries to ContactInfo objects
                    for j, entry_data in enumerate(batch_json["entries"]):
                        # Create AddressResult from JSON address data
                        address_data = entry_data.get("address", {})
                        if address_data:
                            address = AddressResult(
                                sido=address_data.get("sido"),
                                sigungu=address_data.get("sigungu"),
                                road_name=address_data.get("road_name"),
                                building_number=address_data.get("building_number"),
                                dong=address_data.get("dong"),
                                ho=address_data.get("ho"),
                                legal_dong=address_data.get("legal_dong"),
                                building_name=address_data.get("building_name"),
                                floor=address_data.get("floor"),
                                confidence=address_data.get("confidence", {}),
                                human_review=address_data.get("human_review", False)
                            )
                        else:
                            address = AddressResult(confidence={}, human_review=True)
                        
                        # Create ContactInfo from JSON data
                        contact_entry = ContactInfo(
                            name=entry_data.get("name"),
                            phone_number=entry_data.get("phone_number"),
                            phone_type=entry_data.get("phone_type"),
                            address=address,
                            confidence=entry_data.get("confidence", {}),
                            entry_number=entry_counter_start + j + 1,
                            human_review=entry_data.get("human_review", False)
                        )
                        batch_entries.append(contact_entry)
                    
                    batch_method = f"json_parsing_{parse_method}"
                    logger.info(f"✅ [AGENT] JSON parsing successful for batch {batch_num} using {parse_method}: {len(batch_entries)} entries")
                else:
                    raise Exception(f"Invalid JSON structure or failed repair ({parse_method})")
            else:
                raise Exception("No JSON object found")
                
        except Exception as json_error:
            logger.warning(f"⚠️ [AGENT] JSON parsing failed for batch {batch_num}: {str(json_error)}")
            logger.info(f"🔄 [AGENT] Falling back to structured output for batch {batch_num}")
            
            try:
                # Fallback to structured output
                batch_result = structured_output_agent.structured_output(MultiEntryResult, str(agent_results))
                
                if batch_result and batch_result.entries:
                    batch_entries = batch_result.entries
                    # Set entry numbers for this batch
                    for j, entry in enumerate(batch_entries):
                        entry.entry_number = entry_counter_start + j + 1
                    batch_method = "structured_output"
                    logger.info(f"✅ [AGENT] Structured output fallback successful for batch {batch_num}: {len(batch_entries)} entries")
                else:
                    raise Exception("Structured output returned no entries")
                    
            except Exception as structured_error:
                logger.error(f"❌ [AGENT] Both JSON and structured output failed for batch {batch_num}")
                logger.error(f"    JSON error: {str(json_error)}")
                logger.error(f"    Structured error: {str(structured_error)}")
                batch_method = "failed"
                batch_entries = []
        
        # Process successful entries or create fallbacks
        if batch_entries:
            logger.info(f"✅ [AGENT] Geographical batch {batch_num} ({region}) completed: {len(batch_entries)} entries processed using {batch_method}")
        else:
            logger.warning(f"⚠️ [AGENT] Batch {batch_num} ({region}) returned no entries, creating fallback entries")
            # Create fallback entries for this batch
            for j, contact in enumerate(batch_contacts):
                # Create empty address for fallback
                empty_address = AddressResult(
                    confidence={}, human_review=True
                )
                fallback_entry = ContactInfo(
                    address=empty_address,
                    confidence={},
                    entry_number=entry_counter_start + j + 1,
                    human_review=True
                )
                batch_entries.append(fallback_entry)
        
        return {
            "success": True,
            "batch_num": batch_num,
            "region": region,
            "entries": batch_entries,
            "method": batch_method,
            "contacts_count": len(batch_contacts)
        }
        
    except Exception as batch_error:
        logger.error(f"❌ [AGENT] Geographical batch {batch_num} ({region}) processing failed: {str(batch_error)}")
        # Create fallback entries for failed batch
        fallback_entries = []
        for j, contact in enumerate(batch_contacts):
            # Create empty address for fallback
            empty_address = AddressResult(
                confidence={"error": 0.0}, human_review=True
            )
            fallback_entry = ContactInfo(
                address=empty_address,
                confidence={"error": 0.0},
                entry_number=entry_counter_start + j + 1,
                human_review=True
            )
            fallback_entries.append(fallback_entry)
        
        return {
            "success": False,
            "batch_num": batch_num,
            "region": region,
            "entries": fallback_entries,
            "method": "failed",
            "error": str(batch_error),
            "contacts_count": len(batch_contacts)
        }


def group_contacts_by_geography(contacts: List[Dict]) -> Dict[str, List[Dict]]:
    """
    Group contacts by geographical proximity (sido, then sigungu) for better context processing.
    
    Args:
        contacts: List of contact dictionaries with address information
        
    Returns:
        Dict: Grouped contacts by geographical region
    """
    # Korean region patterns for grouping
    sido_patterns = {
        "서울": r'서울',
        "부산": r'부산', 
        "대구": r'대구',
        "인천": r'인천',
        "광주": r'광주',
        "대전": r'대전',
        "울산": r'울산',
        "세종": r'세종',
        "경기": r'경기',
        "강원": r'강원',
        "충북": r'충청?북도?|충북',
        "충남": r'충청?남도?|충남', 
        "전북": r'전라?북도?|전북',
        "전남": r'전라?남도?|전남',
        "경북": r'경상?북도?|경북',
        "경남": r'경상?남도?|경남',
        "제주": r'제주'
    }
    
    # Group contacts by region
    regional_groups = {}
    ungrouped = []
    
    for contact in contacts:
        address_text = str(contact.get('address', ''))
        name = contact.get('name', 'Unknown')
        
        # Find matching sido
        matched_sido = None
        for sido, pattern in sido_patterns.items():
            if re.search(pattern, address_text):
                matched_sido = sido
                break
        
        if matched_sido:
            if matched_sido not in regional_groups:
                regional_groups[matched_sido] = []
            regional_groups[matched_sido].append(contact)
        else:
            ungrouped.append(contact)
    
    # If we have ungrouped contacts, add them as a separate group
    if ungrouped:
        regional_groups["기타"] = ungrouped
    
    return regional_groups

def create_geographical_batches(regional_groups: Dict[str, List[Dict]], batch_size: int = 10) -> List[Dict]:
    """
    Create optimized batches that minimize total API calls while preserving regional context.
    
    Args:
        regional_groups: Contacts grouped by region
        batch_size: Target contacts per batch
        
    Returns:
        List of batch dictionaries with region info and contacts
    """
    # First, collect all contacts with their region info
    all_contacts_with_region = []
    for region, contacts in regional_groups.items():
        for contact in contacts:
            contact_with_region = contact.copy()
            contact_with_region['_region'] = region
            all_contacts_with_region.append(contact_with_region)
    
    total_contacts = len(all_contacts_with_region)
    
    # Calculate optimal number of batches to minimize API calls
    optimal_batches = (total_contacts + batch_size - 1) // batch_size
    
    logger.info(f"📊 [BATCH-OPT] Total contacts: {total_contacts}, Optimal batches: {optimal_batches}")
    
    batches = []
    
    # Sort regions by size (largest first) for better grouping
    sorted_regions = sorted(regional_groups.items(), key=lambda x: len(x[1]), reverse=True)
    
    # Strategy: Fill batches to exactly batch_size, prioritizing regional coherence when possible
    remaining_contacts = []
    
    for region, contacts in sorted_regions:
        region_size = len(contacts)
        
        if region_size >= batch_size:
            # Large region: create full batches and keep remainder
            full_batches = region_size // batch_size
            remainder = region_size % batch_size
            
            # Create full batches for this region
            for i in range(full_batches):
                start_idx = i * batch_size
                end_idx = start_idx + batch_size
                batches.append({
                    "region": f"{region} ({i+1}/{full_batches + (1 if remainder > 0 else 0)})",
                    "contacts": contacts[start_idx:end_idx],
                    "batch_type": "large_region_full"
                })
            
            # Add remainder to the pool
            if remainder > 0:
                for contact in contacts[full_batches * batch_size:]:
                    contact_with_region = contact.copy()
                    contact_with_region['_region'] = region
                    remaining_contacts.append(contact_with_region)
        else:
            # Small region: add all to the pool
            for contact in contacts:
                contact_with_region = contact.copy()
                contact_with_region['_region'] = region
                remaining_contacts.append(contact_with_region)
    
    # Now create optimal batches from remaining contacts
    while remaining_contacts:
        batch_contacts = []
        batch_regions = {}
        
        # Fill batch to exactly batch_size (or take all remaining if less than batch_size)
        take_count = min(batch_size, len(remaining_contacts))
        
        for _ in range(take_count):
            contact = remaining_contacts.pop(0)
            region = contact.pop('_region')  # Remove the region marker
            batch_contacts.append(contact)
            
            if region not in batch_regions:
                batch_regions[region] = 0
            batch_regions[region] += 1
        
        # Create descriptive region name
        if len(batch_regions) == 1:
            # Single region
            region_name = list(batch_regions.keys())[0]
            if region_name in [r for r, c in sorted_regions if len(c) >= batch_size]:
                # This is remainder from a large region
                region_display = f"{region_name} (remainder)"
                batch_type = "large_region_remainder"
            else:
                # This is a complete small region
                region_display = region_name
                batch_type = "small_region_complete"
        else:
            # Multiple regions combined
            region_parts = [f"{region}({count})" for region, count in batch_regions.items()]
            region_display = " + ".join(region_parts)
            batch_type = "mixed_regions_optimized"
        
        batches.append({
            "region": region_display,
            "contacts": batch_contacts,
            "batch_type": batch_type
        })
    
    logger.info(f"✅ [BATCH-OPT] Created {len(batches)} optimized batches (target was {optimal_batches})")
    return batches

@tool
def validate_phone_number_format(text: str) -> Dict[str, Any]:
    """
    Extract and validate phone numbers, prioritizing cellphones (010-XXXX-XXXX).
    
    Args:
        text (str): The text to search for phone numbers
        
    Returns:
        Dict: Validation results with extracted phone numbers
    """
    # Phone number patterns (in priority order)
    phone_patterns = [
        (r'01(0|1|6|8|9)[-\s]*(\d{3,4})[-\s]*(\d{4})', 'cellphone', 0.9),   # Alternative cellphone format
        (r'02[-\s]*(\d{3,4})[-\s]*(\d{4})', 'landline', 0.8),   # Seoul landline
        (r'0(31|32|33|41|42|43|44|51|52|53|54|55|61|62|63|64)[-\s]*(\d{3,4})[-\s]*(\d{4})', 'landline', 0.75),  # Other area codes
    ]
    
    phones = []
    for pattern, phone_type, base_confidence in phone_patterns:
        matches = re.finditer(pattern, text)
        for match in matches:
            if phone_type == 'cellphone' and len(match.groups()) >= 2:
                # Reconstruct cellphone number
                phone_number = f"010-{match.group(1)}-{match.group(2)}"
            else:
                # Use the full match for other patterns
                phone_number = match.group(0).replace(' ', '-')
                # Clean up multiple dashes
                phone_number = re.sub(r'-+', '-', phone_number)
            
            # Higher confidence if found with "전화번호" label
            confidence = base_confidence + 0.05 if '전화번호' in text else base_confidence
            
            phones.append({
                "phone_number": phone_number,
                "phone_type": phone_type,
                "confidence": confidence,
                "context": match.group(0)
            })
    
    return {
        "phones_found": phones,
        "total_phones": len(phones)
    }


contact_info_extraction_agent = Agent(
    model=nova_lite_model,
    # tools=[validate_korean_address_format, validate_phone_number_format],
    system_prompt="""You are a specialized AI agent for extracting basic contact information from Korean documents.
    
    Your task is to identify and extract all contact entries from the given text.
    Make sure not to mix up the names and contact information.
    Normally, the contact information follows the name.
    There may be some cases where there is no available contact information.
    Also remove any corrupted or invalid Unicode characters.
    
    IMPORTANT: Return ONLY a valid JSON array, no preamble or explanation.
    
    Each contact should be a dictionary with these fields:
    - "name": Korean person names or test names like "테스트1" (string or null)
    - "phone_number": All phone numbers found (string or null)  
    - "address": Any address information found (string or null)
    - "raw_text": The original text segment for this contact (string or null)
    
    Extract ALL contacts found in the document. Do not skip any entries.
    Look for patterns like:
    - Names followed by phone numbers
    - Names followed by addresses  
    - Phone numbers with address information
    - Any structured contact information
    
    Response format example:
    [
        {
            "name": "테스트1",
            "phone_number": ["010-1234-5678", "02-1234-5678"],
            "address": "서울시 강남구 테헤란로 123",
            "raw_text": "테스트1 010-1234-5678 서울시 강남구 테헤란로 123"
        }
    ]
    
    If you cannot find an address associated with a person, set the address to null.
    """
)


# Create the Korean Address Confidence Analysis agent
def get_korean_address_agent() -> Agent:
    return Agent(
    model=claude_model,
    tools=[lookup_address_components],
    system_prompt="""You are a specialized AI agent for extracting multiple contact entries from Korean documents.

IMPORTANT: Return ONLY a valid JSON object with "entries" array, no preamble or explanation.

Each entry should contain:
1. Name (이름) - Korean person name or test names like "테스트1"
2. Phone Number (전화번호) - prioritize cellphone (010-XXXX-XXXX) over landline
3. Address (주소) - Korean address components with confidence scores

Process workflow:
1. For each entry:
   - Make sure to read the raw_text field to make sure that the given fields are correct. 
   (e.g. Multiple names in the raw_text field may have been extracted as a single name. Preprocessing has been done with a smaller model and it may have made mistakes.)
   - Extract and validate names, phone numbers, and addresses
   - Use tools to validate address components and phone numbers
   - Calculate confidence scores for each component
   - Determine if human review is needed
2. Return structured results for all entries

Response format example:
{
  "entries": [
    {
      "name": "테스트1",
      "phone_number": "010-1234-5678",
      "phone_type": "cellphone",
      "address": {
        "sido": "서울특별시", (Required. Typically all Korean words like 서울특별시, 경기도, 인천시, etc.)
        "sigungu": "강남구", (Required. Typically all Korean words like 강남구, 성동구, 종로구, etc.)
        "road_name": "테헤란로", (Required. Typically all Korean words like 테헤란로 XX길, 강남대로, 종로, etc. that ends with 로)
        "building_number": "123", (Required. Typically numbers like 123, 456, 789, etc.)
        "dong": null, (Typically numbers like 101동, 102동, 103동, etc. or alphabets like A동, B동, C동, etc. that ends with 동)
        "ho": null, (Typically numbers like 101호, 102호, 103호, etc. that ends with 호 or entries that include dashes like D-01)
        "legal_dong": null, (Optional. Typically all Korean words like 도곡동, 역삼동, 강남동, etc. that ends with 동)
        "building_name": null, (Optional. Typically all Korean words like 테헤란빌라, 럭키상가, 금성빌딩 etc.)
        "floor": null, (Typically numbers like 1층, 2층, 3층, etc. that ends with 층)
        "confidence": {"sido": 0.9, "sigungu": 0.9, "road_name": 0.8, "building_number": 0.7}, (Required. A dictionary of confidence scores for each component, from 0 to 1)
        "human_review": false
      },
      "confidence": {"name": 0.9, "phone": 0.95, "address": 0.8},
      "entry_number": 1,
      "human_review": false
    }
  ],
  "total_entries": 1
}

Address Confidence Scoring:
**Address components sido, sigungu, road_name must be validated by the database. Otherwise, mark them as human review required.**
- Database-validated components: 1.0
- Pattern-matched components: 0.7-0.9 (requires human review)
- Uncertain extractions: <0.3 (requires human review)

Phone number priority:
1. Cellphone (010-XXXX-XXXX): Highest priority
2. Landline (02-XXXX-XXXX, etc.): Lower priority

Set human_review to true when:
- Any component confidence < 0.3
- Address components not validated
- Incomplete phone/address pairs
- Ambiguous name extraction

Always use all provided tools for thorough analysis."""
)


structured_output_agent = Agent(model=nova_lite_model)

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
        korean_address_agent = get_korean_address_agent()
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
            confidence={},
            human_review=True  # Always require human review for fallback cases
        )
        return fallback

def extract_multiple_contact_entries(extracted_text: str, batch_size: int = 10) -> MultiEntryResult:
    """
    Extract multiple contact entries using Strands agent with mini-batch processing.
    
    Args:
        extracted_text (str): Text extracted from OCR
        batch_size (int): Number of contacts to process in each batch (default: 10)
        
    Returns:
        MultiEntryResult: Multiple structured contact entries
    """
    logger.info(f"🤖 [AGENT] Starting multiple contact entry extraction with batch size: {batch_size}")
    logger.debug(f"📝 [AGENT] Input text: '{extracted_text}'")
    
    try:
        # Step 1: Extract basic contact info using structured output
        logger.info(f"🔍 [AGENT] Extracting basic contact information with structured output")
        
        initial_prompt = f"""
        Extract all contact information from this Korean document:
        
        {extracted_text}
        
        Identify every contact entry and extract basic information for each one.
        """
        
        # Use fast JSON parsing first, structured output as fallback
        contacts = []
        total_contacts = 0
        extraction_method = "unknown"
        
        try:
            logger.info(f"🚀 [AGENT] Attempting fast JSON parsing for initial extraction")
            agent_response = contact_info_extraction_agent(initial_prompt)
            logger.info(f"🔍 [AGENT] Agent response: {agent_response}")
            # Try to extract JSON array from the response
            try:
                contacts = json.loads(str(agent_response))
                total_contacts = len(contacts)
                extraction_method = "json_parsing"
                logger.info(f"✅ [AGENT] JSON parsing successful: {total_contacts} contacts extracted")
            except Exception as json_error:
                logger.warning(f"⚠️ [AGENT] JSON parsing failed: {str(json_error)}")
                raise Exception("JSON parsing failed, trying structured output")
            
            pattern = r'\[.*?\]'
            match = re.search(pattern, str(agent_response), re.DOTALL)
            
            if match:
                json_string = match.group()
                success, contacts, parse_method = try_parse_json_with_repair(json_string)
                
                if success and isinstance(contacts, list):
                    total_contacts = len(contacts)
                    extraction_method = f"json_parsing_{parse_method}"
                    logger.info(f"✅ [AGENT] JSON parsing successful ({parse_method}): {total_contacts} contacts extracted")
                else:
                    logger.warning(f"⚠️ [AGENT] JSON repair failed or invalid structure")
                    raise Exception("JSON parsing and repair failed, trying structured output")
            else:
                logger.warning(f"⚠️ [AGENT] No JSON array found in agent response")
                raise Exception("No JSON found, trying structured output")
                
        except Exception as json_error:
            logger.info(f"🔄 [AGENT] Falling back to structured output due to: {str(json_error)}")
            
            try:
                # Fallback to structured output (slower but more reliable)
                initial_result = structured_output_agent.structured_output(InitialExtractionResult, initial_prompt)
                contacts = initial_result.contacts
                total_contacts = len(contacts)
                extraction_method = "structured_output"
                logger.info(f"✅ [AGENT] Structured output fallback successful: {total_contacts} contacts extracted")
                
            except Exception as structured_error:
                logger.error(f"❌ [AGENT] Both JSON parsing and structured output failed")
                logger.error(f"    JSON error: {str(json_error)}")
                logger.error(f"    Structured error: {str(structured_error)}")
                contacts = []
                total_contacts = 0
                extraction_method = "failed"
        
        logger.info(f"📊 [AGENT] Structured extraction found {total_contacts} initial contacts, processing in batches of {batch_size}")
        
        if total_contacts == 0:
            return MultiEntryResult(
                entries=[], 
                total_entries=0
            )

        # Step 2: Group contacts by geography for better context
        logger.info(f"🗺️ [AGENT] Grouping contacts by geographical region")
        regional_groups = group_contacts_by_geography(contacts)
        logger.info(f"📍 [AGENT] Found {len(regional_groups)} geographical regions: {list(regional_groups.keys())}")
        
        # Step 3: Create geographical batches
        geographical_batches = create_geographical_batches(regional_groups, batch_size)
        total_batches = len(geographical_batches)
        logger.info(f"📦 [AGENT] Created {total_batches} geographical batches")

        # Step 4: Process geographical batches in parallel (4 at a time)
        all_entries = []
        PARALLEL_BATCH_SIZE = 4
        
        logger.info(f"🚀 [AGENT] Starting parallel batch processing ({PARALLEL_BATCH_SIZE} batches at a time)")
        
        # Calculate entry counter starts for each batch
        entry_counter = 0
        batch_entry_starts = []
        for batch_info in geographical_batches:
            batch_entry_starts.append(entry_counter)
            entry_counter += len(batch_info["contacts"])
        
        # Process batches in parallel groups
        for i in range(0, len(geographical_batches), PARALLEL_BATCH_SIZE):
            batch_group = geographical_batches[i:i + PARALLEL_BATCH_SIZE]
            group_start_idx = i
            group_end_idx = min(i + PARALLEL_BATCH_SIZE, len(geographical_batches))
            
            logger.info(f"📦 [AGENT] Processing parallel group {group_start_idx//PARALLEL_BATCH_SIZE + 1}: batches {group_start_idx + 1}-{group_end_idx} (4 concurrent)")
            
            # Submit parallel batch processing tasks
            with ThreadPoolExecutor(max_workers=PARALLEL_BATCH_SIZE) as executor:
                # Submit all batches in this group
                future_to_batch = {}
                for j, batch_info in enumerate(batch_group):
                    batch_idx = group_start_idx + j
                    entry_start = batch_entry_starts[batch_idx]
                    
                    future = executor.submit(
                        process_single_batch,
                        batch_info,
                        batch_idx,
                        total_batches,
                        entry_start
                    )
                    future_to_batch[future] = (batch_idx, batch_info)
                
                # Collect results as they complete
                batch_results = []
                for future in as_completed(future_to_batch):
                    batch_idx, batch_info = future_to_batch[future]
                    try:
                        result = future.result()
                        batch_results.append((batch_idx, result))
                        logger.info(f"✅ [AGENT] Parallel batch {result['batch_num']} completed: {result['method']} - {len(result['entries'])} entries")
                    except Exception as e:
                        logger.error(f"❌ [AGENT] Parallel batch {batch_idx + 1} failed with exception: {str(e)}")
                        # Create fallback result
                        fallback_entries = []
                        for j, contact in enumerate(batch_info["contacts"]):
                            empty_address = AddressResult(
                                confidence={"error": 0.0}, human_review=True
                            )
                            fallback_entry = ContactInfo(
                                address=empty_address,
                                confidence={"error": 0.0},
                                entry_number=batch_entry_starts[batch_idx] + j + 1,
                                human_review=True
                            )
                            fallback_entries.append(fallback_entry)
                        
                        batch_results.append((batch_idx, {
                            "success": False,
                            "batch_num": batch_idx + 1,
                            "region": batch_info["region"],
                            "entries": fallback_entries,
                            "method": "exception_fallback",
                            "error": str(e),
                            "contacts_count": len(batch_info["contacts"])
                        }))
                
                # Sort results by batch index to maintain order
                batch_results.sort(key=lambda x: x[0])
                
                # Add entries to final result in correct order
                for batch_idx, result in batch_results:
                    all_entries.extend(result["entries"])
                    if result["success"]:
                        logger.info(f"✅ [AGENT] Added {len(result['entries'])} entries from batch {result['batch_num']} ({result['region']}) using {result['method']}")
                    else:
                        logger.warning(f"⚠️ [AGENT] Added {len(result['entries'])} fallback entries from failed batch {result['batch_num']} ({result['region']})")
            
            logger.info(f"🎯 [AGENT] Parallel group {group_start_idx//PARALLEL_BATCH_SIZE + 1} completed. Total entries so far: {len(all_entries)}")

        logger.info(f"✅ [AGENT] Parallel batch processing completed: {len(all_entries)} total entries from {total_batches} batches (processed 4 at a time)")

        result = MultiEntryResult(
            entries=all_entries,
            total_entries=len(all_entries)
        )
        return result
        
    except Exception as e:
        logger.error(f"❌ [AGENT] Multi-entry processing failed: {str(e)}")
        logger.warning(f"⚠️ [AGENT] Returning fallback result")
        # Return a fallback result if structured output fails
        fallback = MultiEntryResult(
            entries=[],
            total_entries=0
        )
        return fallback


if __name__ == "__main__":
    # Test single entry
    single_text = "서울시 강남구 자극로 21 20이동 303 호"
    single_result = extract_and_correct_korean_address(single_text)
    print("Single entry result:", single_result)
    
    # Test multiple entries
    multi_text = """
    이름: 김철수 전화번호: 010-1234-5678
    주소: 서울시 강남구 테헤란로 123
    
    이름: 박영희 전화번호: 010-9876-5432
    주소: 부산시 해운대구 마린시티로 456
    """
    multi_result = extract_multiple_contact_entries(multi_text)
    print("Multi entry result:", multi_result)
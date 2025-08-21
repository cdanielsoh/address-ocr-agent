from fastapi import APIRouter, File, UploadFile, HTTPException
import uuid
import time
import logging
import tempfile
import os
from app.services.strands_service import StrandsService
from app.services.upstage_service import UpstageService
from app.models.response import MultiEntryResult

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/compare-address-extraction")
async def compare_address_extraction(image: UploadFile = File(...)):
    """Compare Korean address extraction between Upstage OCR and Strands Agent correction"""
    image_id = str(uuid.uuid4())
    logger.info(f"🔄 [COMPARE-API] Starting address extraction comparison - Image ID: {image_id}")
    
    # Validate file type
    if not image.content_type.startswith("image/"):
        logger.error(f"❌ [COMPARE-API] Invalid file type: {image.content_type} - Image ID: {image_id}")
        raise HTTPException(status_code=400, detail="File must be an image")
    
    # Validate file size (10MB limit)
    if image.size and image.size > 10 * 1024 * 1024:
        logger.error(f"❌ [COMPARE-API] File size too large: {image.size} bytes - Image ID: {image_id}")
        raise HTTPException(status_code=400, detail="File size exceeds 10MB limit")
    
    logger.info(f"✅ [COMPARE-API] File validation passed - Type: {image.content_type}, Size: {image.size} bytes - Image ID: {image_id}")
    start_time = time.time()
    
    try:
        # Save uploaded file to temporary path
        logger.info(f"💾 [COMPARE-API] Saving uploaded image to temporary file - Image ID: {image_id}")
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(image.filename)[1]) as temp_file:
            image_bytes = await image.read()
            temp_file.write(image_bytes)
            temp_file_path = temp_file.name
            logger.info(f"✅ [COMPARE-API] Image saved to: {temp_file_path} - Image ID: {image_id}")
        
        try:
            # Initialize services
            logger.info(f"🔧 [COMPARE-API] Initializing services - Image ID: {image_id}")
            upstage_service = UpstageService()
            strands_service = StrandsService()
            
            # Process image with Upstage OCR
            logger.info(f"🔍 [COMPARE-API] Starting Upstage OCR processing - Image ID: {image_id}")
            ocr_start = time.time()
            upstage_result = upstage_service.process_image_with_upstage(temp_file_path)
            ocr_time = int((time.time() - ocr_start) * 1000)
            extracted_text = upstage_result["extracted_text"]
            logger.info(f"✅ [COMPARE-API] Upstage OCR completed in {ocr_time}ms, extracted text length: {len(extracted_text)} - Image ID: {image_id}")
            logger.debug(f"📝 [COMPARE-API] Extracted text: '{extracted_text}' - Image ID: {image_id}")
            
            if not extracted_text:
                logger.error(f"❌ [COMPARE-API] No text found in image - Image ID: {image_id}")
                raise HTTPException(status_code=422, detail="No text found in image")
            
            # Get Upstage raw text result (no parsing, just clean the text)
            logger.info(f"🏠 [COMPARE-API] Preparing Upstage raw text result - Image ID: {image_id}")
            # Clean the extracted text - make it single line and strip whitespace
            cleaned_text = " ".join(extracted_text.split()).strip()
            upstage_raw_result = {
                "extracted_text": cleaned_text,
                "confidence": upstage_result.get("upstage_metadata", {}).get("average_word_confidence", 0.8),
                "is_raw_text": True
            }
            logger.info(f"✅ [COMPARE-API] Upstage raw result prepared - Text: '{cleaned_text}' - Image ID: {image_id}")
            
            # Get Agent corrected address result
            logger.info(f"🧠 [COMPARE-API] Starting Strands Agent address correction - Image ID: {image_id}")
            agent_start = time.time()
            agent_address_result = await strands_service.get_corrected_address(extracted_text)
            agent_time = int((time.time() - agent_start) * 1000)
            # Calculate average confidence from all components
            avg_confidence = sum(agent_address_result.confidence.values()) / len(agent_address_result.confidence) if agent_address_result.confidence else 0.0
            logger.info(f"✅ [COMPARE-API] Agent correction completed in {agent_time}ms, Avg Confidence: {avg_confidence:.3f} - Image ID: {image_id}")
            
            # Calculate processing time
            processing_time = int((time.time() - start_time) * 1000)
            logger.info(f"⏱️ [COMPARE-API] Total processing time: {processing_time}ms (OCR: {ocr_time}ms, Agent: {agent_time}ms) - Image ID: {image_id}")
            
            # Create comparison result as dictionary
            result = {
                "imageId": image_id,
                "upstage_result": upstage_raw_result,
                "agent_result": agent_address_result.model_dump(),
                "processingTime": processing_time
            }
            
            confidence_improvement = avg_confidence - upstage_raw_result["confidence"]
            logger.info(f"🎯 [COMPARE-API] Comparison completed - Raw OCR confidence: {upstage_raw_result['confidence']:.3f}, Agent avg confidence: {avg_confidence:.3f} - Image ID: {image_id}")
            
            return result
        
        finally:
            # Clean up temporary file
            if os.path.exists(temp_file_path):
                logger.info(f"🗑️ [COMPARE-API] Cleaning up temporary file: {temp_file_path} - Image ID: {image_id}")
                os.unlink(temp_file_path)
        
    except HTTPException:
        logger.error(f"❌ [COMPARE-API] HTTP exception occurred - Image ID: {image_id}")
        raise
    except Exception as e:
        logger.error(f"❌ [COMPARE-API] Unexpected error during address comparison - Image ID: {image_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/extract-multiple-entries")
async def extract_multiple_entries(image: UploadFile = File(...)):
    """Extract multiple contact entries (name, phone, address) from a single image"""
    image_id = str(uuid.uuid4())
    logger.info(f"🔄 [MULTI-ENTRY-API] Starting multi-entry extraction - Image ID: {image_id}")
    
    # Validate file type
    if not image.content_type.startswith("image/"):
        logger.error(f"❌ [MULTI-ENTRY-API] Invalid file type: {image.content_type} - Image ID: {image_id}")
        raise HTTPException(status_code=400, detail="File must be an image")
    
    # Validate file size (10MB limit)
    if image.size and image.size > 10 * 1024 * 1024:
        logger.error(f"❌ [MULTI-ENTRY-API] File size too large: {image.size} bytes - Image ID: {image_id}")
        raise HTTPException(status_code=400, detail="File size exceeds 10MB limit")
    
    logger.info(f"✅ [MULTI-ENTRY-API] File validation passed - Type: {image.content_type}, Size: {image.size} bytes - Image ID: {image_id}")
    start_time = time.time()
    
    try:
        # Save uploaded file to temporary path
        logger.info(f"💾 [MULTI-ENTRY-API] Saving uploaded image to temporary file - Image ID: {image_id}")
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(image.filename)[1]) as temp_file:
            image_bytes = await image.read()
            temp_file.write(image_bytes)
            temp_file_path = temp_file.name
            logger.info(f"✅ [MULTI-ENTRY-API] Image saved to: {temp_file_path} - Image ID: {image_id}")
        
        try:
            # Initialize services
            logger.info(f"🔧 [MULTI-ENTRY-API] Initializing services - Image ID: {image_id}")
            upstage_service = UpstageService()
            strands_service = StrandsService()
            
            # Process image with Upstage OCR
            logger.info(f"🔍 [MULTI-ENTRY-API] Starting Upstage OCR processing - Image ID: {image_id}")
            ocr_start = time.time()
            upstage_result = upstage_service.process_image_with_upstage(temp_file_path)
            ocr_time = int((time.time() - ocr_start) * 1000)
            extracted_text = upstage_result["extracted_text"]
            logger.info(f"✅ [MULTI-ENTRY-API] Upstage OCR completed in {ocr_time}ms, extracted text length: {len(extracted_text)} - Image ID: {image_id}")
            logger.debug(f"📝 [MULTI-ENTRY-API] Extracted text: '{extracted_text}' - Image ID: {image_id}")
            
            if not extracted_text:
                logger.error(f"❌ [MULTI-ENTRY-API] No text found in image - Image ID: {image_id}")
                raise HTTPException(status_code=422, detail="No text found in image")
            
            # Extract multiple contact entries using agent
            logger.info(f"🧠 [MULTI-ENTRY-API] Starting multi-entry extraction with agent - Image ID: {image_id}")
            agent_start = time.time()
            multi_entry_result = await strands_service.get_multiple_contact_entries(extracted_text, image_id)
            agent_time = int((time.time() - agent_start) * 1000)
            logger.info(f"✅ [MULTI-ENTRY-API] Multi-entry extraction completed in {agent_time}ms, Found {multi_entry_result.total_entries} entries - Image ID: {image_id}")
            
            # Calculate processing time
            processing_time = int((time.time() - start_time) * 1000)
            logger.info(f"⏱️ [MULTI-ENTRY-API] Total processing time: {processing_time}ms (OCR: {ocr_time}ms, Agent: {agent_time}ms) - Image ID: {image_id}")
            
            # Create processing metadata with raw OCR text
            processing_metadata = {
                "raw_text": extracted_text,
                "ocr_time_ms": ocr_time,
                "agent_time_ms": agent_time,
                "total_time_ms": processing_time,
                "text_length": len(extracted_text)
            }
            
            # Copy the result and add metadata using model_copy
            final_result = multi_entry_result.model_copy(update={
                "processing_metadata": processing_metadata,
                "image_id": image_id
            })
            
            logger.info(f"📊 [MULTI-ENTRY-API] Processing metadata added - Raw text length: {len(extracted_text)} characters")
            logger.info(f"🎯 [MULTI-ENTRY-API] Multi-entry extraction completed successfully - {final_result.total_entries} entries found - Image ID: {image_id}")
            
            return final_result.model_dump()
        
        finally:
            # Clean up temporary file
            if os.path.exists(temp_file_path):
                logger.info(f"🗑️ [MULTI-ENTRY-API] Cleaning up temporary file: {temp_file_path} - Image ID: {image_id}")
                os.unlink(temp_file_path)
        
    except HTTPException:
        logger.error(f"❌ [MULTI-ENTRY-API] HTTP exception occurred - Image ID: {image_id}")
        raise
    except Exception as e:
        logger.error(f"❌ [MULTI-ENTRY-API] Unexpected error during multi-entry extraction - Image ID: {image_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

import boto3
import json
import logging
from typing import Dict, Any, Optional
from botocore.exceptions import ClientError
import os
from requests_toolbelt import MultipartEncoder

logger = logging.getLogger(__name__)

class UpstageService:
    def __init__(self):
        self.sagemaker_client = boto3.client('sagemaker-runtime', region_name=os.getenv('AWS_REGION', 'us-west-2'))
        self.endpoint_name = os.getenv('SAGEMAKER_OCR_ENDPOINT_NAME', 'Endpoint-Document-OCR-1')
    
    def ocr_image_sagemaker(self, file_path: str, endpoint_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Performs OCR using Upstage OCR deployed in SageMaker.
        Access to the endpoint is required.

        :param file_path: The path to the image file
        :param endpoint_name: SageMaker endpoint name (optional, uses default if not provided)
        :return: Resulting Python dictionary of OCR
        """
        try:

            m = MultipartEncoder(
                fields={
                    "document": (file_path, open(file_path, 'rb'), 'image/jpeg'),
                    "model": "ocr"
                }
            )

            body = m.to_string()

            endpoint = endpoint_name or self.endpoint_name
            
            response = self.sagemaker_client.invoke_endpoint(
                EndpointName=endpoint,
                ContentType=m.content_type,
                Body=body,
            )

            # Parse the response
            result = json.loads(response['Body'].read())
            return result
            
        except ClientError as e:
            logger.error(f"SageMaker endpoint error: {e}")
            raise Exception(f"Upstage OCR failed: {str(e)}")
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse OCR response: {e}")
            raise Exception(f"Invalid OCR response format: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error during OCR: {e}")
            raise Exception(f"OCR processing failed: {str(e)}")
    
    def extract_text_from_ocr_result(self, ocr_result: Dict[str, Any]) -> str:
        """
        Extract plain text from Upstage OCR result.
        
        Expected format:
        {
          "text": "Print the words \\nhello, world",
          "pages": [{"text": "...", "words": [...]}],
          "confidence": 0.99
        }
        
        :param ocr_result: The raw OCR result from Upstage
        :return: Extracted text as string
        """
        try:
            # First try to get the main text field (most reliable)
            if 'text' in ocr_result and ocr_result['text']:
                return ocr_result['text'].strip()
            
            # Fallback to extracting from pages
            elif 'pages' in ocr_result and len(ocr_result['pages']) > 0:
                extracted_text = ""
                for page in ocr_result['pages']:
                    if 'text' in page and page['text']:
                        extracted_text += page['text'] + " "
                return extracted_text.strip()
            
            # Last resort: try to reconstruct from words
            elif 'pages' in ocr_result:
                extracted_text = ""
                for page in ocr_result['pages']:
                    if 'words' in page:
                        words = []
                        for word in page['words']:
                            if 'text' in word:
                                words.append(word['text'])
                        extracted_text += " ".join(words) + " "
                return extracted_text.strip()
            
            else:
                # Fallback: no recognized structure
                logger.warning(f"Unknown Upstage OCR result structure: {list(ocr_result.keys())}")
                return ""
                
        except Exception as e:
            logger.error(f"Failed to extract text from Upstage OCR result: {e}")
            return ""
    
    def extract_upstage_metadata(self, ocr_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract metadata from Upstage OCR result.
        
        :param ocr_result: The raw OCR result from Upstage
        :return: Extracted metadata
        """
        metadata = {
            "api_version": ocr_result.get("apiVersion"),
            "model_version": ocr_result.get("modelVersion"),
            "mime_type": ocr_result.get("mimeType"),
            "num_billed_pages": ocr_result.get("numBilledPages"),
            "overall_confidence": ocr_result.get("confidence"),
            "stored": ocr_result.get("stored"),
            "pages_info": []
        }
        
        # Extract page information
        if "metadata" in ocr_result and "pages" in ocr_result["metadata"]:
            for page_meta in ocr_result["metadata"]["pages"]:
                metadata["pages_info"].append({
                    "page": page_meta.get("page"),
                    "width": page_meta.get("width"),
                    "height": page_meta.get("height")
                })
        
        # Extract word-level confidence scores
        word_confidences = []
        if "pages" in ocr_result:
            for page in ocr_result["pages"]:
                if "words" in page:
                    for word in page["words"]:
                        word_confidences.append({
                            "text": word.get("text"),
                            "confidence": word.get("confidence"),
                            "bounding_box": word.get("boundingBox")
                        })
        
        metadata["word_confidences"] = word_confidences
        metadata["total_words"] = len(word_confidences)
        
        # Calculate average word confidence
        if word_confidences:
            avg_confidence = sum(w["confidence"] for w in word_confidences if w["confidence"]) / len(word_confidences)
            metadata["average_word_confidence"] = avg_confidence
        else:
            metadata["average_word_confidence"] = 0.0
        
        return metadata
    
    def process_image_with_upstage(self, file_path: str) -> Dict[str, Any]:
        """
        Complete OCR processing pipeline using Upstage.
        
        :param file_path: The path to the image file
        :return: Processed result with extracted text and metadata
        """
        logger.info(f"🔍 [UPSTAGE] Starting OCR processing for image: {file_path}")
        try:
            # Perform OCR
            logger.info(f"📡 [UPSTAGE] Invoking SageMaker endpoint: {self.endpoint_name}")
            ocr_result = self.ocr_image_sagemaker(file_path)
            
            # Extract plain text
            logger.info(f"📝 [UPSTAGE] Extracting text from OCR result")
            extracted_text = self.extract_text_from_ocr_result(ocr_result)
            logger.info(f"✅ [UPSTAGE] Text extraction completed - Length: {len(extracted_text)} characters")
            logger.debug(f"📄 [UPSTAGE] Extracted text: '{extracted_text}'")
            
            # Extract metadata
            logger.info(f"📊 [UPSTAGE] Extracting metadata from OCR result")
            upstage_metadata = self.extract_upstage_metadata(ocr_result)
            logger.info(f"✅ [UPSTAGE] Metadata extraction completed - Total words: {upstage_metadata.get('total_words', 0)}, Avg confidence: {upstage_metadata.get('average_word_confidence', 0):.3f}")
            
            # Return structured result
            result = {
                "extracted_text": extracted_text,
                "raw_ocr_result": ocr_result,
                "upstage_metadata": upstage_metadata,
                "ocr_provider": "upstage",
                "endpoint_name": self.endpoint_name,
                "text_length": len(extracted_text),
                "has_content": bool(extracted_text.strip())
            }
            logger.info(f"🎯 [UPSTAGE] OCR processing completed successfully")
            return result
            
        except Exception as e:
            logger.error(f"❌ [UPSTAGE] OCR processing failed: {str(e)}")
            raise
    

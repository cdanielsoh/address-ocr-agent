import boto3
import json
import logging
import re
from typing import Dict, Any, Optional, List, Tuple
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
    
    def extract_words_with_positions(self, ocr_result: Dict[str, Any]) -> List[Dict]:
        """
        Extract words with their bounding box positions from OCR result.
        
        :param ocr_result: The raw OCR result from Upstage
        :return: List of words with position information
        """
        words = []
        try:
            for page in ocr_result.get('pages', []):
                for word in page.get('words', []):
                    # Get the top-left corner position (y-coordinate for vertical grouping)
                    bbox = word.get('boundingBox', {}).get('vertices', [{}])[0]  # top-left vertex
                    if bbox:  # Ensure we have valid bounding box data
                        words.append({
                            'text': word.get('text', ''),
                            'x': bbox.get('x', 0),
                            'y': bbox.get('y', 0),
                            'confidence': word.get('confidence', 0.0),
                            'id': word.get('id', -1)
                        })
        except Exception as e:
            logger.error(f"Failed to extract words with positions: {e}")
        
        return words
    
    def group_words_into_lines(self, words: List[Dict], y_tolerance: int = 3) -> List[List[Dict]]:
        """
        Group words into lines based on their y-coordinates.
        Words with similar y-coordinates (within tolerance) are considered on the same line.
        
        :param words: List of words with position information
        :param y_tolerance: Vertical tolerance for grouping words into lines
        :return: List of lines, where each line is a list of words
        """
        if not words:
            return []
        
        try:
            # Sort words by y-coordinate first, then by x-coordinate
            sorted_words = sorted(words, key=lambda w: (w['y'], w['x']))
            
            lines = []
            current_line = [sorted_words[0]]
            current_y = sorted_words[0]['y']
            
            for word in sorted_words[1:]:
                # If the word is close enough vertically, add to current line
                if abs(word['y'] - current_y) <= y_tolerance:
                    current_line.append(word)
                else:
                    # Start a new line
                    # Sort current line by x-coordinate to ensure proper reading order
                    current_line.sort(key=lambda w: w['x'])
                    lines.append(current_line)
                    current_line = [word]
                    current_y = word['y']
            
            # Don't forget the last line
            if current_line:
                current_line.sort(key=lambda w: w['x'])
                lines.append(current_line)
            
            return lines
            
        except Exception as e:
            logger.error(f"Failed to group words into lines: {e}")
            return []
    
    def reconstruct_text_as_markdown(self, lines: List[List[Dict]]) -> str:
        """
        Reconstruct text from grouped lines and format as markdown.
        Simply reconstructs the text maintaining line structure without special formatting.
        
        :param lines: List of lines, where each line is a list of words
        :return: Reconstructed text in markdown format
        """
        try:
            markdown_lines = []
            
            for line in lines:
                # Join words in the line with spaces
                line_text = ' '.join(word['text'] for word in line)
                
                # Skip empty lines
                if not line_text.strip():
                    continue
                
                # Add line as plain text
                markdown_lines.append(line_text)
            
            return '\n'.join(markdown_lines)
            
        except Exception as e:
            logger.error(f"Failed to reconstruct text as markdown: {e}")
            return ""
    
    def reconstruct_structured_text(self, ocr_result: Dict[str, Any], format_type: str = "markdown") -> Dict[str, Any]:
        """
        Reconstruct structured text from OCR result using bounding box information.
        
        :param ocr_result: The raw OCR result from Upstage
        :param format_type: Output format type ("markdown", "plain", or "json")
        :return: Structured text reconstruction result
        """
        logger.info(f"🔧 [UPSTAGE] Starting structured text reconstruction (format: {format_type})")
        
        try:
            # Extract words with positions
            words = self.extract_words_with_positions(ocr_result)
            logger.info(f"📍 [UPSTAGE] Extracted {len(words)} words with position data")
            
            if not words:
                logger.warning("⚠️ [UPSTAGE] No words with position data found")
                return {
                    "reconstructed_text": "",
                    "format": format_type,
                    "total_words": 0,
                    "total_lines": 0,
                    "success": False,
                    "error": "No words with position data found"
                }
            
            # Group words into lines
            lines = self.group_words_into_lines(words, y_tolerance=8)
            logger.info(f"📏 [UPSTAGE] Grouped words into {len(lines)} lines")
            
            # Reconstruct text based on format type
            if format_type == "markdown":
                reconstructed_text = self.reconstruct_text_as_markdown(lines)
            elif format_type == "plain":
                # Simple plain text reconstruction
                reconstructed_text = '\n'.join(' '.join(word['text'] for word in line) for line in lines)
            elif format_type == "json":
                # Return structured JSON with line and word information
                reconstructed_text = json.dumps({
                    "lines": [
                        {
                            "line_number": i + 1,
                            "text": ' '.join(word['text'] for word in line),
                            "words": [
                                {
                                    "text": word['text'],
                                    "x": word['x'],
                                    "y": word['y'],
                                    "confidence": word['confidence']
                                } for word in line
                            ],
                            "bbox": {
                                "min_x": min(word['x'] for word in line),
                                "max_x": max(word['x'] for word in line),
                                "min_y": min(word['y'] for word in line),
                                "max_y": max(word['y'] for word in line)
                            }
                        } for i, line in enumerate(lines)
                    ]
                }, ensure_ascii=False, indent=2)
            else:
                raise ValueError(f"Unsupported format type: {format_type}")
            
            result = {
                "reconstructed_text": reconstructed_text,
                "format": format_type,
                "total_words": len(words),
                "total_lines": len(lines),
                "success": True,
                "average_confidence": sum(w['confidence'] for w in words) / len(words) if words else 0.0
            }
            
            logger.info(f"✅ [UPSTAGE] Text reconstruction completed successfully")
            logger.debug(f"📊 [UPSTAGE] Reconstruction stats - Words: {len(words)}, Lines: {len(lines)}, Format: {format_type}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ [UPSTAGE] Text reconstruction failed: {str(e)}")
            return {
                "reconstructed_text": "",
                "format": format_type,
                "total_words": 0,
                "total_lines": 0,
                "success": False,
                "error": str(e)
            }
    
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
            
            # Perform structured text reconstruction
            logger.info(f"🔧 [UPSTAGE] Performing structured text reconstruction")
            markdown_reconstruction = self.reconstruct_structured_text(ocr_result, format_type="markdown")
            plain_reconstruction = self.reconstruct_structured_text(ocr_result, format_type="plain")
            json_reconstruction = self.reconstruct_structured_text(ocr_result, format_type="json")
            
            # Return structured result
            result = {
                "extracted_text": extracted_text,
                "raw_ocr_result": ocr_result,
                "upstage_metadata": upstage_metadata,
                "ocr_provider": "upstage",
                "endpoint_name": self.endpoint_name,
                "text_length": len(extracted_text),
                "has_content": bool(extracted_text.strip()),
                "structured_text": {
                    "markdown": markdown_reconstruction,
                    "plain": plain_reconstruction,
                    "json": json_reconstruction
                }
            }
            logger.info(f"🎯 [UPSTAGE] OCR processing completed successfully")
            return result
            
        except Exception as e:
            logger.error(f"❌ [UPSTAGE] OCR processing failed: {str(e)}")
            raise
    

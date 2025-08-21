from pydantic import BaseModel, Field
from typing import Optional, Dict, List, Any

class AddressResult(BaseModel):
    sido: Optional[str] = Field(default=None, description="Province/city (시·도)")
    sigungu: Optional[str] = Field(default=None, description="District (시·군·구)")
    road_name: Optional[str] = Field(default=None, description="Road name (도로명)")
    building_number: Optional[str] = Field(default=None, description="Building number (건물번호)")
    dong: Optional[str] = Field(default=None, description="Dong unit (동)")
    ho: Optional[str] = Field(default=None, description="Ho unit (호)")
    legal_dong: Optional[str] = Field(default=None, description="Legal dong name (법정동)")
    building_name: Optional[str] = Field(default=None, description="Building name (건물명)")
    floor: Optional[str] = Field(default=None, description="Floor (층)")
    confidence: Dict[str, float] = Field(description="Confidence scores for each component")
    human_review: bool = Field(description="Whether human review is required")


class ContactInfo(BaseModel):
    name: Optional[str] = Field(default=None, description="Person's name (이름)")
    phone_number: Optional[str] = Field(default=None, description="Phone number (전화번호)")
    phone_type: Optional[str] = Field(default=None, description="Phone type: cellphone, landline, or unknown")
    address: AddressResult = Field(description="Parsed address components")
    confidence: Dict[str, float] = Field(description="Confidence scores for extracted data")
    entry_number: int = Field(description="Sequential entry number")
    human_review: bool = Field(description="Whether this entry needs human review")


class InitialExtractionResult(BaseModel):
    """Result from initial contact extraction pass using simple dictionaries"""
    contacts: List[Dict[str, Optional[str]]] = Field(
        description="List of contact dictionaries, each containing 'name', 'phone_number', 'address', and 'raw_text' fields"
    )
    total_contacts: int = Field(
        description="Total number of contacts found in the document"
    )

class MultiEntryResult(BaseModel):
    entries: List[ContactInfo] = Field(description="List of extracted contact entries")
    total_entries: int = Field(description="Total number of contact entries found")


class HealthResponse(BaseModel):
    status: str
    timestamp: str
    version: str
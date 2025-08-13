from pydantic import BaseModel
from typing import Optional, Dict

class AddressResult(BaseModel):
    sido: Optional[str] = None
    sigungu: Optional[str] = None
    road_name: Optional[str] = None
    building_number: Optional[str] = None
    dong: Optional[str] = None
    ho: Optional[str] = None
    legal_dong: Optional[str] = None
    building_name: Optional[str] = None
    floor: Optional[str] = None
    room_number: Optional[str] = None
    confidence: Dict[str, float]
    human_review: bool = False

    def to_formatted_address(self) -> str:
        """Format address components into a readable Korean address string"""
        parts = []
        
        if self.sido:
            parts.append(self.sido)
        if self.sigungu:
            parts.append(self.sigungu)
        if self.road_name:
            parts.append(self.road_name)
        if self.building_number:
            parts.append(self.building_number)
        if self.dong:
            parts.append(self.dong)
        if self.ho:
            parts.append(self.ho)
        if self.legal_dong and self.building_name:
            parts.append(f"({self.legal_dong}, {self.building_name})")
        
        return " ".join(parts) if parts else ""

class HealthResponse(BaseModel):
    status: str
    timestamp: str
    version: str
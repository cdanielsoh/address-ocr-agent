// Interfaces
export interface AddressResult {
  sido: string | null;
  sigungu: string | null;
  road_name: string | null;
  building_number: string | null;
  dong: string | null;
  ho: string | null;
  legal_dong: string | null;
  building_name: string | null;
  floor: string | null;
  confidence: { [key: string]: number };
  human_review: boolean;
}

export interface ContactEntry {
  name: string | null;
  phone_number: string | null;
  phone_type: 'cellphone' | 'landline' | 'unknown' | null;
  address: AddressResult | null;
  confidence: { [key: string]: number };
  entry_number: number;
  human_review: boolean;
}

export interface MultiEntryResult {
  entries: ContactEntry[];
  total_entries: number;
  processing_metadata: { [key: string]: any };
  image_id: string;
}

export interface EditableContact {
  id: number;
  name: string;
  phone: string;
  address: string;
  isEditing: boolean;
  needsReview: boolean;
  confidence: number;
}
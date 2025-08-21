import React from 'react';
import {
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
  Paper,
  Alert,
} from '@mui/material';
import { EditableContact, MultiEntryResult } from '../types';

interface AddressDetailsTableProps {
  contact: EditableContact;
  multiEntryResult: MultiEntryResult | null;
}

export const AddressDetailsTable: React.FC<AddressDetailsTableProps> = ({
  contact,
  multiEntryResult,
}) => {
  if (!multiEntryResult) {
    return (
      <Typography variant="body2" color="text.secondary" sx={{ py: 2 }}>
        주소 정보를 불러올 수 없습니다
      </Typography>
    );
  }

  // Find the original entry data for address details
  const originalEntry = multiEntryResult.entries.find(entry => entry.entry_number === contact.id);
  const address = originalEntry?.address;

  if (!address) {
    return (
      <Typography variant="body2" color="text.secondary" sx={{ py: 2 }}>
        주소 정보가 없습니다
      </Typography>
    );
  }

  const getConfidenceColor = (confidence: number): 'success' | 'warning' | 'error' => {
    if (confidence >= 0.8) return 'success';
    if (confidence >= 0.6) return 'warning';
    return 'error';
  };

  // Format individual address components with proper Korean suffixes (only if not already present)
  const formatComponent = (value: string | null, type: string): string | null => {
    if (!value) return null;
    
    const addSuffixIfMissing = (text: string, suffix: string): string => {
      return text.endsWith(suffix) ? text : `${text}${suffix}`;
    };
    
    switch (type) {
      case 'dong':
      case 'legal_dong':
        return addSuffixIfMissing(value, '동');
      case 'ho':
        return addSuffixIfMissing(value, '호');
      case 'floor':
        return addSuffixIfMissing(value, '층');
      default:
        return value;
    }
  };

  const addressComponents = [
    { label: '시도', value: formatComponent(address.sido, 'sido'), key: 'sido' },
    { label: '시군구', value: formatComponent(address.sigungu, 'sigungu'), key: 'sigungu' },
    { label: '도로명', value: formatComponent(address.road_name, 'road_name'), key: 'road_name' },
    { label: '건물번호', value: formatComponent(address.building_number, 'building_number'), key: 'building_number' },
    { label: '동', value: formatComponent(address.dong, 'dong'), key: 'dong' },
    { label: '호', value: formatComponent(address.ho, 'ho'), key: 'ho' },
    { label: '법정동', value: formatComponent(address.legal_dong, 'legal_dong'), key: 'legal_dong' },
    { label: '건물명', value: formatComponent(address.building_name, 'building_name'), key: 'building_name' },
    { label: '층', value: formatComponent(address.floor, 'floor'), key: 'floor' }
  ]; // Show all components regardless of values

  return (
    <Paper sx={{ bgcolor: 'grey.50', borderRadius: 2 }}>
      <TableContainer>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell sx={{ fontWeight: 600, bgcolor: 'grey.100' }}>구성요소</TableCell>
              <TableCell sx={{ fontWeight: 600, bgcolor: 'grey.100' }}>값</TableCell>
              <TableCell sx={{ fontWeight: 600, bgcolor: 'grey.100' }}>신뢰도</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {addressComponents.map((component) => (
              <TableRow key={component.key} sx={{ '&:hover': { bgcolor: 'grey.100' } }}>
                <TableCell sx={{ minWidth: 80 }}>
                  <Chip 
                    label={component.label} 
                    size="small" 
                    variant="outlined" 
                    color="primary"
                    sx={{ fontWeight: 500 }}
                  />
                </TableCell>
                <TableCell sx={{ fontWeight: 500, color: component.value ? 'text.primary' : 'text.secondary' }}>
                  {component.value || '정보 없음'}
                </TableCell>
                <TableCell>
                  {address.confidence[component.key] !== undefined ? (
                    <Chip
                      label={`${Math.round(address.confidence[component.key] * 100)}%`}
                      size="small"
                      color={getConfidenceColor(address.confidence[component.key])}
                      variant="filled"
                    />
                  ) : (
                    <Chip
                      label="N/A"
                      size="small"
                      color="default"
                      variant="outlined"
                    />
                  )}
                </TableCell>
              </TableRow>
            ))}
            
            {address.human_review && (
              <TableRow>
                <TableCell colSpan={3} sx={{ p: 2 }}>
                  <Alert 
                    severity="warning" 
                    sx={{ 
                      fontSize: '0.75rem',
                      '& .MuiAlert-message': { fontSize: '0.75rem' }
                    }}
                  >
                    이 주소는 사람의 검토가 필요합니다
                  </Alert>
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </TableContainer>
    </Paper>
  );
};
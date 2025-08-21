import React from 'react';
import {
  Card,
  CardContent,
  Button,
  Box,
  Typography,
  Divider,
} from '@mui/material';
import {
  Download,
  Visibility,
  GetApp,
} from '@mui/icons-material';
import { EditableContact } from '../types';

interface ActionButtonsProps {
  contacts: EditableContact[];
  hasResults: boolean;
  onDownloadCSV: () => void;
  onShowOCR: () => void;
}

export const ActionButtons: React.FC<ActionButtonsProps> = ({
  contacts,
  hasResults,
  onDownloadCSV,
  onShowOCR,
}) => {
  if (!hasResults) {
    return null;
  }

  return (
    <Card>
      <CardContent sx={{ p: 3 }}>
        <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 3 }}>
          <GetApp sx={{ color: 'primary.main' }} />
          내보내기 & 보기
        </Typography>

        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
          {/* CSV Download */}
          <Button
            fullWidth
            variant="contained"
            startIcon={<Download />}
            onClick={onDownloadCSV}
            disabled={contacts.length === 0}
            sx={{ 
              py: 1.5,
              background: 'linear-gradient(135deg, #2c2c2c 0%, #1a1a1a 100%)',
              '&:hover': {
                background: 'linear-gradient(135deg, #1a1a1a 0%, #0d0d0d 100%)',
              }
            }}
          >
            CSV 파일 다운로드
          </Button>

          <Divider sx={{ my: 1 }} />

          {/* OCR Results */}
          <Button
            fullWidth
            variant="outlined"
            startIcon={<Visibility />}
            onClick={onShowOCR}
            sx={{ 
              py: 1.5,
              borderColor: 'grey.300',
              color: 'text.primary',
              '&:hover': {
                borderColor: 'primary.main',
                bgcolor: 'grey.50',
              }
            }}
          >
            원본 OCR 결과 보기
          </Button>

          {/* Export Summary */}
          <Box sx={{ mt: 2, p: 2, bgcolor: 'grey.50', borderRadius: 2 }}>
            <Typography variant="body2" color="text.secondary" gutterBottom>
              내보내기 정보
            </Typography>
            <Typography variant="body2">
              • 총 {contacts.length}개 연락처
            </Typography>
            <Typography variant="body2">
              • 검토 필요: {contacts.filter(c => c.needsReview).length}개
            </Typography>
            <Typography variant="body2">
              • 형식: CSV (Excel 호환)
            </Typography>
          </Box>
        </Box>
      </CardContent>
    </Card>
  );
};
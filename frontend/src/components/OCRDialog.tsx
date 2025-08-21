import React from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Typography,
  Paper,
  IconButton,
  Box,
} from '@mui/material';
import {
  Close,
  TextFields,
} from '@mui/icons-material';

interface OCRDialogProps {
  open: boolean;
  rawOcrText: string;
  onClose: () => void;
}

export const OCRDialog: React.FC<OCRDialogProps> = ({
  open,
  rawOcrText,
  onClose,
}) => {
  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="md"
      fullWidth
      PaperProps={{
        sx: {
          borderRadius: 3,
          maxHeight: '80vh',
        }
      }}
    >
      <DialogTitle sx={{ pb: 1 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <TextFields sx={{ color: 'primary.main' }} />
          <Typography variant="h6" component="span">
            원본 OCR 결과
          </Typography>
        </Box>
        <IconButton
          onClick={onClose}
          sx={{ 
            position: 'absolute', 
            right: 8, 
            top: 8,
            color: 'grey.500'
          }}
        >
          <Close />
        </IconButton>
      </DialogTitle>
      
      <DialogContent sx={{ px: 3 }}>
        <Paper 
          sx={{ 
            p: 3, 
            bgcolor: 'grey.50',
            border: '1px solid',
            borderColor: 'grey.200',
            borderRadius: 2,
            maxHeight: '50vh',
            overflow: 'auto'
          }}
        >
          <Typography 
            variant="body2" 
            component="pre"
            sx={{ 
              fontFamily: '"Fira Code", "Monaco", "Cascadia Code", monospace',
              whiteSpace: 'pre-wrap',
              wordBreak: 'break-word',
              fontSize: '0.875rem',
              lineHeight: 1.6,
              color: 'text.primary',
              margin: 0
            }}
          >
            {rawOcrText || 'OCR 텍스트를 사용할 수 없습니다.'}
          </Typography>
        </Paper>
        
        <Box sx={{ mt: 2, p: 2, bgcolor: 'info.50', borderRadius: 2 }}>
          <Typography variant="body2" color="info.main">
            💡 이 텍스트는 AI가 이미지에서 추출한 원본 OCR 결과입니다. 
            실제 연락처 추출 과정에서는 이 텍스트를 분석하여 구조화된 정보로 변환합니다.
          </Typography>
        </Box>
      </DialogContent>
      
      <DialogActions sx={{ px: 3, pb: 3 }}>
        <Button 
          onClick={onClose} 
          variant="contained"
          sx={{ 
            px: 3,
            background: 'linear-gradient(135deg, #2c2c2c 0%, #1a1a1a 100%)',
            '&:hover': {
              background: 'linear-gradient(135deg, #1a1a1a 0%, #0d0d0d 100%)',
            }
          }}
        >
          닫기
        </Button>
      </DialogActions>
    </Dialog>
  );
};
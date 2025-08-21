import React, { useRef, useCallback } from 'react';
import {
  Box,
  Typography,
  Button,
  Paper,
  Card,
  CardContent,
  CircularProgress,
} from '@mui/material';
import {
  CloudUpload,
  CameraAlt,
} from '@mui/icons-material';
import { useDropzone } from 'react-dropzone';
import Webcam from 'react-webcam';

interface UploadSectionProps {
  selectedImage: string | null;
  showCamera: boolean;
  loading: boolean;
  onImageSelect: (image: string) => void;
  onToggleCamera: () => void;
  onProcessImage: () => void;
}

export const UploadSection: React.FC<UploadSectionProps> = ({
  selectedImage,
  showCamera,
  loading,
  onImageSelect,
  onToggleCamera,
  onProcessImage,
}) => {
  const webcamRef = useRef<Webcam>(null);

  const onDrop = useCallback((acceptedFiles: File[]) => {
    const file = acceptedFiles[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = () => {
        onImageSelect(reader.result as string);
      };
      reader.readAsDataURL(file);
    }
  }, [onImageSelect]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'image/*': ['.jpeg', '.jpg', '.png'] },
    maxSize: 10 * 1024 * 1024,
    multiple: false
  });

  const captureImage = useCallback(() => {
    const imageSrc = webcamRef.current?.getScreenshot();
    if (imageSrc) {
      onImageSelect(imageSrc);
    }
  }, [onImageSelect]);

  return (
    <Card sx={{ height: 'fit-content' }}>
      <CardContent sx={{ p: 3 }}>
        <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 3 }}>
          <CloudUpload sx={{ color: 'primary.main' }} />
          이미지 업로드
        </Typography>
        
        {/* Upload Area */}
        <Paper
          {...getRootProps()}
          sx={{
            p: 2,
            mb: 2,
            border: '2px dashed',
            borderColor: isDragActive ? 'primary.main' : 'grey.300',
            bgcolor: isDragActive ? 'primary.light' : 'transparent',
            cursor: 'pointer',
            textAlign: 'center',
            transition: 'all 0.3s ease',
            borderRadius: 2,
            '&:hover': {
              borderColor: 'primary.main',
              bgcolor: 'grey.50',
            }
          }}
        >
          <input {...getInputProps()} />
          <CloudUpload sx={{ fontSize: 32, color: 'grey.400', mb: 1 }} />
          <Typography variant="body2" color="text.secondary" gutterBottom>
            {isDragActive ? '파일을 여기에 놓으세요' : '클릭하거나 파일을 드래그하세요'}
          </Typography>
          <Typography variant="caption" color="text.secondary">
            JPG, PNG (최대 10MB)
          </Typography>
        </Paper>

        {/* Camera Button */}
        <Button
          fullWidth
          variant="outlined"
          startIcon={<CameraAlt />}
          onClick={onToggleCamera}
          sx={{ mb: 2 }}
        >
          카메라 사용
        </Button>

        {/* Camera */}
        {showCamera && (
          <Box sx={{ mb: 2 }}>
            <Webcam
              ref={webcamRef}
              screenshotFormat="image/jpeg"
              style={{ width: '100%', borderRadius: 8 }}
            />
            <Button
              fullWidth
              variant="contained"
              onClick={captureImage}
              sx={{ mt: 1 }}
            >
              사진 촬영
            </Button>
          </Box>
        )}

        {/* Selected Image Preview */}
        {selectedImage && (
          <Box sx={{ mb: 2 }}>
            <Typography variant="subtitle2" gutterBottom color="text.secondary">
              선택된 이미지:
            </Typography>
            <Paper sx={{ p: 1, borderRadius: 2 }}>
              <img
                src={selectedImage}
                alt="Selected"
                style={{ 
                  width: '100%', 
                  borderRadius: 8, 
                  maxHeight: 200, 
                  objectFit: 'cover' 
                }}
              />
            </Paper>
          </Box>
        )}

        {/* Process Button */}
        {selectedImage && (
          <Button
            fullWidth
            variant="contained"
            onClick={onProcessImage}
            disabled={loading}
            size="large"
            sx={{ 
              py: 1.5,
              background: loading ? undefined : 'linear-gradient(135deg, #2c2c2c 0%, #1a1a1a 100%)',
              '&:hover': {
                background: loading ? undefined : 'linear-gradient(135deg, #1a1a1a 0%, #0d0d0d 100%)',
              }
            }}
          >
            {loading ? (
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, color: 'white' }}>
                <CircularProgress size={20} sx={{ color: 'white' }} />
                처리 중...
              </Box>
            ) : (
              'AI로 연락처 추출하기'
            )}
          </Button>
        )}
      </CardContent>
    </Card>
  );
};
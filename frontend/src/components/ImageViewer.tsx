import React, { useRef, useState } from 'react';
import {
  Card,
  CardContent,
  Typography,
  Paper,
  Box,
  IconButton,
  Tooltip,
} from '@mui/material';
import {
  ZoomIn,
  ZoomOut,
  RestartAlt,
  Image as ImageIcon,
} from '@mui/icons-material';

interface ImageViewerProps {
  selectedImage: string;
  sidebarOpen: boolean;
  containerWidth?: number; // Percentage width of container
}

export const ImageViewer: React.FC<ImageViewerProps> = ({
  selectedImage,
  sidebarOpen,
  containerWidth = 50,
}) => {
  const imageRef = useRef<HTMLImageElement>(null);
  const [imageZoom, setImageZoom] = useState(1);
  const [imagePosition, setImagePosition] = useState({ x: 0, y: 0 });
  const [showMagnifier, setShowMagnifier] = useState(false);
  const [magnifierPos, setMagnifierPos] = useState({ x: 0, y: 0 });

  const handleImageMouseMove = (e: React.MouseEvent<HTMLImageElement>) => {
    if (!imageRef.current) return;
    
    const rect = imageRef.current.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    
    setMagnifierPos({ x: e.clientX, y: e.clientY });
    setImagePosition({ x, y });
  };

  return (
    <Card sx={{ height: 'fit-content' }}>
      <CardContent sx={{ p: 3 }}>
        <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 3 }}>
          <ImageIcon sx={{ color: 'primary.main' }} />
          이미지 뷰어
        </Typography>
        
        <Paper 
          sx={{ 
            p: 2, 
            position: 'relative', 
            overflow: 'auto', // Changed from hidden to auto for zoomed images
            borderRadius: 2,
            bgcolor: 'grey.50',
            minHeight: Math.min(400, window.innerHeight * 0.5),
            maxHeight: Math.min(800, window.innerHeight * 0.8),
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center'
          }}
        >
          <img
            ref={imageRef}
            src={selectedImage}
            alt="Processing"
            style={{
              width: '100%',
              maxHeight: Math.min(700, window.innerHeight * 0.7),
              objectFit: 'contain',
              transform: `scale(${imageZoom})`,
              cursor: imageZoom === 1 ? 'zoom-in' : 'zoom-out',
              borderRadius: 8,
              transition: 'transform 0.2s ease',
            }}
            onMouseMove={handleImageMouseMove}
            onMouseEnter={() => setShowMagnifier(true)}
            onMouseLeave={() => setShowMagnifier(false)}
            onClick={() => setImageZoom(imageZoom === 1 ? 2 : 1)}
          />
          
          {/* Zoom Controls */}
          <Box sx={{ 
            position: 'absolute', 
            top: 8, 
            right: 8, 
            display: 'flex', 
            flexDirection: 'column', 
            gap: 1 
          }}>
            <Tooltip title="확대 (최대 300%)" placement="left">
              <span>
                <IconButton 
                  size="small" 
                  onClick={() => setImageZoom(Math.min(3, imageZoom + 0.5))}
                  disabled={imageZoom >= 3}
                  sx={{ 
                    bgcolor: 'rgba(255,255,255,0.9)',
                    boxShadow: 1,
                    '&:hover': { bgcolor: 'rgba(255,255,255,1)' }
                  }}
                >
                  <ZoomIn />
                </IconButton>
              </span>
            </Tooltip>
            <Tooltip title="축소 (최소 50%)" placement="left">
              <span>
                <IconButton 
                  size="small" 
                  onClick={() => setImageZoom(Math.max(0.5, imageZoom - 0.5))}
                  disabled={imageZoom <= 0.5}
                  sx={{ 
                    bgcolor: 'rgba(255,255,255,0.9)',
                    boxShadow: 1,
                    '&:hover': { bgcolor: 'rgba(255,255,255,1)' }
                  }}
                >
                  <ZoomOut />
                </IconButton>
              </span>
            </Tooltip>
            <Tooltip title="100% 크기로 재설정" placement="left">
              <span>
                <IconButton 
                  size="small" 
                  onClick={() => setImageZoom(1)}
                  disabled={imageZoom === 1}
                  sx={{ 
                    bgcolor: 'rgba(255,255,255,0.9)',
                    boxShadow: 1,
                    '&:hover': { bgcolor: 'rgba(255,255,255,1)' }
                  }}
                >
                  <RestartAlt />
                </IconButton>
              </span>
            </Tooltip>
          </Box>

          {/* Zoom Level Indicator */}
          {imageZoom !== 1 && (
            <Box 
              sx={{ 
                position: 'absolute', 
                bottom: 8, 
                left: 8,
                bgcolor: 'rgba(0,0,0,0.7)',
                color: 'white',
                px: 1,
                py: 0.5,
                borderRadius: 1,
                fontSize: '0.75rem'
              }}
            >
              {Math.round(imageZoom * 100)}%
            </Box>
          )}
        </Paper>

        {/* Magnifier */}
        {showMagnifier && (
          <Box
            sx={{
              position: 'fixed',
              width: 150,
              height: 150,
              border: '3px solid #fff',
              borderRadius: '50%',
              background: `url(${selectedImage})`,
              backgroundSize: `${imageZoom * 300}%`,
              backgroundPosition: `-${imagePosition.x * imageZoom * 2}px -${imagePosition.y * imageZoom * 2}px`,
              pointerEvents: 'none',
              zIndex: 1000,
              boxShadow: '0 4px 20px rgba(0,0,0,0.3)',
              left: magnifierPos.x + 10,
              top: magnifierPos.y - 75,
            }}
          />
        )}
      </CardContent>
    </Card>
  );
};
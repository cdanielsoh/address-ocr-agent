import React, { useState } from 'react';
import {
  Box,
  Container,
  Typography,
  AppBar,
  Toolbar,
  IconButton,
  Alert,
  Fade,
  Drawer,
} from '@mui/material';
import {
  Menu,
  ChevronLeft,
  ContactPage,
} from '@mui/icons-material';
import { ThemeProvider } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import axios from 'axios';

// Import components
import { UploadSection } from './components/UploadSection';
import { ResultsSummary } from './components/ResultsSummary';
import { ContactsTable } from './components/ContactsTable';
import { ImageViewer } from './components/ImageViewer';
import { ActionButtons } from './components/ActionButtons';
import { OCRDialog } from './components/OCRDialog';

// Import types and theme
import { EditableContact, MultiEntryResult } from './types';
import { theme } from './theme';

const SIDEBAR_WIDTH = 320;

function App() {
  // States
  const [selectedImage, setSelectedImage] = useState<string | null>(null);
  const [showCamera, setShowCamera] = useState(false);
  const [multiEntryResult, setMultiEntryResult] = useState<MultiEntryResult | null>(null);
  const [contacts, setContacts] = useState<EditableContact[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [ocrDialogOpen, setOcrDialogOpen] = useState(false);
  const [rawOcrText, setRawOcrText] = useState<string>('');
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [tableWidthRatio, setTableWidthRatio] = useState(65); // Percentage for table width
  const [responseTime, setResponseTime] = useState<number | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [dragStartX, setDragStartX] = useState(0);
  const [dragStartRatio, setDragStartRatio] = useState(0);

  // Helper functions
  const formatAddressComponent = (value: string | null, suffix: string): string | null => {
    if (!value) return null;
    // Check if the suffix is already present
    if (value.endsWith(suffix)) {
      return value;
    }
    return `${value}${suffix}`;
  };

  const formatAddress = (address: any): string => {
    if (!address) return '';
    const parts = [
      address.sido,
      address.sigungu,
      address.road_name,
      address.building_number,
      formatAddressComponent(address.dong, '동'),
      formatAddressComponent(address.ho, '호'),
      formatAddressComponent(address.legal_dong, '동'),
      address.building_name,
      formatAddressComponent(address.floor, '층')
    ].filter(Boolean);
    return parts.join(' ');
  };

  const calculateAverageConfidence = (confidence: { [key: string]: number }): number => {
    const values = Object.values(confidence).filter(v => typeof v === 'number');
    return values.length > 0 ? values.reduce((a, b) => a + b, 0) / values.length : 0;
  };

  // Image handling
  const handleImageSelect = (image: string) => {
    setSelectedImage(image);
    setShowCamera(false);
    setContacts([]);
    setMultiEntryResult(null);
    setError(null);
  };

  const handleToggleCamera = () => {
    setShowCamera(!showCamera);
  };

  // Process image
  const processImage = async () => {
    if (!selectedImage) return;

    setLoading(true);
    setError(null);
    setResponseTime(null);
    const startTime = performance.now();

    try {
      const response = await fetch(selectedImage);
      const blob = await response.blob();
      
      const formData = new FormData();
      formData.append('image', blob, 'image.jpg');

      const apiResponse = await axios.post('/api/extract-multiple-entries', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });

      const endTime = performance.now();
      const processingTime = endTime - startTime;
      setResponseTime(processingTime);

      const result: MultiEntryResult = apiResponse.data;
      setMultiEntryResult(result);
      
      // Store raw OCR text from metadata if available  
      setRawOcrText(result.processing_metadata?.raw_text || 'OCR 텍스트를 사용할 수 없습니다.');

      // Convert to editable format
      const editableContacts: EditableContact[] = result.entries.map((entry, index) => ({
        id: entry.entry_number || index + 1,
        name: entry.name || '',
        phone: entry.phone_number || '',
        address: formatAddress(entry.address),
        isEditing: false,
        needsReview: entry.human_review,
        confidence: calculateAverageConfidence(entry.confidence)
      }));

      setContacts(editableContacts);

    } catch (err: any) {
      setError(err.response?.data?.detail || 'Processing failed');
    } finally {
      setLoading(false);
    }
  };

  // Contact editing
  const handleUpdateContact = (id: number, field: 'name' | 'phone' | 'address', value: string) => {
    setContacts(prev => prev.map(contact => 
      contact.id === id ? { ...contact, [field]: value } : contact
    ));
  };

  // CSV Download
  const downloadCSV = () => {
    if (contacts.length === 0) return;
    
    const headers = ['이름', '전화번호', '주소', '검토필요', '신뢰도'];
    const csvContent = [
      headers.join(','),
      ...contacts.map(contact => [
        `"${contact.name}"`,
        `"${contact.phone}"`,
        `"${contact.address}"`,
        contact.needsReview ? '예' : '아니오',
        `${(contact.confidence * 100).toFixed(1)}%`
      ].join(','))
    ].join('\n');

    // Add BOM (Byte Order Mark) for proper UTF-8 encoding
    const BOM = '\uFEFF';
    const csvWithBOM = BOM + csvContent;

    const blob = new Blob([csvWithBOM], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `contacts_${new Date().toISOString().split('T')[0]}.csv`;
    link.click();
  };

  const needsReviewCount = contacts.filter(c => c.needsReview).length;

  // Drag handlers for resizable divider
  const handleMouseDown = (e: React.MouseEvent) => {
    if (!selectedImage) return;
    setIsDragging(true);
    setDragStartX(e.clientX);
    setDragStartRatio(tableWidthRatio);
    e.preventDefault();
  };

  const handleMouseMove = (e: MouseEvent) => {
    if (!isDragging || !selectedImage) return;
    
    const containerWidth = window.innerWidth - (sidebarOpen ? SIDEBAR_WIDTH : 0) - 48; // Account for padding
    const deltaX = e.clientX - dragStartX;
    const deltaPercent = (deltaX / containerWidth) * 100;
    const newRatio = Math.min(80, Math.max(30, dragStartRatio + deltaPercent));
    
    setTableWidthRatio(newRatio);
  };

  const handleMouseUp = () => {
    setIsDragging(false);
  };

  // Add global mouse event listeners for dragging
  React.useEffect(() => {
    if (isDragging) {
      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
      document.body.style.cursor = 'col-resize';
      document.body.style.userSelect = 'none';
      
      return () => {
        document.removeEventListener('mousemove', handleMouseMove);
        document.removeEventListener('mouseup', handleMouseUp);
        document.body.style.cursor = '';
        document.body.style.userSelect = '';
      };
    }
  }, [isDragging, dragStartX, dragStartRatio, tableWidthRatio, selectedImage, sidebarOpen]);

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Box sx={{ display: 'flex', minHeight: '100vh', bgcolor: 'background.default' }}>
        {/* App Bar */}
        <AppBar 
          position="fixed" 
          sx={{ 
            zIndex: 1300,
            bgcolor: 'background.paper',
            color: 'text.primary',
            boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)',
            borderBottom: '1px solid',
            borderColor: 'grey.200'
          }}
        >
          <Toolbar>
            <IconButton
              color="inherit"
              onClick={() => setSidebarOpen(!sidebarOpen)}
              edge="start"
              sx={{ mr: 2 }}
            >
              {sidebarOpen ? <ChevronLeft /> : <Menu />}
            </IconButton>
            <ContactPage sx={{ mr: 1, color: 'primary.main' }} />
            <Typography variant="h6" sx={{ flexGrow: 1, fontWeight: 600 }}>
              연락처 추출 시스템
            </Typography>
          </Toolbar>
        </AppBar>

        {/* Sidebar */}
        <Drawer
          variant="persistent"
          open={sidebarOpen}
          sx={{
            width: sidebarOpen ? SIDEBAR_WIDTH : 0,
            '& .MuiDrawer-paper': {
              width: SIDEBAR_WIDTH,
              boxSizing: 'border-box',
              mt: 8,
              bgcolor: 'background.paper',
              borderRight: '1px solid',
              borderColor: 'grey.200',
              transition: 'width 0.3s ease'
            }
          }}
        >
          <Container sx={{ p: 3, height: '100%', overflow: 'auto' }}>
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
              <UploadSection
                selectedImage={selectedImage}
                showCamera={showCamera}
                loading={loading}
                onImageSelect={handleImageSelect}
                onToggleCamera={handleToggleCamera}
                onProcessImage={processImage}
              />
              
              {multiEntryResult && (
                <ResultsSummary
                  totalEntries={multiEntryResult.total_entries}
                  needsReview={needsReviewCount}
                  processing={loading}
                  responseTime={responseTime}
                />
              )}

              {contacts.length > 0 && (
                <ActionButtons
                  contacts={contacts}
                  hasResults={!!multiEntryResult}
                  onDownloadCSV={downloadCSV}
                  onShowOCR={() => setOcrDialogOpen(true)}
                />
              )}
            </Box>
          </Container>
        </Drawer>

        {/* Main Content */}
        <Box 
          component="main" 
          sx={{ 
            flexGrow: 1, 
            mt: 8,
            minHeight: 'calc(100vh - 64px)',
            bgcolor: 'background.default'
          }}
        >
          <Container maxWidth={false} sx={{ p: 3, height: '100%' }}>
            {/* Error Alert */}
            {error && (
              <Fade in={!!error}>
                <Alert 
                  severity="error" 
                  onClose={() => setError(null)}
                  sx={{ mb: 3, borderRadius: 2 }}
                >
                  {error}
                </Alert>
              </Fade>
            )}

            <Box sx={{ display: 'flex', height: '100%', position: 'relative' }}>
              {/* Contacts Table */}
              <Box sx={{ 
                flex: selectedImage ? `0 0 ${tableWidthRatio}%` : 1,
                minWidth: 0, // Allow shrinking below content size
                pr: selectedImage ? 1 : 0 // Add padding when image is present
              }}>
                <ContactsTable
                  contacts={contacts}
                  multiEntryResult={multiEntryResult}
                  onUpdateContact={handleUpdateContact}
                />
              </Box>

              {/* Draggable Divider */}
              {selectedImage && (
                <Box
                  onMouseDown={handleMouseDown}
                  sx={{
                    width: 16,
                    cursor: 'col-resize',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    bgcolor: 'transparent',
                    position: 'relative',
                    minHeight: '100%',
                    alignSelf: 'stretch',
                    '&:hover': {
                      bgcolor: 'grey.100',
                    },
                    '&:hover::before': {
                      content: '""',
                      position: 'absolute',
                      width: 3,
                      height: '90%',
                      bgcolor: 'primary.main',
                      borderRadius: 1,
                    }
                  }}
                />
              )}

              {/* Image Viewer */}
              {selectedImage && (
                <Box sx={{ 
                  flex: `0 0 ${100 - tableWidthRatio}%`,
                  minWidth: 0, // Allow shrinking below content size
                  pl: 1 // Add padding from divider
                }}>
                  <ImageViewer
                    selectedImage={selectedImage}
                    sidebarOpen={sidebarOpen}
                    containerWidth={100 - tableWidthRatio}
                  />
                </Box>
              )}
            </Box>
          </Container>
        </Box>

        {/* OCR Results Dialog */}
        <OCRDialog
          open={ocrDialogOpen}
          rawOcrText={rawOcrText}
          onClose={() => setOcrDialogOpen(false)}
        />
      </Box>
    </ThemeProvider>
  );
}

export default App;
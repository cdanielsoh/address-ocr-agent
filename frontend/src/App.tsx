import React, { useState, useRef, useCallback } from 'react';
import {
  Container,
  Paper,
  Typography,
  Button,
  Box,
  Card,
  CardContent,
  CardHeader,
  CircularProgress,
  Chip,
  Alert
} from '@mui/material';
import { CameraAlt, Upload, CloudUpload } from '@mui/icons-material';
import { useDropzone } from 'react-dropzone';
import Webcam from 'react-webcam';
import axios from 'axios';

interface AddressResult {
  sido: string | null;
  sigungu: string | null;
  road_name: string | null;
  building_number: string | null;
  dong: string | null;
  ho: string | null;
  legal_dong: string | null;
  building_name: string | null;
  floor: string | null;
  room_number: string | null;
  confidence: { [key: string]: number };
  human_review: boolean;
}

interface RawOCRResult {
  extracted_text: string;
  confidence: number;
  is_raw_text: boolean;
}

interface ComparisonResult {
  imageId: string;
  upstage_result: RawOCRResult;
  agent_result: AddressResult;
  processingTime: number;
}


function App() {
  const [selectedImage, setSelectedImage] = useState<string | null>(null);
  const [showCamera, setShowCamera] = useState(false);
  const [comparisonResult, setComparisonResult] = useState<ComparisonResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const webcamRef = useRef<Webcam>(null);

  const onDrop = useCallback((acceptedFiles: File[]) => {
    console.log('📁 [FRONTEND] File(s) dropped/selected:', acceptedFiles.length);
    const file = acceptedFiles[0];
    if (file) {
      console.log('📄 [FRONTEND] Processing file:', {
        name: file.name,
        size: file.size,
        type: file.type,
        lastModified: new Date(file.lastModified).toISOString()
      });
      const reader = new FileReader();
      reader.onload = () => {
        console.log('✅ [FRONTEND] File successfully read as data URL');
        setSelectedImage(reader.result as string);
        setShowCamera(false);
      };
      reader.onerror = () => {
        console.error('❌ [FRONTEND] Failed to read file');
      };
      reader.readAsDataURL(file);
    } else {
      console.warn('⚠️ [FRONTEND] No file selected');
    }
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'image/*': ['.jpeg', '.jpg', '.png']
    },
    maxSize: 10 * 1024 * 1024 // 10MB
  });

  const capture = useCallback(() => {
    console.log('📷 [FRONTEND] Starting camera capture');
    const imageSrc = webcamRef.current?.getScreenshot();
    if (imageSrc) {
      console.log('✅ [FRONTEND] Camera capture successful - Image captured');
      setSelectedImage(imageSrc);
      setShowCamera(false);
      console.log('🔄 [FRONTEND] Camera closed, image ready for processing');
    } else {
      console.error('❌ [FRONTEND] Camera capture failed - No image captured');
    }
  }, [webcamRef]);

  const processImage = async () => {
    if (!selectedImage) return;

    console.log('🚀 [FRONTEND] Starting address extraction enhancement process');
    setLoading(true);
    setError(null);

    const startTime = Date.now();

    try {
      console.log('📷 [FRONTEND] Converting base64 image to blob');
      const response = await fetch(selectedImage);
      const blob = await response.blob();
      console.log(`✅ [FRONTEND] Image converted to blob - Size: ${blob.size} bytes, Type: ${blob.type}`);
      
      const formData = new FormData();
      formData.append('image', blob, 'image.jpg');
      console.log('📦 [FRONTEND] FormData prepared for API call');

      console.log('🌐 [FRONTEND] Calling compare-address-extraction API endpoint');
      const apiResponse = await axios.post('/api/compare-address-extraction', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        onUploadProgress: (progressEvent) => {
          const percentCompleted = Math.round((progressEvent.loaded * 100) / (progressEvent.total || 1));
          console.log(`📤 [FRONTEND] Upload progress: ${percentCompleted}%`);
        },
      });

      const processingTime = Date.now() - startTime;
      console.log(`✅ [FRONTEND] API call completed successfully in ${processingTime}ms`);
      console.log('📊 [FRONTEND] Enhancement result received:', {
        imageId: apiResponse.data.imageId,
        upstageConfidence: apiResponse.data.upstage_result?.confidence,
        agentConfidences: apiResponse.data.agent_result?.confidence,
        humanReviewRequired: apiResponse.data.agent_result?.human_review,
        agentAvgConfidence: apiResponse.data.agent_result ? getAverageConfidence(apiResponse.data.agent_result.confidence) : null,
        serverProcessingTime: apiResponse.data.processingTime,
        clientTotalTime: processingTime
      });

      setComparisonResult(apiResponse.data);

      // Log the formatted addresses
      if (apiResponse.data.upstage_result) {
        console.log(`🔍 [FRONTEND] Original OCR: "${apiResponse.data.upstage_result.extracted_text}" (confidence: ${(apiResponse.data.upstage_result.confidence * 100).toFixed(1)}%)`);
      }

      if (apiResponse.data.agent_result) {
        const agentFormatted = formatAddressResult(apiResponse.data.agent_result);
        const avgConfidence = getAverageConfidence(apiResponse.data.agent_result.confidence);
        console.log(`🧠 [FRONTEND] AI enhanced: "${agentFormatted}" (avg confidence: ${(avgConfidence * 100).toFixed(1)}%, human review: ${apiResponse.data.agent_result.human_review})`);
        console.log('🎯 [FRONTEND] Individual component confidences:', apiResponse.data.agent_result.confidence);
      }

    } catch (err: any) {
      const processingTime = Date.now() - startTime;
      console.error(`❌ [FRONTEND] API call failed after ${processingTime}ms:`, err);
      console.error('📋 [FRONTEND] Error details:', {
        status: err.response?.status,
        statusText: err.response?.statusText,
        data: err.response?.data,
        message: err.message
      });
      
      setError(err.response?.data?.detail || err.response?.data?.message || 'An error occurred during processing');
    } finally {
      setLoading(false);
      const totalTime = Date.now() - startTime;
      console.log(`⏱️ [FRONTEND] Total processing time: ${totalTime}ms`);
    }
  };

  const getConfidenceColor = (score: number) => {
    if (score >= 0.8) return 'success';
    if (score >= 0.6) return 'warning';
    return 'error';
  };

  const getConfidenceText = (score: number) => {
    if (score >= 0.8) return '높음';
    if (score >= 0.6) return '보통';
    return '낮음';
  };

  const formatAddressResult = (result: AddressResult): string => {
    const parts: string[] = [];
    
    if (result.sido) parts.push(result.sido);
    if (result.sigungu) parts.push(result.sigungu);
    if (result.road_name) parts.push(result.road_name);
    if (result.building_number) parts.push(result.building_number);
    if (result.dong) parts.push(result.dong);
    if (result.ho) parts.push(result.ho);
    if (result.floor) parts.push(result.floor);
    if (result.room_number) parts.push(result.room_number);
    
    return parts.length > 0 ? parts.join(' ') : '주소 구성 요소를 찾을 수 없습니다';
  };

  const getAverageConfidence = (confidence: { [key: string]: number }): number => {
    const values = Object.values(confidence);
    return values.length > 0 ? values.reduce((a, b) => a + b, 0) / values.length : 0;
  };

  const RawOCRResultCard: React.FC<{ title: string; result: RawOCRResult }> = ({ title, result }) => (
    <Card sx={{ mb: 3, border: '1px solid #e9ecef', borderRadius: 2, mx: { xs: 0, md: 0 } }}>
      <CardHeader 
        title={title}
        sx={{ bgcolor: '#f8f9fa', py: 2 }}
        titleTypographyProps={{ variant: 'subtitle1', fontWeight: 600 }}
      />
      <CardContent>
        <Typography 
          variant="h6"
          gutterBottom 
          sx={{ 
            fontFamily: 'monospace', 
            bgcolor: '#f5f5f5', 
            p: { xs: 1.5, md: 2 }, 
            borderRadius: 1, 
            wordBreak: 'break-word',
            fontSize: { xs: '1rem', md: '1.25rem' }
          }}>
          "{result.extracted_text}"
        </Typography>
        <Chip
          label={`신뢰도: ${(result.confidence * 100).toFixed(1)}% (${getConfidenceText(result.confidence)})`}
          color={getConfidenceColor(result.confidence)}
          size="small"
        />
      </CardContent>
    </Card>
  );

  const AddressResultCard: React.FC<{ title: string; result: AddressResult }> = ({ title, result }) => (
    <Card sx={{ mb: 3, border: '2px solid #e3f2fd', borderRadius: 2, mx: { xs: 0, md: 0 } }}>
      <CardHeader 
        title={title}
        sx={{ bgcolor: '#e3f2fd', py: 2 }}
        titleTypographyProps={{ variant: 'subtitle1', fontWeight: 600, color: 'primary.dark' }}
      />
      <CardContent>
        <Box sx={{ mb: 3 }}>
          <Typography 
            variant="h6"
            gutterBottom 
            sx={{ 
              color: 'primary.main', 
              fontWeight: 600, 
              wordBreak: 'break-word',
              fontSize: { xs: '1rem', md: '1.25rem' }
            }}>
            {formatAddressResult(result)}
          </Typography>
          <Box sx={{ display: 'flex', gap: 1, mb: 2, flexWrap: 'wrap', justifyContent: { xs: 'flex-start', md: 'flex-start' } }}>
            {result.human_review && (
              <Chip
                label="⚠️ 사람 검토 필요"
                color="warning"
                variant="outlined"
                size="small"
                sx={{ fontWeight: 'bold' }}
              />
            )}
          </Box>
        </Box>

        <Typography variant="subtitle2" gutterBottom sx={{ fontWeight: 600 }}>
          주소 구성 요소:
        </Typography>
        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, justifyContent: { xs: 'flex-start', md: 'flex-start' } }}>
          {[
            { key: 'sido', label: '시도', value: result.sido },
            { key: 'sigungu', label: '시군구', value: result.sigungu },
            { key: 'road_name', label: '도로명', value: result.road_name },
            { key: 'building_number', label: '건물번호', value: result.building_number },
            { key: 'dong', label: '동', value: result.dong },
            { key: 'ho', label: '호', value: result.ho },
            { key: 'floor', label: '층', value: result.floor },
            { key: 'room_number', label: '호실', value: result.room_number },
            { key: 'legal_dong', label: '법정동', value: result.legal_dong },
            { key: 'building_name', label: '건물명', value: result.building_name },
          ].map(({ key, label, value }) => {
            const confidence = result.confidence[key];
            return value && (
              <Box key={key} sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                <Chip
                  label={`${label}: ${value}`}
                  size="small"
                  variant="outlined"
                  color="primary"
                />
                {confidence !== undefined && (
                  <Chip
                    label={`${(confidence * 100).toFixed(1)}%`}
                    size="small"
                    color={getConfidenceColor(confidence)}
                    sx={{ fontSize: '0.7rem', height: '20px' }}
                  />
                )}
              </Box>
            );
          })}
        </Box>
      </CardContent>
    </Card>
  );

  return (
    <Box sx={{ minHeight: '100vh', bgcolor: '#fafafa', display: 'flex', flexDirection: 'column' }}>
      {/* Header */}
      <Box sx={{ bgcolor: 'white', borderBottom: '1px solid #e0e0e0', px: 3, py: 2 }}>
        <Typography variant="h6" component="div" sx={{ fontWeight: 600 }}>
          한국 주소 AI 에이전트
          <Typography component="span" variant="caption" sx={{ ml: 2, color: 'text.secondary' }}>
            OCR 향상 및 검토 기능
          </Typography>
        </Typography>
      </Box>

      <Container maxWidth="xl" sx={{ flex: 1, py: 0, display: 'flex', flexDirection: { xs: 'column', md: 'row' } }}>
        {/* Left Sidebar - Image Input */}
        <Box sx={{ 
          width: { xs: '100%', md: '320px' },
          bgcolor: 'white',
          borderRight: { xs: 'none', md: '1px solid #e0e0e0' },
          borderBottom: { xs: '1px solid #e0e0e0', md: 'none' },
          p: { xs: 2, md: 3 },
          height: { xs: 'auto', md: 'calc(100vh - 80px)' },
          overflow: 'auto',
          minHeight: { xs: 'auto', md: 'calc(100vh - 80px)' }
        }}>
          <Typography variant="h6" gutterBottom sx={{ fontWeight: 600, mb: 3 }}>
            주소 이미지 업로드
          </Typography>
          
          <Box sx={{ mb: 2 }}>
            <Button
              variant="outlined"
              startIcon={<CameraAlt />}
              onClick={() => {
                const newCameraState = !showCamera;
                console.log(`📹 [FRONTEND] Camera ${newCameraState ? 'opened' : 'closed'}`);
                setShowCamera(newCameraState);
              }}
              sx={{ mr: 1, mb: 1 }}
              size="small"
            >
              Camera
            </Button>
            <Button
              variant="outlined"
              startIcon={<Upload />}
              onClick={() => {
                console.log('📤 [FRONTEND] Upload button clicked - Opening file dialog');
                (document.querySelector('input[type="file"]') as HTMLInputElement)?.click();
              }}
              size="small"
            >
              업로드
            </Button>
          </Box>

          {showCamera && (
            <Box sx={{ mb: 2 }}>
              <Webcam
                audio={false}
                ref={webcamRef}
                screenshotFormat="image/jpeg"
                width="100%"
              />
              <Button
                variant="contained"
                onClick={capture}
                sx={{ mt: 1 }}
                fullWidth
                size="small"
              >
                사진 촬영
              </Button>
            </Box>
          )}

          <Box
            {...getRootProps()}
            sx={{
              border: '2px dashed #ccc',
              borderRadius: 2,
              p: { xs: 3, md: 2 },
              textAlign: 'center',
              cursor: 'pointer',
              bgcolor: isDragActive ? 'action.hover' : 'transparent',
              mb: 2
            }}
          >
            <input {...getInputProps()} />
            <CloudUpload sx={{ fontSize: 40, color: 'text.secondary', mb: 1 }} />
            <Typography 
              variant="caption"
              display="block"
              sx={{ fontSize: { xs: '0.875rem', md: '0.75rem' } }}>
              {isDragActive
                ? '여기에 이미지를 놓으세요...'
                : '이미지를 드래그하여 놓거나 클릭하여 선택하세요'}
            </Typography>
          </Box>

          {selectedImage && (
            <Box>
              <img
                src={selectedImage}
                alt="Selected"
                style={{ width: '100%', maxHeight: 200, objectFit: 'contain', borderRadius: 8 }}
              />
              <Button
                variant="contained"
                color="primary"
                onClick={() => {
                  console.log('🎯 [FRONTEND] Enhance Address button clicked');
                  processImage();
                }}
                disabled={loading}
                fullWidth
                size="large"
                sx={{ 
                  mt: 2, 
                  py: 1.5,
                  borderRadius: 2,
                  textTransform: 'none',
                  fontWeight: 600
                }}
              >
                {loading ? (
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <CircularProgress size={20} color="inherit" />
                    <span>처리 중...</span>
                  </Box>
                ) : (
                  'AI로 주소 향상하기'
                )}
              </Button>
            </Box>
          )}
        </Box>

        {/* Main Content Area */}
        <Box sx={{ flex: 1, display: 'flex', flexDirection: 'column', minHeight: { xs: '50vh', md: 'auto' } }}>
          {!comparisonResult && !loading && (
            <Box sx={{ 
              flex: 1, 
              display: 'flex', 
              flexDirection: 'column', 
              justifyContent: 'center', 
              alignItems: 'center',
              textAlign: 'center',
              px: { xs: 2, md: 4 }
            }}>
              <Box sx={{ mb: 4 }}>
                <Typography 
                  variant="h4"
                  gutterBottom 
                  sx={{ 
                    fontWeight: 300, 
                    color: 'text.primary',
                    fontSize: { xs: '1.5rem', md: '2.125rem' }
                  }}>
                  한국 주소 AI 에이전트에 오신 것을 환영합니다!
                </Typography>
                <Typography 
                  variant="body1"
                  color="text.secondary" 
                  sx={{ 
                    maxWidth: 600, 
                    mx: 'auto', 
                    lineHeight: 1.6,
                    fontSize: { xs: '0.875rem', md: '1rem' }
                  }}>
                  AI 기반 주소 교정 및 검증으로 OCR 결과를 향상시키세요. 
                  한국 주소가 포함된 이미지를 업로드하시면, AI 에이전트가 OCR 출력을 
                  스마트 교정 및 품질 검토 표시로 향상시켜 드립니다.
                </Typography>
              </Box>
              
              <Box sx={{ mb: 4 }}>
                <Typography 
                  variant="h6"
                  gutterBottom 
                  sx={{ 
                    color: 'primary.main', 
                    fontWeight: 600,
                    fontSize: { xs: '1rem', md: '1.25rem' }
                  }}>
                  업로드 가능한 이미지:
                </Typography>
                <Box sx={{ textAlign: 'left', display: 'inline-block' }}>
                  <Typography variant="body2" sx={{ mb: 0.5, color: 'text.secondary' }}>• 주소가 포함된 문서 또는 양식</Typography>
                  <Typography variant="body2" sx={{ mb: 0.5, color: 'text.secondary' }}>• 주소가 적힌 우편 봉투</Typography>
                  <Typography variant="body2" sx={{ mb: 0.5, color: 'text.secondary' }}>• 위치 정보가 포함된 명함</Typography>
                  <Typography variant="body2" sx={{ color: 'text.secondary' }}>• 한국 주소가 포함된 모든 이미지</Typography>
                </Box>
              </Box>
            </Box>
          )}
          
          {(comparisonResult || loading) && (
            <Box sx={{ flex: 1, p: { xs: 2, md: 3 }, overflow: 'auto' }}>
              <Typography 
                variant="h5"
                gutterBottom 
                sx={{ 
                  fontWeight: 600, 
                  mb: 3,
                  fontSize: { xs: '1.25rem', md: '1.5rem' }
                }}>
                OCR 향상 결과
              </Typography>

              {error && (
                <Alert severity="error" sx={{ mb: 3 }}>
                  {error}
                </Alert>
              )}

              {comparisonResult && (
                <Box>
                  {/* Original OCR Section */}
                  <Box sx={{ mb: 4 }}>
                    <Typography variant="h6" gutterBottom sx={{ color: 'text.secondary', fontWeight: 500 }}>
                      원본 OCR 출력
                    </Typography>
                    <RawOCRResultCard 
                      title="원시 텍스트 추출"
                      result={comparisonResult.upstage_result}
                    />
                  </Box>

                  {/* Enhanced Results Section */}
                  <Box sx={{ mb: 4 }}>
                    <Typography variant="h6" gutterBottom sx={{ color: 'primary.main', fontWeight: 600 }}>
                      AI 향상 주소
                    </Typography>
                    <AddressResultCard 
                      title="스마트 교정 및 검증"
                      result={comparisonResult.agent_result}
                    />
                  </Box>

                  {/* Processing Info */}
                  <Card sx={{ bgcolor: '#f8f9fa', border: '1px solid #e9ecef' }}>
                    <CardContent sx={{ py: 2 }}>
                      <Box sx={{ display: 'flex', gap: { xs: 1, md: 2 }, flexWrap: 'wrap', alignItems: 'center', justifyContent: { xs: 'center', md: 'flex-start' } }}>
                        <Chip
                          label={`⏱️ ${comparisonResult.processingTime}ms`}
                          size="small"
                          variant="outlined"
                        />
                        <Chip
                          label={`🆔 ${comparisonResult.imageId.slice(0, 8)}...`}
                          size="small"
                          variant="outlined"
                        />
                      </Box>
                    </CardContent>
                  </Card>
                </Box>
              )}
            </Box>
          )}
        </Box>
      </Container>
    </Box>
  );
}

export default App;
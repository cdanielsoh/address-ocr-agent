import React from 'react';
import {
  Card,
  CardContent,
  Typography,
  Box,
  Chip,
  LinearProgress,
} from '@mui/material';
import {
  Assessment,
  CheckCircle,
  Warning,
  Group,
  Schedule,
} from '@mui/icons-material';

interface ResultsSummaryProps {
  totalEntries: number;
  needsReview: number;
  processing?: boolean;
  responseTime?: number | null;
}

export const ResultsSummary: React.FC<ResultsSummaryProps> = ({
  totalEntries,
  needsReview,
  processing = false,
  responseTime = null,
}) => {
  const formatResponseTime = (time: number): string => {
    if (time < 1000) {
      return `${Math.round(time)}ms`;
    } else {
      return `${(time / 1000).toFixed(1)}초`;
    }
  };

  const successRate = totalEntries > 0 ? ((totalEntries - needsReview) / totalEntries) * 100 : 0;

  return (
    <Card>
      <CardContent sx={{ p: 3 }}>
        <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 3 }}>
          <Assessment sx={{ color: 'primary.main' }} />
          추출 결과
        </Typography>

        {processing && (
          <Box sx={{ mb: 3 }}>
            <Typography variant="body2" color="text.secondary" gutterBottom>
              연락처를 추출하고 있습니다...
            </Typography>
            <LinearProgress sx={{ borderRadius: 1 }} />
          </Box>
        )}

        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
          {/* Total Entries */}
          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <Group sx={{ color: 'grey.600', fontSize: 20 }} />
              <Typography variant="body1" color="text.secondary">
                총 연락처
              </Typography>
            </Box>
            <Chip 
              label={totalEntries}
              color="primary"
              size="small"
              sx={{ fontWeight: 600 }}
            />
          </Box>

          {/* Success Rate */}
          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <CheckCircle sx={{ color: 'success.main', fontSize: 20 }} />
              <Typography variant="body1" color="text.secondary">
                처리 완료
              </Typography>
            </Box>
            <Chip 
              label={`${totalEntries - needsReview}개`}
              color="success"
              variant="outlined"
              size="small"
              sx={{ fontWeight: 600 }}
            />
          </Box>

          {/* Needs Review */}
          {needsReview > 0 && (
            <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <Warning sx={{ color: 'warning.main', fontSize: 20 }} />
                <Typography variant="body1" color="text.secondary">
                  검토 필요
                </Typography>
              </Box>
              <Chip 
                label={`${needsReview}개`}
                color="warning"
                variant="outlined"
                size="small"
                sx={{ fontWeight: 600 }}
              />
            </Box>
          )}

          {/* Response Time */}
          {responseTime !== null && (
            <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <Schedule sx={{ color: 'info.main', fontSize: 20 }} />
                <Typography variant="body1" color="text.secondary">
                  응답 시간
                </Typography>
              </Box>
              <Chip 
                label={formatResponseTime(responseTime)}
                color="default"
                variant="outlined"
                size="small"
                sx={{ fontWeight: 600 }}
              />
            </Box>
          )}

          {/* Success Rate Bar */}
          {totalEntries > 0 && (
            <Box sx={{ mt: 2 }}>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                <Typography variant="body2" color="text.secondary">
                  성공률
                </Typography>
                <Typography variant="body2" color="text.primary" fontWeight={600}>
                  {successRate.toFixed(1)}%
                </Typography>
              </Box>
              <LinearProgress 
                variant="determinate" 
                value={successRate}
                sx={{ 
                  height: 8, 
                  borderRadius: 4,
                  bgcolor: 'grey.200',
                  '& .MuiLinearProgress-bar': {
                    borderRadius: 4,
                    bgcolor: successRate >= 80 ? 'success.main' : successRate >= 60 ? 'warning.main' : 'error.main'
                  }
                }}
              />
            </Box>
          )}
        </Box>
      </CardContent>
    </Card>
  );
};
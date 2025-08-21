import React, { useState } from 'react';
import {
  Card,
  CardContent,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  IconButton,
  Chip,
  Box,
  Collapse,
  Tooltip,
} from '@mui/material';
import {
  Edit,
  Save,
  Cancel,
  ExpandMore,
  ExpandLess,
  Home,
  TableView,
} from '@mui/icons-material';
import { EditableContact, MultiEntryResult } from '../types';
import { AddressDetailsTable } from './AddressDetailsTable';

interface ContactsTableProps {
  contacts: EditableContact[];
  multiEntryResult: MultiEntryResult | null;
  onUpdateContact: (id: number, field: 'name' | 'phone' | 'address', value: string) => void;
}

export const ContactsTable: React.FC<ContactsTableProps> = ({
  contacts,
  multiEntryResult,
  onUpdateContact,
}) => {
  const [editingContact, setEditingContact] = useState<number | null>(null);
  const [expandedRows, setExpandedRows] = useState<Set<number>>(new Set());

  const startEditing = (id: number) => {
    setEditingContact(id);
  };

  const saveEdit = (id: number, field: 'name' | 'phone' | 'address', value: string) => {
    onUpdateContact(id, field, value);
    setEditingContact(null);
  };

  const cancelEdit = () => {
    setEditingContact(null);
  };

  const toggleRowExpansion = (contactId: number) => {
    const newExpanded = new Set(expandedRows);
    if (newExpanded.has(contactId)) {
      newExpanded.delete(contactId);
    } else {
      newExpanded.add(contactId);
    }
    setExpandedRows(newExpanded);
  };

  const getConfidenceColor = (confidence: number): 'success' | 'warning' | 'error' => {
    if (confidence >= 0.8) return 'success';
    if (confidence >= 0.6) return 'warning';
    return 'error';
  };

  if (contacts.length === 0) {
    return (
      <Card sx={{ height: '400px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <Box sx={{ textAlign: 'center', color: 'text.secondary' }}>
          <TableView sx={{ fontSize: 64, mb: 2, opacity: 0.3 }} />
          <Typography variant="h6" gutterBottom>
            연락처 추출 시스템
          </Typography>
          <Typography variant="body2">
            이미지를 업로드하고 연락처를 추출하세요
          </Typography>
        </Box>
      </Card>
    );
  }

  return (
    <Card>
      <CardContent sx={{ p: 0 }}>
        <Box sx={{ p: 3, pb: 0 }}>
          <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <TableView sx={{ color: 'primary.main' }} />
            추출된 연락처
          </Typography>
        </Box>
        
        <TableContainer sx={{ maxHeight: 'calc(100vh - 300px)' }}>
          <Table stickyHeader>
            <TableHead>
              <TableRow>
                <TableCell sx={{ width: 60, fontWeight: 600 }}>#</TableCell>
                <TableCell sx={{ fontWeight: 600 }}>이름</TableCell>
                <TableCell sx={{ fontWeight: 600 }}>전화번호</TableCell>
                <TableCell sx={{ fontWeight: 600, maxWidth: 300 }}>주소</TableCell>
                <TableCell sx={{ fontWeight: 600, width: 150 }}>상태</TableCell>
                <TableCell sx={{ fontWeight: 600, width: 100 }}>작업</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {contacts.map((contact) => (
                <React.Fragment key={contact.id}>
                  <TableRow 
                    sx={{ 
                      '&:hover': { bgcolor: 'grey.50' },
                      bgcolor: contact.needsReview ? 'warning.50' : 'inherit'
                    }}
                  >
                    <TableCell sx={{ fontWeight: 500 }}>{contact.id}</TableCell>
                    
                    {/* Name Cell */}
                    <TableCell>
                      {editingContact === contact.id ? (
                        <TextField
                          size="small"
                          defaultValue={contact.name}
                          onKeyPress={(e) => {
                            if (e.key === 'Enter') {
                              saveEdit(contact.id, 'name', (e.target as HTMLInputElement).value);
                            }
                          }}
                          autoFocus
                          sx={{ minWidth: 120 }}
                        />
                      ) : (
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                          <Typography variant="body2" sx={{ fontWeight: contact.name ? 500 : 400 }}>
                            {contact.name || '이름 없음'}
                          </Typography>
                          <IconButton size="small" onClick={() => startEditing(contact.id)}>
                            <Edit fontSize="small" />
                          </IconButton>
                        </Box>
                      )}
                    </TableCell>

                    {/* Phone Cell */}
                    <TableCell>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <Typography variant="body2" sx={{ fontWeight: 500 }}>
                          {contact.phone || '번호 없음'}
                        </Typography>
                        {contact.phone && (
                          <Chip 
                            label={contact.phone.startsWith('010') ? '휴대폰' : '일반'}
                            size="small"
                            color={contact.phone.startsWith('010') ? 'primary' : 'default'}
                            variant="outlined"
                          />
                        )}
                      </Box>
                    </TableCell>

                    {/* Address Cell */}
                    <TableCell sx={{ maxWidth: 300 }}>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <IconButton 
                          size="small" 
                          onClick={() => toggleRowExpansion(contact.id)}
                          sx={{ p: 0.5 }}
                        >
                          <Home fontSize="small" />
                          {expandedRows.has(contact.id) ? 
                            <ExpandLess fontSize="small" /> : 
                            <ExpandMore fontSize="small" />
                          }
                        </IconButton>
                        <Tooltip title={contact.address || '주소 정보 없음'}>
                          <Typography 
                            variant="body2" 
                            noWrap 
                            sx={{ 
                              maxWidth: 250,
                              color: contact.address ? 'text.primary' : 'text.secondary',
                              fontStyle: contact.address ? 'normal' : 'italic'
                            }}
                          >
                            {contact.address || '주소 정보 없음'}
                          </Typography>
                        </Tooltip>
                      </Box>
                    </TableCell>

                    {/* Status Cell */}
                    <TableCell>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexWrap: 'wrap' }}>
                        <Chip
                          label={`${(contact.confidence * 100).toFixed(0)}%`}
                          size="small"
                          color={getConfidenceColor(contact.confidence)}
                          variant="outlined"
                        />
                        {contact.needsReview && (
                          <Chip 
                            label="검토필요" 
                            size="small" 
                            color="warning"
                            variant="filled"
                          />
                        )}
                      </Box>
                    </TableCell>

                    {/* Actions Cell */}
                    <TableCell>
                      {editingContact === contact.id ? (
                        <Box sx={{ display: 'flex', gap: 0.5 }}>
                          <IconButton size="small" color="primary">
                            <Save fontSize="small" />
                          </IconButton>
                          <IconButton size="small" onClick={cancelEdit}>
                            <Cancel fontSize="small" />
                          </IconButton>
                        </Box>
                      ) : (
                        <IconButton size="small" onClick={() => startEditing(contact.id)}>
                          <Edit fontSize="small" />
                        </IconButton>
                      )}
                    </TableCell>
                  </TableRow>
                  
                  {/* Expandable Address Details Row */}
                  <TableRow>
                    <TableCell style={{ paddingBottom: 0, paddingTop: 0 }} colSpan={6}>
                      <Collapse in={expandedRows.has(contact.id)} timeout="auto" unmountOnExit>
                        <Box sx={{ margin: 2 }}>
                          <Typography variant="subtitle2" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                            <Home fontSize="small" />
                            주소 상세정보 (#{contact.id})
                          </Typography>
                          <AddressDetailsTable contact={contact} multiEntryResult={multiEntryResult} />
                        </Box>
                      </Collapse>
                    </TableCell>
                  </TableRow>
                </React.Fragment>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      </CardContent>
    </Card>
  );
};
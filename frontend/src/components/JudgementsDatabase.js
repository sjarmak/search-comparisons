import React, { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TablePagination,
  TableSortLabel,
  TextField,
  Typography,
  Chip,
  IconButton,
  Tooltip,
  CircularProgress,
  Alert,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Grid,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  ButtonGroup
} from '@mui/material';
import RefreshIcon from '@mui/icons-material/Refresh';
import DeleteIcon from '@mui/icons-material/Delete';
import FileDownloadIcon from '@mui/icons-material/FileDownload';
import { API_URL as DEFAULT_API_URL } from '../services/api';

/**
 * Component for viewing and managing the judgments database.
 * 
 * @param {Object} props - Component props
 * @param {string} props.API_URL - The API URL for making requests
 */
const JudgementsDatabase = ({ API_URL = DEFAULT_API_URL }) => {
  const [judgements, setJudgements] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(10);
  const [orderBy, setOrderBy] = useState('created_at');
  const [order, setOrder] = useState('desc');
  const [filters, setFilters] = useState({
    query: '',
    rater_id: '',
    source: '',
    score: ''
  });
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [judgementToDelete, setJudgementToDelete] = useState(null);
  const [deleteLoading, setDeleteLoading] = useState(false);
  const [exportDialogOpen, setExportDialogOpen] = useState(false);
  const [exportLoading, setExportLoading] = useState(false);
  const [exportType, setExportType] = useState('all'); // 'all' or 'filtered'

  // Fetch judgements from the backend
  const fetchJudgements = async () => {
    setLoading(true);
    setError(null);
    try {
      console.log('Fetching judgements from:', `${API_URL}/api/judgements/query/all`);
      const response = await fetch(`${API_URL}/api/judgements/query/all`);
      if (!response.ok) {
        throw new Error('Failed to fetch judgements');
      }
      const data = await response.json();
      setJudgements(data);
    } catch (err) {
      console.error('Error fetching judgements:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // Handle delete confirmation
  const handleDeleteClick = (judgement) => {
    setJudgementToDelete(judgement);
    setDeleteDialogOpen(true);
  };

  // Handle delete confirmation
  const handleDeleteConfirm = async () => {
    if (!judgementToDelete) return;

    setDeleteLoading(true);
    try {
      const response = await fetch(`${API_URL}/api/judgements/${judgementToDelete.id}`, {
        method: 'DELETE',
      });

      if (!response.ok) {
        throw new Error('Failed to delete judgement');
      }

      // Remove the deleted judgement from the state
      setJudgements(prev => prev.filter(j => j.id !== judgementToDelete.id));
      setDeleteDialogOpen(false);
      setJudgementToDelete(null);
    } catch (err) {
      console.error('Error deleting judgement:', err);
      setError(err.message);
    } finally {
      setDeleteLoading(false);
    }
  };

  // Handle delete cancellation
  const handleDeleteCancel = () => {
    setDeleteDialogOpen(false);
    setJudgementToDelete(null);
  };

  // Load judgements on component mount
  useEffect(() => {
    fetchJudgements();
  }, []);

  // Handle sorting
  const handleRequestSort = (property) => {
    const isAsc = orderBy === property && order === 'asc';
    setOrder(isAsc ? 'desc' : 'asc');
    setOrderBy(property);
  };

  // Handle pagination
  const handleChangePage = (event, newPage) => {
    setPage(newPage);
  };

  const handleChangeRowsPerPage = (event) => {
    setRowsPerPage(parseInt(event.target.value, 10));
    setPage(0);
  };

  // Handle filtering
  const handleFilterChange = (field, value) => {
    setFilters(prev => ({
      ...prev,
      [field]: value
    }));
    setPage(0);
  };

  // Sort and filter judgements
  const getSortedAndFilteredJudgements = () => {
    let filtered = [...judgements];

    // Apply filters
    if (filters.query) {
      filtered = filtered.filter(j => 
        j.query.toLowerCase().includes(filters.query.toLowerCase())
      );
    }
    if (filters.rater_id) {
      filtered = filtered.filter(j => 
        j.rater_id.toLowerCase().includes(filters.rater_id.toLowerCase())
      );
    }
    if (filters.source) {
      filtered = filtered.filter(j => 
        j.record_source.toLowerCase().includes(filters.source.toLowerCase())
      );
    }
    if (filters.score !== '') {
      filtered = filtered.filter(j => 
        j.judgement_score === parseFloat(filters.score)
      );
    }

    // Apply sorting
    filtered.sort((a, b) => {
      const aValue = a[orderBy];
      const bValue = b[orderBy];
      
      if (order === 'asc') {
        return aValue > bValue ? 1 : -1;
      } else {
        return aValue < bValue ? 1 : -1;
      }
    });

    return filtered;
  };

  // Get unique sources for filter dropdown
  const getUniqueSources = () => {
    const sources = new Set(judgements.map(j => j.record_source));
    return Array.from(sources).sort();
  };

  // Format date for display
  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleString();
  };

  // Helper function to get score label with epsilon comparison
  const getScoreLabel = (score) => {
    // Convert to number and round to 3 decimal places for comparison
    const numScore = Number(score);
    const roundedScore = Math.round(numScore * 1000) / 1000;
    
    // Use a larger epsilon for floating point comparison
    const epsilon = 0.001;
    
    if (Math.abs(roundedScore - 1) < epsilon) return 'Perfect (1)';
    if (Math.abs(roundedScore - 0.667) < epsilon) return 'Good (0.67)';
    if (Math.abs(roundedScore - 0.333) < epsilon) return 'Fair (0.33)';
    if (Math.abs(roundedScore - 0) < epsilon) return 'Poor (0)';
    return `Unknown (${roundedScore})`;
  };

  // Helper function to get score color
  const getScoreColor = (score) => {
    // Convert to number and round to 3 decimal places for comparison
    const numScore = Number(score);
    const roundedScore = Math.round(numScore * 1000) / 1000;
    
    // Use a larger epsilon for floating point comparison
    const epsilon = 0.001;
    
    if (Math.abs(roundedScore - 1) < epsilon) return 'success';
    if (Math.abs(roundedScore - 0.667) < epsilon) return 'info';
    if (Math.abs(roundedScore - 0.333) < epsilon) return 'warning';
    if (Math.abs(roundedScore - 0) < epsilon) return 'error';
    return 'default';
  };

  // Format judgement data for export
  const formatJudgementForExport = (judgement) => {
    // Helper function to get source label
    const getSourceLabel = (source) => {
      switch (source) {
        case 'ADS': return 'ADS';
        case 'Google Scholar': return 'Google Scholar';
        case 'Boosted ADS': return 'Boosted ADS';
        default: return source || 'Unknown';
      }
    };

    // Get the numeric score from judgement_score
    const score = Number(judgement.judgement_score);

    return {
      'Query': judgement.query || '',
      'Title': judgement.record_title || '',
      'Source': getSourceLabel(judgement.record_source),
      'Score': score,  // Use the numeric score
      'Score Label': getScoreLabel(score),  // Generate label from the numeric score
      'Note': judgement.judgement_note || '',
      'Date': formatDate(judgement.created_at),
      'Rater ID': judgement.rater_id || ''
    };
  };

  // Convert data to CSV format
  const convertToCSV = (data) => {
    if (!data.length) return '';
    
    const headers = Object.keys(data[0]);
    const csvRows = [
      headers.join(','),
      ...data.map(row => 
        headers.map(header => {
          const value = row[header]?.toString() || '';
          // Escape quotes and wrap in quotes if contains comma or quote
          return value.includes(',') || value.includes('"') 
            ? `"${value.replace(/"/g, '""')}"` 
            : value;
        }).join(',')
      )
    ];
    
    return csvRows.join('\n');
  };

  // Convert data to TXT format
  const convertToTXT = (data) => {
    if (!data.length) return '';
    
    const headers = Object.keys(data[0]);
    const maxLengths = headers.reduce((acc, header) => {
      acc[header] = Math.max(
        header.length,
        ...data.map(row => (row[header]?.toString() || '').length)
      );
      return acc;
    }, {});

    const formatRow = (row) => 
      headers.map(header => 
        (row[header]?.toString() || '').padEnd(maxLengths[header])
      ).join(' | ');

    const separator = headers.map(header => 
      '-'.repeat(maxLengths[header])
    ).join('-+-');

    return [
      formatRow(Object.fromEntries(headers.map(h => [h, h]))),
      separator,
      ...data.map(formatRow)
    ].join('\n');
  };

  // Sanitize string for use in filename
  const sanitizeFilename = (str) => {
    // Replace invalid filename characters with underscores
    // Keep alphanumeric, spaces, hyphens, and underscores
    return str
      .replace(/[^a-zA-Z0-9\s-_]/g, '_')
      .replace(/\s+/g, '_')
      .substring(0, 50); // Limit length to avoid too long filenames
  };

  // Extract identifier from similar query
  const extractSimilarIdentifier = (query) => {
    console.log('Extracting from query:', query); // Debug log
    const match = query.match(/^similar\((.*?)\)/);
    const result = match ? match[1] : query;
    console.log('Extracted result:', result); // Debug log
    return result;
  };

  // Handle export
  const handleExport = async (format) => {
    setExportLoading(true);
    try {
      const dataToExport = exportType === 'all' 
        ? judgements 
        : getSortedAndFilteredJudgements();
      
      // Debug log the data being exported
      console.log('Data to export:', dataToExport.map(j => ({
        score: j.judgement_score,
        scoreType: typeof j.judgement_score,
        raw: j
      })));
      
      const formattedData = dataToExport.map(formatJudgementForExport);
      const content = format === 'csv' 
        ? convertToCSV(formattedData)
        : convertToTXT(formattedData);
      
      const blob = new Blob([content], { 
        type: format === 'csv' ? 'text/csv' : 'text/plain' 
      });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      
      // Generate filename based on export type
      let filename;
      if (exportType === 'filtered' && filters.query) {
        console.log('Original query:', filters.query); // Debug log
        // For filtered exports, use the query in the filename
        const queryContent = filters.query.startsWith('similar(') 
          ? extractSimilarIdentifier(filters.query)
          : filters.query;
        console.log('Query content after processing:', queryContent); // Debug log
        const sanitizedQuery = sanitizeFilename(queryContent);
        console.log('Sanitized query:', sanitizedQuery); // Debug log
        filename = `judgements_query_${sanitizedQuery}.${format}`;
        console.log('Final filename:', filename); // Debug log
      } else {
        // For all exports or filtered exports without query, use timestamp
        const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
        filename = `judgements_${exportType}_${timestamp}.${format}`;
      }
      
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      
      setExportDialogOpen(false);
    } catch (err) {
      console.error('Error exporting data:', err);
      setError('Failed to export data');
    } finally {
      setExportLoading(false);
    }
  };

  // Handle export dialog open
  const handleExportClick = (type) => {
    console.log('Export clicked with type:', type); // Debug log
    console.log('Current filters:', filters); // Debug log
    setExportType(type);
    setExportDialogOpen(true);
  };

  // Handle export dialog close
  const handleExportDialogClose = () => {
    setExportDialogOpen(false);
  };

  // Render the component
  return (
    <Box sx={{ width: '100%', p: 2 }}>
      <Paper sx={{ width: '100%', mb: 2 }}>
        <Box sx={{ p: 2, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Typography variant="h6" component="div">
            Judgements Database
          </Typography>
          <Box sx={{ display: 'flex', gap: 1 }}>
            <ButtonGroup variant="outlined" size="small">
              <Button
                startIcon={<FileDownloadIcon />}
                onClick={() => handleExportClick('all')}
                disabled={loading || judgements.length === 0}
              >
                Export All
              </Button>
              <Button
                startIcon={<FileDownloadIcon />}
                onClick={() => handleExportClick('filtered')}
                disabled={loading || getSortedAndFilteredJudgements().length === 0}
              >
                Export Filtered
              </Button>
            </ButtonGroup>
            <Tooltip title="Refresh">
              <IconButton onClick={fetchJudgements} disabled={loading}>
                <RefreshIcon />
              </IconButton>
            </Tooltip>
          </Box>
        </Box>

        {/* Filters */}
        <Box sx={{ p: 2 }}>
          <Grid container spacing={2}>
            <Grid item xs={12} sm={6} md={3}>
              <TextField
                fullWidth
                label="Search Query"
                value={filters.query}
                onChange={(e) => handleFilterChange('query', e.target.value)}
                size="small"
              />
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <TextField
                fullWidth
                label="Rater ID"
                value={filters.rater_id}
                onChange={(e) => handleFilterChange('rater_id', e.target.value)}
                size="small"
              />
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <FormControl fullWidth size="small">
                <InputLabel>Source</InputLabel>
                <Select
                  value={filters.source}
                  label="Source"
                  onChange={(e) => handleFilterChange('source', e.target.value)}
                >
                  <MenuItem value="">All</MenuItem>
                  {getUniqueSources().map(source => (
                    <MenuItem key={source} value={source}>{source}</MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <FormControl fullWidth size="small">
                <InputLabel>Score</InputLabel>
                <Select
                  value={filters.score}
                  label="Score"
                  onChange={(e) => handleFilterChange('score', e.target.value)}
                >
                  <MenuItem value="">All</MenuItem>
                  <MenuItem value="0">Poor (0)</MenuItem>
                  <MenuItem value="0.33">Fair (0.33)</MenuItem>
                  <MenuItem value="0.67">Good (0.67)</MenuItem>
                  <MenuItem value="1">Perfect (1)</MenuItem>
                </Select>
              </FormControl>
            </Grid>
          </Grid>
        </Box>

        {error && (
          <Alert severity="error" sx={{ mx: 2, mb: 2 }}>
            {error}
          </Alert>
        )}

        <TableContainer>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>
                  <TableSortLabel
                    active={orderBy === 'query'}
                    direction={orderBy === 'query' ? order : 'asc'}
                    onClick={() => handleRequestSort('query')}
                  >
                    Query
                  </TableSortLabel>
                </TableCell>
                <TableCell>
                  <TableSortLabel
                    active={orderBy === 'record_title'}
                    direction={orderBy === 'record_title' ? order : 'asc'}
                    onClick={() => handleRequestSort('record_title')}
                  >
                    Title
                  </TableSortLabel>
                </TableCell>
                <TableCell>
                  <TableSortLabel
                    active={orderBy === 'record_source'}
                    direction={orderBy === 'record_source' ? order : 'asc'}
                    onClick={() => handleRequestSort('record_source')}
                  >
                    Source
                  </TableSortLabel>
                </TableCell>
                <TableCell>
                  <TableSortLabel
                    active={orderBy === 'judgement_score'}
                    direction={orderBy === 'judgement_score' ? order : 'asc'}
                    onClick={() => handleRequestSort('judgement_score')}
                  >
                    Score
                  </TableSortLabel>
                </TableCell>
                <TableCell>Note</TableCell>
                <TableCell>
                  <TableSortLabel
                    active={orderBy === 'created_at'}
                    direction={orderBy === 'created_at' ? order : 'asc'}
                    onClick={() => handleRequestSort('created_at')}
                  >
                    Date
                  </TableSortLabel>
                </TableCell>
                <TableCell>Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {loading ? (
                <TableRow>
                  <TableCell colSpan={7} align="center">
                    <CircularProgress />
                  </TableCell>
                </TableRow>
              ) : (
                getSortedAndFilteredJudgements()
                  .slice(page * rowsPerPage, page * rowsPerPage + rowsPerPage)
                  .map((judgement) => (
                    <TableRow key={judgement.id}>
                      <TableCell>{judgement.query}</TableCell>
                      <TableCell>{judgement.record_title}</TableCell>
                      <TableCell>
                        <Chip 
                          label={judgement.record_source}
                          size="small"
                          color={
                            judgement.record_source === 'ADS' ? 'primary' :
                            judgement.record_source === 'Google Scholar' ? 'error' :
                            judgement.record_source === 'Boosted ADS' ? 'success' :
                            'default'
                          }
                        />
                      </TableCell>
                      <TableCell>
                        <Chip
                          label={getScoreLabel(judgement.judgement_score)}
                          size="small"
                          color={getScoreColor(judgement.judgement_score)}
                        />
                      </TableCell>
                      <TableCell>
                        {judgement.judgement_note || '-'}
                      </TableCell>
                      <TableCell>{formatDate(judgement.created_at)}</TableCell>
                      <TableCell>
                        <Tooltip title="Delete judgement">
                          <IconButton
                            size="small"
                            color="error"
                            onClick={() => handleDeleteClick(judgement)}
                          >
                            <DeleteIcon />
                          </IconButton>
                        </Tooltip>
                      </TableCell>
                    </TableRow>
                  ))
              )}
            </TableBody>
          </Table>
        </TableContainer>
        <TablePagination
          rowsPerPageOptions={[5, 10, 25, 50]}
          component="div"
          count={getSortedAndFilteredJudgements().length}
          rowsPerPage={rowsPerPage}
          page={page}
          onPageChange={handleChangePage}
          onRowsPerPageChange={handleChangeRowsPerPage}
        />
      </Paper>

      {/* Delete Confirmation Dialog */}
      <Dialog
        open={deleteDialogOpen}
        onClose={handleDeleteCancel}
      >
        <DialogTitle>Delete Judgement</DialogTitle>
        <DialogContent>
          <Typography>
            Are you sure you want to delete this judgement?
          </Typography>
          {judgementToDelete && (
            <Box sx={{ mt: 2 }}>
              <Typography variant="subtitle2">Query:</Typography>
              <Typography>{judgementToDelete.query}</Typography>
              <Typography variant="subtitle2" sx={{ mt: 1 }}>Title:</Typography>
              <Typography>{judgementToDelete.record_title}</Typography>
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={handleDeleteCancel} disabled={deleteLoading}>
            Cancel
          </Button>
          <Button
            onClick={handleDeleteConfirm}
            color="error"
            disabled={deleteLoading}
            startIcon={deleteLoading ? <CircularProgress size={20} /> : null}
          >
            {deleteLoading ? 'Deleting...' : 'Delete'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Export Format Dialog */}
      <Dialog
        open={exportDialogOpen}
        onClose={handleExportDialogClose}
      >
        <DialogTitle>Choose Export Format</DialogTitle>
        <DialogContent>
          <Typography>
            Select the format to export {exportType === 'all' ? 'all' : 'filtered'} judgements:
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleExportDialogClose} disabled={exportLoading}>
            Cancel
          </Button>
          <Button
            onClick={() => handleExport('csv')}
            disabled={exportLoading}
            startIcon={exportLoading ? <CircularProgress size={20} /> : null}
          >
            {exportLoading ? 'Exporting...' : 'CSV'}
          </Button>
          <Button
            onClick={() => handleExport('txt')}
            disabled={exportLoading}
            startIcon={exportLoading ? <CircularProgress size={20} /> : null}
          >
            {exportLoading ? 'Exporting...' : 'TXT'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default JudgementsDatabase; 
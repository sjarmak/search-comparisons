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
  Button
} from '@mui/material';
import RefreshIcon from '@mui/icons-material/Refresh';
import DeleteIcon from '@mui/icons-material/Delete';
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

  // Render the component
  return (
    <Box sx={{ width: '100%', p: 2 }}>
      <Paper sx={{ width: '100%', mb: 2 }}>
        <Box sx={{ p: 2, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Typography variant="h6" component="div">
            Judgements Database
          </Typography>
          <Tooltip title="Refresh">
            <IconButton onClick={fetchJudgements} disabled={loading}>
              <RefreshIcon />
            </IconButton>
          </Tooltip>
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
                          label={
                            judgement.judgement_score === 1 ? 'Perfect (1)' :
                            judgement.judgement_score === 0.67 ? 'Good (0.67)' :
                            judgement.judgement_score === 0.33 ? 'Fair (0.33)' :
                            'Poor (0)'
                          }
                          size="small"
                          color={
                            judgement.judgement_score === 1 ? 'success' :
                            judgement.judgement_score === 0.67 ? 'info' :
                            judgement.judgement_score === 0.33 ? 'warning' :
                            'error'
                          }
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
    </Box>
  );
};

export default JudgementsDatabase; 
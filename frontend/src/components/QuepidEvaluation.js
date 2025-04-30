/**
 * Quepid Evaluation component for search-comparisons application.
 * 
 * This component provides UI for evaluating search results against
 * Quepid judgments, calculating metrics like nDCG@10.
 */
import React, { useState, useEffect } from 'react';
import { experimentService } from '../services/api';
import {
  Container,
  Typography,
  TextField,
  Button,
  Box,
  Card,
  CardContent,
  Chip,
  Grid,
  List,
  ListItem,
  ListItemText,
  Alert,
  CircularProgress,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Divider,
  Slider,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Link
} from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';

// Available document types for boosting
const DOC_TYPES = [
  'article',
  'refereed',
  'proceedings',
  'book',
  'thesis',
  'other'
];

const QuepidEvaluation = () => {
  // State for search parameters
  const [query, setQuery] = useState('triton');
  const [caseId, setCaseId] = useState('8914');
  const [maxResults, setMaxResults] = useState(20);
  
  // State for boost configuration
  const [boostConfig, setBoostConfig] = useState({
    name: "Boosted Results",
    citation_boost: 1.0,
    recency_boost: 1.0,
    doctype_boosts: {}
  });
  
  // State for UI
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [successMessage, setSuccessMessage] = useState(null);
  const [results, setResults] = useState(null);
  const [judgedDocuments, setJudgedDocuments] = useState([]);
  
  // Fetch judged documents when component mounts or caseId/query changes
  useEffect(() => {
    const fetchJudgedDocuments = async () => {
      try {
        const response = await experimentService.getJudgedDocuments(caseId, query);
        if (response.error) {
          setError(response.message || 'Error fetching judged documents');
        } else {
          setJudgedDocuments(response);
        }
      } catch (error) {
        setError(error.message || 'Error fetching judged documents');
      }
    };

    if (caseId && query) {
      fetchJudgedDocuments();
    }
  }, [caseId, query]);
  
  // Function to update boost configuration
  const updateBoostConfig = (field, value) => {
    setBoostConfig(prev => ({
      ...prev,
      [field]: value
    }));
  };
  
  // Function to update doctype boost
  const updateDoctypeBoost = (doctype, value) => {
    setBoostConfig(prev => ({
      ...prev,
      doctype_boosts: {
        ...prev.doctype_boosts,
        [doctype]: value
      }
    }));
  };
  
  // Function to evaluate search results with Quepid
  const handleEvaluate = async () => {
    // Clear previous state
    setError(null);
    setSuccessMessage(null);
    setResults(null);
    
    // Validate inputs
    if (!query.trim()) {
      setError('Please enter a search query');
      return;
    }
    
    if (!caseId || isNaN(parseInt(caseId))) {
      setError('Please enter a valid case ID');
      return;
    }
    
    // Prepare the evaluation request
    const evaluationRequest = {
      query: query.trim(),
      case_id: parseInt(caseId),
      max_results: maxResults,
      sources: ['ads'],  // Always use ADS
      boost_configs: [
        {
          name: "Base Results",
          citation_boost: 0.0,
          recency_boost: 0.0,
          doctype_boosts: {}
        },
        boostConfig
      ]
    };
    
    // Call the API
    setIsLoading(true);
    
    try {
      console.log('Sending request:', evaluationRequest); // Debug log
      const response = await experimentService.evaluateWithQuepid(evaluationRequest);
      console.log('API Response:', response); // Debug log
      
      if (response.error) {
        setError(response.message || 'Error evaluating search results');
      } else {
        setResults(response);
        if (!response.source_results || response.source_results.length === 0) {
          setError('No search results were returned');
        } else {
          setSuccessMessage('Evaluation completed successfully');
        }
      }
    } catch (error) {
      console.error('Quepid evaluation error:', error);
      const errorMessage = error.response?.data?.detail || 
                          error.message || 
                          'Error connecting to the server';
      setError(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };
  
  // Function to render the judged documents
  const renderJudgedDocuments = () => {
    if (!judgedDocuments.length) return null;
    
    return (
      <Box sx={{ mt: 4 }}>
        <Typography variant="h5" gutterBottom>
          Judged Documents
        </Typography>
        <TableContainer component={Paper}>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Title</TableCell>
                <TableCell>Authors</TableCell>
                <TableCell>Year</TableCell>
                <TableCell>Citations</TableCell>
                <TableCell>Type</TableCell>
                <TableCell>Database</TableCell>
                <TableCell>Score</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {judgedDocuments.map((doc, idx) => (
                <React.Fragment key={idx}>
                  <TableRow>
                    <TableCell>
                      <Typography variant="body2">
                        {doc.title || 'No title available'}
                      </Typography>
                      {doc.bibcode && (
                        <Typography variant="caption" color="primary">
                          <a href={`https://ui.adsabs.harvard.edu/abs/${doc.bibcode}/abstract`} 
                             target="_blank" 
                             rel="noopener noreferrer">
                            View
                          </a>
                        </Typography>
                      )}
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2">
                        {doc.authors?.join('; ')}
                      </Typography>
                    </TableCell>
                    <TableCell>{doc.year}</TableCell>
                    <TableCell>{doc.citation_count || 0}</TableCell>
                    <TableCell>{doc.doc_type || 'N/A'}</TableCell>
                    <TableCell>{doc.database || 'N/A'}</TableCell>
                    <TableCell>
                      <Chip 
                        label={`${doc.score}`}
                        color={doc.score === 3 ? undefined : doc.score > 0 ? 'success' : 'default'}
                        size="small"
                        sx={{
                          backgroundColor: doc.score === 3 ? '#00e676' : undefined,
                          color: doc.score === 3 ? '#000' : undefined
                        }}
                      />
                    </TableCell>
                  </TableRow>
                  {doc.abstract && (
                    <TableRow>
                      <TableCell colSpan={7} sx={{ py: 0 }}>
                        <Accordion>
                          <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                            <Typography variant="subtitle2">Abstract</Typography>
                          </AccordionSummary>
                          <AccordionDetails>
                            <Typography variant="body2" paragraph>
                              {doc.abstract}
                            </Typography>
                            {doc.keywords && doc.keywords.length > 0 && (
                              <>
                                <Typography variant="subtitle2">Keywords:</Typography>
                                <Box sx={{ mt: 1 }}>
                                  {doc.keywords.map((keyword, kidx) => (
                                    <Chip
                                      key={kidx}
                                      label={keyword}
                                      size="small"
                                      sx={{ mr: 0.5, mb: 0.5 }}
                                    />
                                  ))}
                                </Box>
                              </>
                            )}
                          </AccordionDetails>
                        </Accordion>
                      </TableCell>
                    </TableRow>
                  )}
                </React.Fragment>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      </Box>
    );
  };
  
  // Function to render the evaluation results
  const renderResults = () => {
    if (!results) return null;
    
    return (
      <Box sx={{ mt: 4 }}>
        <Typography variant="h5" gutterBottom>
          Evaluation Results
        </Typography>

        {/* Metrics Display */}
        <Grid container spacing={4}>
          {results.source_results?.map((sourceResult, index) => (
            <Grid item xs={12} key={index}>
              <Paper elevation={2} sx={{ p: 3 }}>
                <Typography variant="h6" gutterBottom>
                  {sourceResult.source.toUpperCase()} Results
                </Typography>
                
                {/* Metrics Grid */}
                <Grid container spacing={2}>
                  {sourceResult.metrics.map((metric, idx) => (
                    <Grid item xs={12} sm={6} md={4} key={idx}>
                      <Paper elevation={1} sx={{ p: 2, bgcolor: 'grey.50' }}>
                        <Typography variant="h6">
                          {metric.value.toFixed(3)}
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                          {metric.name}
                        </Typography>
                        <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                          {metric.description}
                        </Typography>
                      </Paper>
                    </Grid>
                  ))}
                </Grid>

                {/* Summary Stats */}
                <Box sx={{ mt: 2 }}>
                  <Typography variant="body2" color="text.secondary">
                    Documents judged: {results.total_judged} | 
                    Documents retrieved: {sourceResult?.results_count || 0} | 
                    Judged documents found: {sourceResult?.judged_retrieved || 0} | 
                    Relevant documents found: {sourceResult?.relevant_retrieved || 0}
                  </Typography>
                </Box>
              </Paper>
            </Grid>
          ))}
        </Grid>
      </Box>
    );
  };
  
  return (
    <Container maxWidth="lg">
      <Box my={4}>
        <Typography variant="h4" component="h1" gutterBottom>
          Quepid Evaluation
        </Typography>

        <Typography variant="body1" paragraph>
          Evaluate search results against Quepid relevance judgments to measure the effectiveness of search algorithms.
        </Typography>
        
        <Card sx={{ mb: 4 }}>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Evaluation Parameters
            </Typography>
            
            <Grid container spacing={3}>
              <Grid item xs={12} md={6}>
                <TextField
                  label="Search Query"
                  fullWidth
                  margin="normal"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="Enter search query"
                />
              </Grid>
              
              <Grid item xs={12} md={6}>
                <TextField
                  label="Quepid Case ID"
                  fullWidth
                  margin="normal"
                  value={caseId}
                  onChange={(e) => setCaseId(e.target.value)}
                  placeholder="Enter your Quepid case ID"
                  type="number"
                />
              </Grid>

              <Grid item xs={12} md={6}>
                <TextField
                  label="Max Results"
                  fullWidth
                  margin="normal"
                  value={maxResults}
                  onChange={(e) => setMaxResults(parseInt(e.target.value) || 20)}
                  placeholder="Maximum number of results"
                  type="number"
                />
              </Grid>

              {/* Boost Configuration */}
              <Grid item xs={12}>
                <Typography variant="h6" gutterBottom sx={{ mt: 2 }}>
                  Boost Configuration
                </Typography>
                <Grid container spacing={3}>
                  <Grid item xs={12} md={4}>
                    <Typography gutterBottom>Citation Boost</Typography>
                    <Slider
                      value={boostConfig.citation_boost}
                      onChange={(_, value) => updateBoostConfig('citation_boost', value)}
                      min={0}
                      max={2}
                      step={0.1}
                      marks
                    />
                    <Typography variant="caption" color="text.secondary">
                      {boostConfig.citation_boost.toFixed(1)}
                    </Typography>
                  </Grid>
                  
                  <Grid item xs={12} md={4}>
                    <Typography gutterBottom>Recency Boost</Typography>
                    <Slider
                      value={boostConfig.recency_boost}
                      onChange={(_, value) => updateBoostConfig('recency_boost', value)}
                      min={0}
                      max={2}
                      step={0.1}
                      marks
                    />
                    <Typography variant="caption" color="text.secondary">
                      {boostConfig.recency_boost.toFixed(1)}
                    </Typography>
                  </Grid>

                  <Grid item xs={12}>
                    <Typography gutterBottom>Document Type Boosts</Typography>
                    <Grid container spacing={2}>
                      {DOC_TYPES.map((doctype) => (
                        <Grid item xs={12} sm={6} md={4} key={doctype}>
                          <Typography variant="caption" display="block">
                            {doctype.charAt(0).toUpperCase() + doctype.slice(1)}
                          </Typography>
                          <Slider
                            value={boostConfig.doctype_boosts[doctype] || 1.0}
                            onChange={(_, value) => updateDoctypeBoost(doctype, value)}
                            min={0}
                            max={2}
                            step={0.1}
                            marks
                          />
                          <Typography variant="caption" color="text.secondary">
                            {(boostConfig.doctype_boosts[doctype] || 1.0).toFixed(1)}
                          </Typography>
                        </Grid>
                      ))}
                    </Grid>
                  </Grid>
                </Grid>
              </Grid>
            </Grid>

            <Box mt={3} textAlign="center">
              <Button
                variant="contained"
                color="primary"
                onClick={handleEvaluate}
                disabled={isLoading}
                size="large"
              >
                {isLoading ? <CircularProgress size={24} /> : 'Evaluate Search Results'}
              </Button>
            </Box>
            
            {error && (
              <Alert severity="error" sx={{ mt: 2 }}>
                {typeof error === 'string' ? error : 'An error occurred while evaluating results'}
              </Alert>
            )}
            
            {successMessage && (
              <Alert severity="success" sx={{ mt: 2 }}>
                {successMessage}
              </Alert>
            )}
          </CardContent>
        </Card>
        
        {renderJudgedDocuments()}
        {renderResults()}
      </Box>
    </Container>
  );
};

export default QuepidEvaluation;
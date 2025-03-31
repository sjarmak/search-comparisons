/**
 * Quepid Evaluation component for search-comparisons application.
 * 
 * This component provides UI for evaluating search results against
 * Quepid judgments, calculating metrics like nDCG@10.
 */
import React, { useState } from 'react';
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
  MenuItem
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
  const [query, setQuery] = useState('');
  const [caseId, setCaseId] = useState('');
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
      const response = await experimentService.evaluateWithQuepid(evaluationRequest);
      
      if (response.error) {
        setError(response.message || 'Error evaluating search results');
      } else {
        setResults(response);
        setSuccessMessage('Evaluation completed successfully');
      }
    } catch (error) {
      // Handle different types of error objects
      const errorMessage = error.response?.data?.detail || 
                          error.message || 
                          'Error connecting to the server';
      setError(errorMessage);
      console.error('Quepid evaluation error:', error);
    } finally {
      setIsLoading(false);
    }
  };
  
  // Function to render the evaluation results
  const renderResults = () => {
    if (!results) return null;
    
    return (
      <Box mt={4}>
        <Typography variant="h5" gutterBottom>
          Evaluation Results for "{results.query}"
        </Typography>
        
        <Box mb={2}>
          <Chip 
            label={`Case: ${results.case_name || 'N/A'}`} 
            color="primary" 
            variant="outlined" 
            sx={{ marginRight: 1 }}
          />
          <Chip 
            label={`Total judged: ${results.total_judged || 0}`} 
            color="primary" 
            variant="outlined" 
            sx={{ marginRight: 1 }}
          />
          <Chip 
            label={`Total relevant: ${results.total_relevant || 0}`} 
            color="primary" 
            variant="outlined"
          />
        </Box>
        
        {results.available_queries && results.available_queries.length > 0 && (
          <Alert severity="info" sx={{ mb: 2 }}>
            <Typography variant="body2">
              Note: The exact query was not found. Here are some available queries in this case:
            </Typography>
            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, mt: 1 }}>
              {results.available_queries.map((q, i) => (
                <Chip 
                  key={i} 
                  label={q}
                  size="small"
                  onClick={() => setQuery(q)}
                  color="primary"
                />
              ))}
            </Box>
          </Alert>
        )}
        
        <TableContainer component={Paper}>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Source</TableCell>
                <TableCell>nDCG@10</TableCell>
                <TableCell>Precision@10</TableCell>
                <TableCell>Recall</TableCell>
                <TableCell>Judged/Relevant</TableCell>
                <TableCell>Improvement</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {results.source_results?.map((sourceResult) => {
                // Find metrics
                const ndcg10 = sourceResult.metrics?.find(m => m.name === 'ndcg@10');
                const precision10 = sourceResult.metrics?.find(m => m.name === 'p@10');
                const recall = sourceResult.metrics?.find(m => m.name === 'recall');
                
                return (
                  <TableRow key={sourceResult.source}>
                    <TableCell>{sourceResult.source}</TableCell>
                    <TableCell>{ndcg10 ? ndcg10.value.toFixed(3) : 'N/A'}</TableCell>
                    <TableCell>{precision10 ? precision10.value.toFixed(3) : 'N/A'}</TableCell>
                    <TableCell>{recall ? recall.value.toFixed(3) : 'N/A'}</TableCell>
                    <TableCell>
                      {sourceResult.judged_retrieved || 0}/{sourceResult.relevant_retrieved || 0} of {sourceResult.results_count || 0}
                    </TableCell>
                    <TableCell>
                      {sourceResult.improvement ? (
                        <Typography
                          color={sourceResult.improvement >= 0 ? 'success.main' : 'error.main'}
                        >
                          {sourceResult.improvement > 0 ? '↑' : '↓'} 
                          {Math.abs(sourceResult.improvement).toFixed(3)}
                        </Typography>
                      ) : 'N/A'}
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </TableContainer>
        
        <Box mt={4}>
          <Typography variant="h6" gutterBottom>
            Detailed Metrics
          </Typography>
          
          {results.source_results?.map((sourceResult) => (
            <Accordion key={sourceResult.source}>
              <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                <Typography>{sourceResult.source}</Typography>
              </AccordionSummary>
              <AccordionDetails>
                <TableContainer>
                  <Table size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell>Metric</TableCell>
                        <TableCell>Value</TableCell>
                        <TableCell>Description</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {sourceResult.metrics?.map((metric, idx) => (
                        <TableRow key={idx}>
                          <TableCell>{metric.name}</TableCell>
                          <TableCell>{metric.value.toFixed(3)}</TableCell>
                          <TableCell>{metric.description}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              </AccordionDetails>
            </Accordion>
          ))}
        </Box>
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
        
        {renderResults()}
      </Box>
    </Container>
  );
};

export default QuepidEvaluation;
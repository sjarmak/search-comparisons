import React, { useState } from 'react';
import { 
  Box, Typography, TextField, Button, 
  Grid, Paper, CircularProgress, Chip,
  Card, CardContent, Divider, Alert, Tooltip,
  List, ListItem, ListItemText, IconButton
} from '@mui/material';
import SearchIcon from '@mui/icons-material/Search';
import InfoIcon from '@mui/icons-material/Info';
import SchemaIcon from '@mui/icons-material/Schema';
import TipsAndUpdatesIcon from '@mui/icons-material/TipsAndUpdates';

import { searchService } from '../services/api';

/**
 * QueryIntent component for transforming queries based on user intent
 * 
 * @returns {React.ReactElement} The QueryIntent component
 */
const QueryIntent = () => {
  // State for query and results
  const [query, setQuery] = useState('');
  const [transformedQuery, setTransformedQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState(null);
  const [error, setError] = useState(null);
  const [intentInfo, setIntentInfo] = useState(null);
  
  // Function to analyze and transform the query
  const analyzeQuery = async () => {
    if (!query.trim()) {
      setError("Please enter a search query");
      return;
    }
    
    setLoading(true);
    setError(null);
    
    try {
      // This is a placeholder for your future agentic workflow
      // You would replace this with an actual API call to your backend
      // that would analyze the query and return a transformed version
      
      // Mock implementation of query intent analysis
      // In the future, replace with your actual API call
      await new Promise(resolve => setTimeout(resolve, 1000)); // Simulate API call
      
      // Example transformation logic (to be replaced with your actual logic)
      let transformed = query;
      let intent = "information";
      let explanation = "";
      
      // Simple rule-based intent detection (replace with ML/LLM-based approach)
      if (query.toLowerCase().includes("latest") || query.toLowerCase().includes("recent")) {
        transformed = `${query} year:2022-2023`;
        intent = "recency";
        explanation = "Added year filter to focus on recent papers";
      } else if (query.toLowerCase().includes("review") || query.toLowerCase().includes("survey")) {
        transformed = `${query} doctype:review`;
        intent = "overview";
        explanation = "Added doctype filter to focus on review papers";
      } else if (query.toLowerCase().includes("who") || query.toLowerCase().includes("authors")) {
        transformed = `${query} sort:citation_count desc`;
        intent = "authoritative";
        explanation = "Sorted by citation count to find influential authors";
      } else if (query.toLowerCase().includes("compare") || query.toLowerCase().includes("versus") || query.toLowerCase().includes("vs")) {
        transformed = `(${query}) reviews:50`;
        intent = "comparison";
        explanation = "Added references filter to find papers that compare topics";
      }
      
      const intentInfo = {
        original: query,
        transformed: transformed,
        intent: intent,
        explanation: explanation
      };
      
      setTransformedQuery(transformed);
      setIntentInfo(intentInfo);
      
      // Now you would actually send this transformed query to ADS
      // For now, we'll just simulate it
      await searchADS(transformed);
      
    } catch (err) {
      console.error('Error analyzing query:', err);
      setError(`Failed to analyze query: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };
  
  // Function to search ADS with the transformed query
  const searchADS = async (adsQuery) => {
    try {
      // In a real implementation, you would call your ADS API
      // For now, this is a placeholder
      
      // Mock response with sample data
      const mockResults = {
        query: adsQuery,
        results: [
          {
            title: "Sample Paper 1 for query: " + adsQuery,
            authors: ["Author A", "Author B", "Author C"],
            year: 2023,
            abstract: "This is a sample abstract for the first result that would match your transformed query.",
            bibcode: "2023ApJ...123..456S",
            citation_count: 42
          },
          {
            title: "Sample Paper 2 for query: " + adsQuery,
            authors: ["Author D", "Author E"],
            year: 2022,
            abstract: "This is a sample abstract for the second result that would match your transformed query.",
            bibcode: "2022ApJ...456..789T",
            citation_count: 18
          }
        ]
      };
      
      // In production, you would use real API call like:
      // const response = await searchService.getSearchResults('ads', adsQuery, [], 10);
      
      setResults(mockResults);
      
    } catch (err) {
      console.error('Error searching ADS:', err);
      setError(`Failed to search ADS: ${err.message}`);
    }
  };
  
  // Render a single search result
  const renderSearchResult = (result, index) => {
    return (
      <Card key={index} variant="outlined" sx={{ mb: 2 }}>
        <CardContent>
          <Typography variant="h6" component="div">
            {result.title}
          </Typography>
          <Typography variant="body2" color="text.secondary" gutterBottom>
            {Array.isArray(result.authors) 
              ? result.authors.slice(0, 3).join(', ') + (result.authors.length > 3 ? ', et al.' : '')
              : result.authors}
            {result.year ? ` (${result.year})` : ''}
          </Typography>
          <Typography variant="body2" color="text.secondary" gutterBottom>
            {result.bibcode} | Citations: {result.citation_count}
          </Typography>
          <Divider sx={{ my: 1 }} />
          <Typography variant="body2">
            {result.abstract}
          </Typography>
        </CardContent>
      </Card>
    );
  };
  
  // Render the intent analysis card
  const renderIntentCard = () => {
    if (!intentInfo) return null;
    
    return (
      <Paper elevation={3} sx={{ p: 3, mb: 4, bgcolor: 'white' }}>
        <Box display="flex" justifyContent="space-between" alignItems="flex-start">
          <Typography variant="h6" gutterBottom color="primary.main">
            Query Intent Analysis
          </Typography>
          <Chip 
            icon={<TipsAndUpdatesIcon />} 
            label={intentInfo.intent.toUpperCase()} 
            color="primary" 
          />
        </Box>
        
        <Grid container spacing={2}>
          <Grid item xs={12} md={6}>
            <Typography variant="subtitle2" gutterBottom>
              Original Query:
            </Typography>
            <Paper variant="outlined" sx={{ p: 1, bgcolor: 'grey.50' }}>
              <Typography variant="body1">
                {intentInfo.original}
              </Typography>
            </Paper>
          </Grid>
          <Grid item xs={12} md={6}>
            <Typography variant="subtitle2" gutterBottom>
              Transformed Query:
            </Typography>
            <Paper variant="outlined" sx={{ p: 1, bgcolor: 'blue.50' }}>
              <Typography variant="body1" color="primary">
                {intentInfo.transformed}
              </Typography>
            </Paper>
          </Grid>
          <Grid item xs={12}>
            <Typography variant="subtitle2" gutterBottom>
              Explanation:
            </Typography>
            <Paper variant="outlined" sx={{ p: 1, bgcolor: 'grey.50' }}>
              <Typography variant="body2">
                {intentInfo.explanation || "No specific transformations applied."}
              </Typography>
            </Paper>
          </Grid>
        </Grid>
      </Paper>
    );
  };
  
  return (
    <Box>
      <Typography variant="h5" gutterBottom>
        Query Intent Analysis
      </Typography>
      <Typography paragraph>
        Enter a search query and our system will analyze the intent behind it, 
        transform it to better match your needs, and then search ADS with the improved query.
      </Typography>
      
      <Paper elevation={3} sx={{ p: 3, mb: 4 }}>
        <Grid container spacing={2} alignItems="center">
          <Grid item xs={12} sm={9}>
            <TextField
              fullWidth
              label="Search Query"
              variant="outlined"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Enter your search query (e.g., 'recent papers on exoplanets')"
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  analyzeQuery();
                }
              }}
              disabled={loading}
            />
          </Grid>
          <Grid item xs={12} sm={3}>
            <Button
              variant="contained"
              color="primary"
              onClick={analyzeQuery}
              disabled={loading}
              startIcon={loading ? <CircularProgress size={18} /> : <SchemaIcon />}
              fullWidth
            >
              {loading ? "Analyzing..." : "Analyze Intent"}
            </Button>
          </Grid>
        </Grid>
      </Paper>

      {/* Alert for errors */}
      {error && (
        <Alert severity="error" sx={{ mt: 2, mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}
      
      {/* Intent analysis results */}
      {intentInfo && renderIntentCard()}
      
      {/* Search results */}
      {results && (
        <Box>
          <Typography variant="h6" gutterBottom>
            Search Results
          </Typography>
          <Box>
            {results.results.map((result, index) => (
              renderSearchResult(result, index)
            ))}
          </Box>
        </Box>
      )}
      
      {/* Loading indicator */}
      {loading && (
        <Box display="flex" justifyContent="center" my={4}>
          <CircularProgress />
        </Box>
      )}
    </Box>
  );
};

export default QueryIntent;

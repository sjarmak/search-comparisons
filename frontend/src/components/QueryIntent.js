import React, { useState } from 'react';
import { 
  Box, Typography, TextField, Button, 
  Grid, Paper, CircularProgress, Chip,
  Card, CardContent, Divider, Alert, Tooltip,
  List, ListItem, ListItemText, IconButton, Link, Stack
} from '@mui/material';
import SearchIcon from '@mui/icons-material/Search';
import InfoIcon from '@mui/icons-material/Info';
import SchemaIcon from '@mui/icons-material/Schema';
import TipsAndUpdatesIcon from '@mui/icons-material/TipsAndUpdates';
import { styled } from '@mui/material/styles';

import { searchService } from '../services/api';

const StyledPaper = styled(Paper)(({ theme }) => ({
  padding: theme.spacing(2),
  marginBottom: theme.spacing(2),
  backgroundColor: theme.palette.background.paper,
}));

const ResultPaper = styled(Paper)(({ theme }) => ({
  padding: theme.spacing(2),
  marginBottom: theme.spacing(2),
  backgroundColor: theme.palette.background.paper,
  '&:hover': {
    backgroundColor: theme.palette.action.hover,
  },
}));

const AuthorChip = styled(Chip)(({ theme }) => ({
  marginRight: theme.spacing(0.5),
  marginBottom: theme.spacing(0.5),
}));

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
      // Call the backend API to transform the query and get results
      const response = await searchService.transformQuery(query);
      
      console.log('Raw response from backend:', response);
      
      if (response.error) {
        throw new Error(response.message);
      }
      
      // Extract the transformed query and intent info
      const intentInfo = {
        original: response.original_query,
        transformed: response.transformed_query,
        intent: response.intent,
        explanation: response.explanation
      };
      
      console.log('Processed intent info:', intentInfo);
      
      setTransformedQuery(response.transformed_query);
      setIntentInfo(intentInfo);
      
      // Set the search results - handle both possible response structures
      const searchResults = {
        query: response.transformed_query,
        results: response.search_results?.results || response.results?.docs || []
      };
      
      console.log('Processed search results:', searchResults);
      
      setResults(searchResults);
      
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
      // Call the backend API to get search results
      const response = await searchService.getSearchResults('ads', adsQuery, [], 20);
      
      if (response.error) {
        throw new Error(response.message);
      }
      
      setResults(response);
      
    } catch (err) {
      console.error('Error searching ADS:', err);
      setError(`Failed to search ADS: ${err.message}`);
    }
  };
  
  // Render a single search result
  const renderSearchResult = (result, index) => {
    const formatCitationCount = (count) => {
      if (count >= 1000) {
        return `${(count / 1000).toFixed(1)}k`;
      }
      return count.toString();
    };

    // Create links object
    const links = {
      ads: `https://ui.adsabs.harvard.edu/abs/${result.bibcode}/abstract`,
      pdf: result.property?.includes('PUB_PDF') ? `https://ui.adsabs.harvard.edu/link_gateway/${result.bibcode}/PUB_PDF` : null,
      arxiv: result.property?.includes('EPRINT_HTML') ? `https://arxiv.org/abs/${result.bibcode}` : null
    };

    // Format authors
    const authors = Array.isArray(result.author) ? result.author : [];

    return (
      <React.Fragment key={result.bibcode || index}>
        <ResultPaper elevation={1}>
          <Typography variant="h6" component="div" gutterBottom>
            <Link 
              href={links.ads} 
              target="_blank" 
              rel="noopener noreferrer"
              color="primary"
              underline="hover"
            >
              {result.title}
            </Link>
          </Typography>
          
          <Stack direction="row" spacing={1} alignItems="center" mb={1}>
            <Typography variant="body2" color="textSecondary">
              {authors.join(', ')}
            </Typography>
            {result.year && (
              <Typography variant="body2" color="textSecondary">
                • {result.year}
              </Typography>
            )}
            {result.citation_count > 0 && (
              <Typography variant="body2" color="textSecondary">
                • {formatCitationCount(result.citation_count)} citations
              </Typography>
            )}
          </Stack>

          {result.pub && (
            <Typography variant="body2" color="textSecondary" gutterBottom>
              {result.pub}
              {result.volume && `, Vol. ${result.volume}`}
              {result.page && `, p. ${result.page}`}
            </Typography>
          )}

          {result.abstract && (
            <Typography variant="body2" paragraph>
              {result.abstract}
            </Typography>
          )}

          <Stack direction="row" spacing={1} alignItems="center">
            {links.pdf && (
              <Link 
                href={links.pdf} 
                target="_blank" 
                rel="noopener noreferrer"
                variant="body2"
              >
                PDF
              </Link>
            )}
            {links.arxiv && (
              <Link 
                href={links.arxiv} 
                target="_blank" 
                rel="noopener noreferrer"
                variant="body2"
              >
                arXiv
              </Link>
            )}
            {result.doi && (
              <Link 
                href={`https://doi.org/${result.doi}`} 
                target="_blank" 
                rel="noopener noreferrer"
                variant="body2"
              >
                DOI
              </Link>
            )}
          </Stack>

          {result.keyword && result.keyword.length > 0 && (
            <Box mt={1}>
              {result.keyword.map((keyword, idx) => (
                <Chip 
                  key={idx} 
                  label={keyword} 
                  size="small" 
                  sx={{ mr: 0.5, mb: 0.5 }}
                />
              ))}
            </Box>
          )}
        </ResultPaper>
        {index < results.results.length - 1 && <Divider />}
      </React.Fragment>
    );
  };
  
  // Render the intent analysis card
  const renderIntentCard = () => {
    if (!intentInfo) return null;
    
    return (
      <StyledPaper elevation={1}>
        <Typography variant="h6" gutterBottom>
          Query Intent Analysis
        </Typography>
        <Typography variant="subtitle1" color="textSecondary">
          {intentInfo.intent.toUpperCase()}
        </Typography>
        <Typography variant="body1" paragraph>
          <strong>Original Query:</strong> {intentInfo.original}
        </Typography>
        <Typography variant="body1" paragraph>
          <strong>Transformed Query:</strong> {intentInfo.transformed}
        </Typography>
        <Typography variant="body2" color="textSecondary">
          {intentInfo.explanation || "No specific transformations applied."}
        </Typography>
      </StyledPaper>
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
            Search Results ({results.results.length})
          </Typography>
          <List>
            {results.results.map((result, index) => (
              renderSearchResult(result, index))
            )}
          </List>
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

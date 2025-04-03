import React, { useState } from 'react';
import { 
  Container, Box, Typography, TextField, Button, 
  Checkbox, FormControlLabel, FormGroup, Grid, 
  CircularProgress, Paper, Tabs, Tab, Divider, Alert,
  IconButton, AppBar, Toolbar, TableContainer, Table,
  TableHead, TableBody, TableRow, TableCell, Chip,
  List, ListItem, ListItemAvatar, ListItemText, ListItemSecondaryAction,
  Avatar, Tooltip, Accordion, AccordionSummary, AccordionDetails,
  Menu, MenuItem
} from '@mui/material';
import InfoIcon from '@mui/icons-material/Info';
import ScienceIcon from '@mui/icons-material/Science';
import SearchIcon from '@mui/icons-material/Search';
import GitHubIcon from '@mui/icons-material/GitHub';
import LaunchIcon from '@mui/icons-material/Launch';
import AssessmentIcon from '@mui/icons-material/Assessment';
import AccountCircleIcon from '@mui/icons-material/AccountCircle';
import ExitToAppIcon from '@mui/icons-material/ExitToApp';
import { Routes, Route, Navigate, useNavigate } from 'react-router-dom';

import { searchService, experimentService } from './services/api';
import BoostExperiment from './components/BoostExperiment';
import QuepidEvaluation from './components/QuepidEvaluation';
import SimilarityTests from './components/SimilarityTests';
import QueryIntent from './components/QueryIntent';
import Login from './components/Login';
import ProtectedRoute from './components/ProtectedRoute';
import StableInput from './components/StableInput';
import { useAuth, DEFAULT_PASSWORD } from './contexts/AuthContext';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';
const APP_VERSION = "1.0.0";

/**
 * Main application component
 * 
 * @returns {React.ReactElement} The main application component
 */
function App() {
  // Authentication state
  const { isAuthenticated, login, logout } = useAuth();
  const navigate = useNavigate();
  
  // User menu state
  const [anchorEl, setAnchorEl] = useState(null);
  const openMenu = Boolean(anchorEl);
  
  // State for search query and options
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState(null);
  const [error, setError] = useState(null);
  const [mainTab, setMainTab] = useState(0);
  const [experimentTab, setExperimentTab] = useState(0);
  
  // State for source selection
  const [sources, setSources] = useState({
    ads: true,
    scholar: true,
    semanticScholar: true,
    webOfScience: true
  });
  
  // State for similarity metrics selection
  const [metrics, setMetrics] = useState({
    jaccard: true,
    rankBiased: true
  });
  
  // State for metadata fields to compare
  const [fields, setFields] = useState({
    title: true,
    abstract: true,
    authors: true,
    doi: true,
    year: true,
    citation_count: true
  });

  // Boost experiment state
  const [boostConfig, setBoostConfig] = useState({
    query: '',
    boost_fields: ['citation_count', 'year'],
    boost_weights: {
      citation_count: 0.2,
      year: 0.4
    },
    max_boost: 1.5
  });
  
  // Result tab state
  const [resultTab, setResultTab] = useState(0);
  const [filterText, setFilterText] = useState('');

  // Active source for detailed results
  const [activeSource, setActiveSource] = useState(null);

  // Handle user menu open
  const handleMenuClick = (event) => {
    setAnchorEl(event.currentTarget);
  };

  // Handle user menu close
  const handleMenuClose = () => {
    setAnchorEl(null);
  };

  // Handle logout
  const handleLogout = () => {
    handleMenuClose();
    logout();
    navigate('/login');
  };

  // Handle source selection changes
  const handleSourceChange = (event) => {
    setSources({
      ...sources,
      [event.target.name]: event.target.checked
    });
  };

  // Handle metrics selection changes
  const handleMetricsChange = (event) => {
    setMetrics({
      ...metrics,
      [event.target.name]: event.target.checked
    });
  };

  // Handle fields selection changes
  const handleFieldsChange = (event) => {
    setFields({
      ...fields,
      [event.target.name]: event.target.checked
    });
  };

  // Handle tab changes
  const handleMainTabChange = (event, newValue) => {
    setMainTab(newValue);
  };

  const handleExperimentTabChange = (event, newValue) => {
    console.log('Experiment tab changed to:', newValue);
    setExperimentTab(newValue);
  };

  // Submit the search query
  const handleSearch = async () => {
    if (!query.trim()) {
      setError("Please enter a search query");
      return;
    }
    
    if (!Object.values(sources).some(val => val)) {
      setError("Please select at least one search source");
      return;
    }
    
    setLoading(true);
    setError(null);
    
    try {
      const selectedSources = Object.keys(sources).filter(key => sources[key]);
      const selectedMetrics = Object.keys(metrics).filter(key => metrics[key]);
      
      // Always include all fields since we removed the fields selection UI
      const selectedFields = ['title', 'abstract', 'authors', 'doi', 'year', 'citation_count'];
      
      const requestBody = {
        query,
        sources: selectedSources,
        metrics: selectedMetrics,
        fields: selectedFields
      };

      const response = await searchService.compareSearchResults(requestBody);
      
      if (response.error) {
        setError(response.message);
      } else {
        setResults(response);
      }
    } catch (err) {
      console.error('Search error:', err);
      setError(`Failed to fetch results: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  // Run boost experiment
  const handleRunBoostExperiment = async () => {
    if (!boostConfig.query.trim()) {
      setError("Please enter a query for the boost experiment");
      return;
    }
    
    setLoading(true);
    setError(null);
    
    try {
      const response = await experimentService.runBoostExperiment(boostConfig);
      
      if (response.error) {
        setError(response.message);
      } else {
        // Set results in a format that can be displayed
        setResults({
          type: 'boost',
          ...response
        });
      }
    } catch (err) {
      console.error('Boost experiment error:', err);
      setError(`Failed to run boost experiment: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  // Format source name for display
  const formatSourceName = (source) => {
    switch(source) {
      case 'ads':
        return 'NASA ADS / SciX';
      case 'scholar':
        return 'Google Scholar';
      case 'semanticScholar':
        return 'Semantic Scholar';
      case 'webOfScience':
        return 'Web of Science';
      default:
        return source;
    }
  };

  // Format metric name for display
  const formatMetricName = (metric) => {
    switch(metric) {
      case 'jaccard':
        return 'Jaccard Similarity';
      case 'rankBiased':
      case 'rank_biased':
        return 'Rank-Biased Overlap';
      case 'cosine':
        return 'Cosine Similarity';
      case 'euclidean':
        return 'Euclidean Distance';
      default:
        return metric.replace(/_/g, ' ').split(' ').map(word => 
          word.charAt(0).toUpperCase() + word.slice(1)
        ).join(' ');
    }
  };

  // Helper function to get metric description
  const getMetricDescription = (metric) => {
    switch(metric) {
      case 'jaccard':
        return 'Measures the similarity between finite sample sets, and is defined as the size of the intersection divided by the size of the union of the sample sets.';
      case 'rankBiased':
      case 'rank_biased':
        return 'Rank-Biased Overlap (RBO) measures the similarity between two ranked lists, weighting items towards the top of the lists more heavily.';
      case 'cosine':
        return 'Measures the cosine of the angle between two vectors, representing how similar the two vectors are irrespective of their size.';
      case 'euclidean':
        return 'Measures the straight-line distance between two points in Euclidean space.';
      default:
        return 'No description available for this metric.';
    }
  };

  // Add a new function to handle running a new search with custom weights
  const handleRunNewSearchWithWeights = async (transformedQuery, boostConfig) => {
    if (!transformedQuery.trim()) {
      setError("Please enter a search query");
      return Promise.reject(new Error("Empty query"));
    }
    
    // Store current Google Scholar results if available to preserve them
    const currentScholarResults = results?.results?.scholar || [];
    const currentOriginResults = results?.results?.origin || [];
    
    setLoading(true);
    setError(null);
    
    try {
      const selectedSources = Object.keys(sources).filter(key => sources[key]);
      const selectedMetrics = Object.keys(metrics).filter(key => metrics[key]);
      
      // Always include all fields since we removed the fields selection UI
      const selectedFields = ['title', 'abstract', 'authors', 'doi', 'year', 'citation_count'];
      
      // Clean the transformedQuery to make sure it doesn't get too complex on repeated applications
      let cleanQuery = transformedQuery;
      
      // If this looks like a complex query, log it for debugging
      if (transformedQuery.includes("^") || (transformedQuery.match(/:/g) || []).length > 1) {
        console.log("Complex transformed query:", transformedQuery);
      }
      
      const requestBody = {
        query: cleanQuery, // Use the transformed query with field weights
        sources: selectedSources,
        metrics: selectedMetrics,
        fields: selectedFields,
        originalQuery: query, // Include the original query for reference
        useTransformedQuery: true // Flag to indicate this is a transformed query
      };

      const response = await searchService.compareSearchResults(requestBody);
      
      if (response.error) {
        setError(response.message);
        return Promise.reject(new Error(response.message));
      } else {
        // Make a copy of the response to avoid mutation issues
        const modifiedResponse = JSON.parse(JSON.stringify(response));
        
        // If we had Google Scholar results before, always preserve them
        if (currentScholarResults.length > 0) {
          console.log("Restoring Google Scholar results from previous search");
          if (!modifiedResponse.results) {
            modifiedResponse.results = {};
          }
          modifiedResponse.results.scholar = currentScholarResults;
        }
        
        // If field boosts were applied, we need to preserve the original results
        // to ensure proper comparison
        if (boostConfig && 
            boostConfig.fieldBoosts && 
            Object.values(boostConfig.fieldBoosts).some(v => v > 0)) {
          console.log("Field boosts detected, preserving original results");
          
          // If we have original results and the response doesn't have them for some reason
          if (currentOriginResults.length > 0 && results?.originalResults?.length > 0) {
            console.log("Restoring original results for comparison");
            modifiedResponse.originalResults = results.originalResults;
          }
        }
        
        setResults(modifiedResponse);
        return Promise.resolve(modifiedResponse);
      }
    } catch (err) {
      console.error('Search error:', err);
      const errorMessage = `Failed to fetch results: ${err.message}`;
      setError(errorMessage);
      return Promise.reject(new Error(errorMessage));
    } finally {
      setLoading(false);
    }
  };

  // Experiment Tabs rendering
  const renderExperimentTabs = () => {
    console.log('renderExperimentTabs called, current tab:', experimentTab);
    return (
      <>
        <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 2, width: '100%' }}>
          <Tabs
            value={experimentTab}
            onChange={handleExperimentTabChange}
            aria-label="experiment tabs"
            variant="fullWidth"
            sx={{ mb: 0 }}
          >
            <Tab label="Boost Experiment" value={0} />
            <Tab label="Quepid Evaluation" value={1} />
            <Tab label="Similarity Tests" value={2} />
            <Tab label="Query Intent" value={3} />
          </Tabs>
        </Box>
        
        {experimentTab === 0 && (
          <Box>
            <Typography variant="h5" gutterBottom>
              Boost Experiment
            </Typography>
            <Typography paragraph>
              Apply configurable boost factors to search results based on citation count, publication year, document type, and more.
              See how different boost configurations affect the ranking of results.
            </Typography>
            <BoostExperiment 
              originalResults={results && results.results ? Object.values(results.results)[0] || [] : []}
              query={results ? results.query : ''}
              API_URL={API_URL}
              onRunNewSearch={handleRunNewSearchWithWeights}
              results={results}
            />
          </Box>
        )}
        
        {experimentTab === 1 && (
          <QuepidEvaluation />
        )}
        
        {experimentTab === 2 && (
          <>
            {console.log('Attempting to render SimilarityTests component')}
            <SimilarityTests />
          </>
        )}
        
        {experimentTab === 3 && (
          <QueryIntent />
        )}
      </>
    );
  };

  // The main application UI
  const AppContent = () => (
    <>
      <AppBar position="static">
        <Toolbar>
          <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
            SciX Search Comparisons
          </Typography>
          {isAuthenticated && (
            <>
              <IconButton
                size="large"
                edge="end"
                color="inherit"
                aria-label="account"
                aria-controls="menu-appbar"
                aria-haspopup="true"
                onClick={handleMenuClick}
              >
                <AccountCircleIcon />
              </IconButton>
              <Menu
                id="menu-appbar"
                anchorEl={anchorEl}
                open={openMenu}
                onClose={handleMenuClose}
                MenuListProps={{
                  'aria-labelledby': 'user-button',
                }}
              >
                <MenuItem onClick={handleLogout}>
                  <ExitToAppIcon fontSize="small" sx={{ mr: 1 }} />
                  Logout
                </MenuItem>
              </Menu>
            </>
          )}
        </Toolbar>
        <Tabs 
          value={mainTab} 
          onChange={handleMainTabChange}
          variant="fullWidth"
          textColor="inherit"
          indicatorColor="secondary"
        >
          <Tab icon={<SearchIcon />} label="SEARCH" />
          <Tab icon={<ScienceIcon />} label="EXPERIMENTS" />
          <Tab icon={<InfoIcon />} label="ABOUT" />
        </Tabs>
      </AppBar>

      <Container maxWidth="lg">
        {/* Alert for errors */}
        {error && (
          <Alert severity="error" sx={{ mt: 2 }} onClose={() => setError(null)}>
            {error}
          </Alert>
        )}

        {/* Search Tab */}
        {mainTab === 0 && (
          <Box my={4}>
            <Paper elevation={3} sx={{ p: 3, mb: 4 }}>
              <Box component="form" noValidate autoComplete="off">
                <Grid container spacing={2}>
                  <Grid item xs={12}>
                    <StableInput
                      fullWidth
                      label="Search Query"
                      variant="outlined"
                      value={query}
                      onChange={(e) => {
                        setQuery(e.target.value);
                      }}
                      placeholder="Enter your academic search query"
                      debounceTime={500}
                    />
                  </Grid>
                  
                  <Grid item xs={12} sm={4}>
                    <Typography variant="subtitle1">Search Sources</Typography>
                    <FormGroup>
                      <FormControlLabel
                        control={<Checkbox checked={sources.ads} onChange={handleSourceChange} name="ads" />}
                        label="ADS/SciX"
                      />
                      <FormControlLabel
                        control={<Checkbox checked={sources.scholar} onChange={handleSourceChange} name="scholar" />}
                        label="Google Scholar"
                      />
                      <FormControlLabel
                        control={<Checkbox checked={sources.semanticScholar} onChange={handleSourceChange} name="semanticScholar" />}
                        label="Semantic Scholar"
                      />
                      <FormControlLabel
                        control={<Checkbox checked={sources.webOfScience} onChange={handleSourceChange} name="webOfScience" />}
                        label="Web of Science"
                      />
                    </FormGroup>
                  </Grid>
                  
                  <Grid item xs={12} sm={4}>
                    <Typography variant="subtitle1">Similarity Metrics</Typography>
                    <FormGroup>
                      <FormControlLabel
                        control={<Checkbox checked={metrics.jaccard} onChange={handleMetricsChange} name="jaccard" />}
                        label="Jaccard Similarity"
                      />
                      <FormControlLabel
                        control={<Checkbox checked={metrics.rankBiased} onChange={handleMetricsChange} name="rankBiased" />}
                        label="Rank-Biased Overlap"
                      />
                    </FormGroup>
                  </Grid>
                  
                  <Grid item xs={12}>
                    <Button
                      variant="contained"
                      color="primary"
                      onClick={handleSearch}
                      disabled={loading}
                      fullWidth
                    >
                      {loading ? <CircularProgress size={24} /> : "Compare Search Results"}
                    </Button>
                  </Grid>
                </Grid>
              </Box>
            </Paper>

            {/* Display search results if available */}
            {results && results.type !== 'boost' && (
              <Box mt={4}>
                <Typography variant="h5" gutterBottom>
                  Search Results
                </Typography>
                
                {Object.keys(results.results).length > 0 && (
                  <Box>
                    <Paper elevation={3} sx={{ mb: 3 }}>
                      <Tabs 
                        value={resultTab || 0} 
                        onChange={(e, newValue) => setResultTab(newValue)}
                        variant="fullWidth"
                        textColor="primary"
                        indicatorColor="primary"
                      >
                        <Tab label="Results by Source" id="result-tab-0" />
                        <Tab label="Comparison" id="result-tab-1" />
                        <Tab label="Visualization" id="result-tab-2" />
                      </Tabs>
                      
                      <Box sx={{ p: 2 }}>
                        {/* Results by Source Tab */}
                        {resultTab === 0 && (
                          <Box>
                            <Typography variant="h6" gutterBottom>
                              Results by Source
                            </Typography>
                            {/* Source-specific results... */}
                            {Object.keys(results.results).length > 0 && (
                              <Box>
                                <Box sx={{ mb: 2, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                  <Typography variant="subtitle1">
                                    Showing results for: <strong>{results.query}</strong>
                                  </Typography>
                                  <StableInput
                                    size="small"
                                    variant="outlined"
                                    placeholder="Filter results..."
                                    value={filterText}
                                    onChange={(e) => {
                                      setFilterText(e.target.value);
                                    }}
                                    sx={{ width: 250 }}
                                  />
                                </Box>
                                
                                {/* Side by Side Grid Layout */}
                                <Grid container spacing={2}>
                                  {Object.keys(results.results).map(source => {
                                    const sourceResults = results.results[source];
                                    const filteredResults = filterText
                                      ? sourceResults.filter(result => 
                                          result.title.toLowerCase().includes(filterText.toLowerCase()) ||
                                          (result.abstract && result.abstract.toLowerCase().includes(filterText.toLowerCase())) ||
                                          (result.authors && result.authors.some(author => 
                                            author && author.toLowerCase().includes(filterText.toLowerCase())
                                          ))
                                        )
                                      : sourceResults;
                                      
                                    return (
                                      <Grid item xs={12} sm={6} md={4} lg={3} key={source}>
                                        <Paper 
                                          elevation={3} 
                                          sx={{ 
                                            height: { xs: 400, sm: 500, md: 550, lg: 600 }, 
                                            display: 'flex', 
                                            flexDirection: 'column',
                                            overflow: 'hidden'
                                          }}
                                        >
                                          <Box sx={{ 
                                            p: 1, 
                                            bgcolor: 
                                              source === 'ads' ? 'primary.main' :
                                              source === 'scholar' ? 'error.main' :
                                              source === 'semanticScholar' ? 'warning.main' : 'success.main',
                                            color: 'white',
                                            borderTopLeftRadius: 4,
                                            borderTopRightRadius: 4,
                                            display: 'flex',
                                            justifyContent: 'space-between',
                                            alignItems: 'center',
                                            position: 'sticky',
                                            top: 0,
                                            zIndex: 1
                                          }}>
                                            <Typography variant="subtitle1" sx={{ fontWeight: 'bold' }}>
                                              {formatSourceName(source)}
                                            </Typography>
                                            <Chip 
                                              label={`${filteredResults.length} results`}
                                              size="small"
                                              sx={{ 
                                                bgcolor: 'rgba(255,255,255,0.2)', 
                                                color: 'white',
                                                '& .MuiChip-label': { fontWeight: 'bold' }
                                              }} 
                                            />
                                          </Box>
                                          
                                          <Box sx={{ 
                                            flexGrow: 1, 
                                            overflow: 'auto', 
                                            maxHeight: { 
                                              xs: 'calc(400px - 48px)', 
                                              sm: 'calc(500px - 48px)', 
                                              md: 'calc(550px - 48px)', 
                                              lg: 'calc(600px - 48px)' 
                                            }
                                          }}>
                                            <List disablePadding>
                                              {filteredResults.map((result, idx) => (
                                                <Tooltip
                                                  key={idx}
                                                  title={
                                                    <Box sx={{ p: 1, maxWidth: 400 }}>
                                                      {/* Title */}
                                                      <Typography variant="subtitle2" gutterBottom>
                                                        {result.title}
                                                      </Typography>
                                                      
                                                      <Divider sx={{ my: 1 }} />
                                                      
                                                      {/* Key metadata in a single line */}
                                                      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, mb: 1 }}>
                                                        {result.year && (
                                                          <Chip 
                                                            size="small" 
                                                            label={`Year: ${result.year}`} 
                                                            sx={{ fontSize: '0.7rem' }}
                                                          />
                                                        )}
                                                        {(result.citation_count !== undefined && result.citation_count !== null) && (
                                                          <Chip 
                                                            size="small" 
                                                            label={`Citations: ${result.citation_count}`} 
                                                            sx={{ fontSize: '0.7rem' }}
                                                          />
                                                        )}
                                                        {result.doi && (
                                                          <Chip 
                                                            size="small" 
                                                            label={`DOI: ${result.doi.substring(0, 15)}...`} 
                                                            sx={{ fontSize: '0.7rem' }}
                                                          />
                                                        )}
                                                      </Box>
                                                      
                                                      {/* Authors - condensed */}
                                                      {result.authors && result.authors.length > 0 && (
                                                        <Typography variant="caption" sx={{ display: 'block', mb: 1 }}>
                                                          <strong>Authors:</strong> {Array.isArray(result.authors) 
                                                            ? result.authors.slice(0, 3).join(', ') + (result.authors.length > 3 ? ', et al.' : '')
                                                            : result.authors}
                                                        </Typography>
                                                      )}
                                                      
                                                      {/* Abstract snippet */}
                                                      {result.abstract && (
                                                        <Typography variant="caption" sx={{ display: 'block' }}>
                                                          <strong>Abstract:</strong> {result.abstract.length > 300 
                                                            ? `${result.abstract.substring(0, 300)}...` 
                                                            : result.abstract}
                                                        </Typography>
                                                      )}
                                                    </Box>
                                                  }
                                                  arrow
                                                  placement="right"
                                                  componentsProps={{
                                                    tooltip: {
                                                      sx: { bgcolor: 'background.paper', color: 'text.primary', boxShadow: 3 }
                                                    }
                                                  }}
                                                >
                                                  <ListItem 
                                                    divider 
                                                    sx={{ 
                                                      '&:hover': { bgcolor: 'action.hover' },
                                                      px: 2, 
                                                      py: 1,
                                                      minHeight: 80,
                                                      maxHeight: 110
                                                    }}
                                                    secondaryAction={
                                                      result.url && (
                                                        <IconButton 
                                                          size="small" 
                                                          href={result.url} 
                                                          target="_blank" 
                                                          aria-label="View source"
                                                          sx={{ ml: 1 }}
                                                        >
                                                          <LaunchIcon fontSize="small" />
                                                        </IconButton>
                                                      )
                                                    }
                                                  >
                                                    <ListItemText
                                                      disableTypography
                                                      primary={
                                                        <Box sx={{ display: 'flex', alignItems: 'flex-start' }}>
                                                          <Chip 
                                                            label={result.rank} 
                                                            size="small" 
                                                            sx={{ 
                                                              mr: 1, 
                                                              minWidth: 28,
                                                              height: 20,
                                                              bgcolor: 
                                                                source === 'ads' ? 'primary.light' :
                                                                source === 'scholar' ? 'error.light' :
                                                                source === 'semanticScholar' ? 'warning.light' : 'success.light',
                                                            }} 
                                                          />
                                                          <Typography 
                                                            variant="body2" 
                                                            sx={{ 
                                                              fontWeight: 'medium',
                                                              display: '-webkit-box',
                                                              WebkitLineClamp: 2,
                                                              WebkitBoxOrient: 'vertical',
                                                              overflow: 'hidden',
                                                              lineHeight: 1.2,
                                                              mb: 0.5
                                                            }}
                                                          >
                                                            {result.title}
                                                          </Typography>
                                                        </Box>
                                                      }
                                                      secondary={
                                                        <Box sx={{ mt: 0.5 }}>
                                                          {/* Authors + Year */}
                                                          <Typography 
                                                            variant="caption" 
                                                            sx={{ 
                                                              display: 'block',
                                                              color: 'text.secondary',
                                                              whiteSpace: 'nowrap',
                                                              overflow: 'hidden',
                                                              textOverflow: 'ellipsis'
                                                            }}
                                                          >
                                                            {Array.isArray(result.authors) 
                                                              ? result.authors.slice(0, 2).join(', ') + (result.authors.length > 2 ? ', et al.' : '') 
                                                              : result.authors}
                                                            {result.year ? ` (${result.year})` : ''}
                                                          </Typography>
                                                          
                                                          {/* Abstract preview */}
                                                          {result.abstract && (
                                                            <Typography 
                                                              variant="caption" 
                                                              sx={{ 
                                                                display: '-webkit-box',
                                                                WebkitLineClamp: 1,
                                                                WebkitBoxOrient: 'vertical',
                                                                overflow: 'hidden',
                                                                color: 'text.secondary',
                                                                lineHeight: 1.2,
                                                                mt: 0.5
                                                              }}
                                                            >
                                                              {result.abstract}
                                                            </Typography>
                                                          )}
                                                          
                                                          {/* Citations as a small indicator in bottom right */}
                                                          {(result.citation_count !== undefined && result.citation_count !== null) && (
                                                            <Box sx={{ 
                                                              display: 'flex', 
                                                              justifyContent: 'flex-end',
                                                              mt: 0.5  
                                                            }}>
                                                              <Chip
                                                                size="small"
                                                                label={`Cited: ${result.citation_count}`}
                                                                sx={{ 
                                                                  height: 16,
                                                                  fontSize: '0.6rem',
                                                                  '& .MuiChip-label': { px: 0.8 }
                                                                }}
                                                              />
                                                            </Box>
                                                          )}
                                                        </Box>
                                                      }
                                                    />
                                                  </ListItem>
                                                </Tooltip>
                                              ))}
                                            </List>
                                          </Box>
                                        </Paper>
                                      </Grid>
                                    );
                                  })}
                                </Grid>
                              </Box>
                            )}
                          </Box>
                        )}

                        {/* Results Comparison Tab */}
                        {resultTab === 1 && (
                          <Box>
                            <Typography variant="h6" gutterBottom>
                              Results Comparison
                            </Typography>
                            {/* Display the similarity metrics */}
                            {results.comparison && results.comparison.similarity && (
                              <Box>
                                <Typography variant="h6" gutterBottom>
                                  Similarity Metrics
                                </Typography>
                                
                                {/* Metrics explanation */}
                                <Box sx={{ mb: 3, p: 2, bgcolor: 'background.paper', borderRadius: 1, border: '1px solid #eee' }}>
                                  <Typography variant="subtitle2" gutterBottom>
                                    Understanding the Metrics:
                                  </Typography>
                                  <Typography variant="body2">
                                    <strong>Overlap:</strong> Records are matched by DOI (when available) or by title. The total shows unique matching papers.
                                  </Typography>
                                  <Typography variant="body2">
                                    <strong>Same Rank:</strong> Papers that appear at the same rank position in both source results (e.g., paper appears as #3 in both sources).
                                  </Typography>
                                  <Typography variant="body2">
                                    <strong>Jaccard Similarity:</strong> Measures overlap regardless of ranking - number of shared records divided by total unique records from both sources.
                                  </Typography>
                                  <Typography variant="body2">
                                    <strong>Rank-Biased Overlap:</strong> Measures similarity considering the ranking of results, giving more weight to matches at higher positions.
                                  </Typography>
                                </Box>
                                
                                <TableContainer>
                                  <Table size="small">
                                    <TableHead>
                                      <TableRow>
                                        <TableCell>Sources</TableCell>
                                        <TableCell align="center">Total Overlap</TableCell>
                                        <TableCell align="center">Breakdown</TableCell>
                                        <TableCell align="center">Same Rank</TableCell>
                                        <TableCell align="right">
                                          <Tooltip title={getMetricDescription('jaccard')}>
                                            <Typography variant="body2" display="inline" sx={{ cursor: 'help', textDecoration: 'underline', textDecorationStyle: 'dotted' }}>
                                              Jaccard Similarity
                                            </Typography>
                                          </Tooltip>
                                        </TableCell>
                                        <TableCell align="right">
                                          <Tooltip title={getMetricDescription('rankBiased')}>
                                            <Typography variant="body2" display="inline" sx={{ cursor: 'help', textDecoration: 'underline', textDecorationStyle: 'dotted' }}>
                                              Rank-Biased Overlap
                                            </Typography>
                                          </Tooltip>
                                        </TableCell>
                                      </TableRow>
                                    </TableHead>
                                    <TableBody>
                                      {Object.entries(results.comparison.overlap).map(([key, stats]) => {
                                        const [source1, source2] = key.split('_vs_');
                                        const sourceNames = [formatSourceName(source1), formatSourceName(source2)];
                                        const comparisonLabel = `${sourceNames[0]} vs ${sourceNames[1]}`;
                                        
                                        // Calculate metrics
                                        const jaccardValue = results.comparison.similarity?.jaccard?.[key];
                                        const rankBiasedValue = results.comparison.similarity?.rankBiased?.[key];
                                        
                                        const doiMatches = stats.matching_dois?.length || 0;
                                        const titleMatches = stats.all_matching_titles?.length || 0;
                                        const sameRankCount = stats.same_rank_count || 0;
                                        
                                        return (
                                          <TableRow key={key}>
                                            <TableCell>{comparisonLabel}</TableCell>
                                            <TableCell align="center">
                                              <Chip 
                                                label={stats.overlap}
                                                size="small" 
                                                color="success"
                                                sx={{ fontWeight: 'bold' }}
                                              />
                                            </TableCell>
                                            <TableCell align="center">
                                              <Typography variant="caption">
                                                {doiMatches} by DOI, {titleMatches} by title
                                              </Typography>
                                            </TableCell>
                                            <TableCell align="center">
                                              <Tooltip title="Papers that appear at the same rank position in both sources">
                                                <Chip 
                                                  label={sameRankCount}
                                                  size="small" 
                                                  color="info"
                                                  sx={{ fontWeight: 'bold' }}
                                                />
                                              </Tooltip>
                                            </TableCell>
                                            <TableCell align="right">
                                              <strong>{jaccardValue !== undefined ? jaccardValue.toFixed(4) : '0.0000'}</strong>
                                            </TableCell>
                                            <TableCell align="right">
                                              <strong>{rankBiasedValue !== undefined ? rankBiasedValue.toFixed(4) : '0.0000'}</strong>
                                            </TableCell>
                                          </TableRow>
                                        );
                                      })}
                                    </TableBody>
                                  </Table>
                                </TableContainer>
                              </Box>
                            )}
                          </Box>
                        )}

                        {/* Visualization Tab */}
                        {resultTab === 2 && (
                          <Box>
                            <Typography variant="h6" gutterBottom>
                              Visualization
                            </Typography>
                            <Typography variant="body2" sx={{ mb: 2 }}>
                              Visual representation of search result similarity across different sources.
                            </Typography>
                            
                            {results.comparison && results.comparison.similarity && (
                              <Box>
                                <Typography variant="h6" gutterBottom>
                                  Similarity Metrics Visualization
                                </Typography>
                                
                                <Paper elevation={2} sx={{ p: 2, mb: 3 }}>
                                  <Typography variant="subtitle2" gutterBottom>
                                    About this visualization:
                                  </Typography>
                                  <Typography variant="body2">
                                    These bar charts show the Jaccard similarity and Rank-Biased Overlap (RBO) metrics between ADS/SciX and other search engines.
                                    Higher values indicate greater similarity between result sets.
                                  </Typography>
                                  <Alert severity="info" sx={{ mt: 1 }}>
                                    <Typography variant="body2" sx={{ fontWeight: 'medium' }}>
                                      Current Query: <strong>{results.query}</strong>
                                    </Typography>
                                    <Typography variant="body2" sx={{ mt: 0.5, fontStyle: 'italic' }}>
                                      In future versions, multiple queries will be displayed with different patterns to identify trends in search engine behavior across query types.
                                    </Typography>
                                  </Alert>
                                </Paper>

                                {/* Jaccard Similarity Bar Chart */}
                                <Paper elevation={2} sx={{ p: 2, mb: 3 }}>
                                  <Typography variant="subtitle1" gutterBottom color="primary">
                                    Jaccard Similarity
                                  </Typography>
                                  <Typography variant="body2" sx={{ mb: 2 }}>
                                    Jaccard similarity measures the proportion of shared results regardless of ranking position.
                                  </Typography>
                                  
                                  <Box sx={{ height: 300, position: 'relative', border: '1px solid #eee', borderRadius: 1, p: 2, mb: 2 }}>
                                    {/* Y-axis */}
                                    <Box sx={{ 
                                      position: 'absolute', 
                                      left: 0, 
                                      top: 0, 
                                      bottom: 0, 
                                      width: 50, 
                                      display: 'flex', 
                                      flexDirection: 'column', 
                                      justifyContent: 'space-between', 
                                      alignItems: 'flex-end', 
                                      pr: 1,
                                      borderRight: '1px solid #eee' 
                                    }}>
                                      <Typography variant="caption">1.0</Typography>
                                      <Typography variant="caption">0.8</Typography>
                                      <Typography variant="caption">0.6</Typography>
                                      <Typography variant="caption">0.4</Typography>
                                      <Typography variant="caption">0.2</Typography>
                                      <Typography variant="caption">0.0</Typography>
                                    </Box>
                                    
                                    {/* X-axis labels */}
                                    <Box sx={{ position: 'absolute', left: 50, right: 0, bottom: 0, height: 20, display: 'flex', justifyContent: 'space-around', alignItems: 'center' }}>
                                      <Typography variant="caption">ADS vs Google Scholar</Typography>
                                      <Typography variant="caption">ADS vs Semantic Scholar</Typography>
                                      <Typography variant="caption">ADS vs Web of Science</Typography>
                                    </Box>
                                    
                                    {/* Bar Chart area */}
                                    <Box sx={{ position: 'absolute', left: 50, right: 0, top: 0, bottom: 20, display: 'flex', alignItems: 'flex-end', justifyContent: 'space-around' }}>
                                      {/* Process data for bar chart */}
                                      {(() => {
                                        // Define the comparison pairs we want to show
                                        const comparisonPairs = [
                                          { key: 'ads_vs_scholar', label: 'ADS vs Google Scholar', color: 'error.main' },
                                          { key: 'ads_vs_semanticScholar', label: 'ADS vs Semantic Scholar', color: 'warning.main' },
                                          { key: 'ads_vs_webOfScience', label: 'ADS vs Web of Science', color: 'success.main' }
                                        ];
                                        
                                        return comparisonPairs.map(pair => {
                                          // Handle both directions (ads_vs_x or x_vs_ads)
                                          const alt1 = pair.key;
                                          const alt2 = pair.key.split('_vs_').reverse().join('_vs_');
                                          
                                          // Get value from either direction
                                          const value = results.comparison.similarity.jaccard?.[alt1] || 
                                                     results.comparison.similarity.jaccard?.[alt2] || 
                                                     0;
                                          
                                          // Calculate bar height based on value
                                          const barHeight = `${value * 100}%`;
                                          
                                          return (
                                            <Tooltip
                                              key={pair.key}
                                              title={`${pair.label}: ${value.toFixed(4)} (Query: "${results.query}")`}
                                              placement="top"
                                            >
                                              <Box
                                                sx={{
                                                  width: '20%',
                                                  height: barHeight,
                                                  bgcolor: pair.color,
                                                  borderRadius: '4px 4px 0 0',
                                                  transition: 'transform 0.2s',
                                                  cursor: 'pointer',
                                                  '&:hover': {
                                                    transform: 'scaleY(1.05)',
                                                    filter: 'brightness(1.1)'
                                                  }
                                                }}
                                              />
                                            </Tooltip>
                                          );
                                        });
                                      })()}
                                    </Box>
                                  </Box>
                                  
                                  {/* Legend */}
                                  <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 2, justifyContent: 'center', mt: 2 }}>
                                    <Box sx={{ display: 'flex', alignItems: 'center' }}>
                                      <Box sx={{ width: 16, height: 10, bgcolor: 'error.main', mr: 1 }} />
                                      <Typography variant="caption">ADS vs Google Scholar</Typography>
                                    </Box>
                                    <Box sx={{ display: 'flex', alignItems: 'center' }}>
                                      <Box sx={{ width: 16, height: 10, bgcolor: 'warning.main', mr: 1 }} />
                                      <Typography variant="caption">ADS vs Semantic Scholar</Typography>
                                    </Box>
                                    <Box sx={{ display: 'flex', alignItems: 'center' }}>
                                      <Box sx={{ width: 16, height: 10, bgcolor: 'success.main', mr: 1 }} />
                                      <Typography variant="caption">ADS vs Web of Science</Typography>
                                    </Box>
                                  </Box>
                                </Paper>
                                
                                {/* Rank-Biased Overlap Bar Chart */}
                                <Paper elevation={2} sx={{ p: 2 }}>
                                  <Typography variant="subtitle1" gutterBottom color="primary">
                                    Rank-Biased Overlap
                                  </Typography>
                                  <Typography variant="body2" sx={{ mb: 2 }}>
                                    Rank-Biased Overlap considers the order of results, giving higher weight to matches at the top of result lists.
                                  </Typography>
                                  
                                  <Box sx={{ height: 300, position: 'relative', border: '1px solid #eee', borderRadius: 1, p: 2, mb: 2 }}>
                                    {/* Y-axis */}
                                    <Box sx={{ 
                                      position: 'absolute', 
                                      left: 0, 
                                      top: 0, 
                                      bottom: 0, 
                                      width: 50, 
                                      display: 'flex', 
                                      flexDirection: 'column', 
                                      justifyContent: 'space-between', 
                                      alignItems: 'flex-end', 
                                      pr: 1,
                                      borderRight: '1px solid #eee' 
                                    }}>
                                      <Typography variant="caption">1.0</Typography>
                                      <Typography variant="caption">0.8</Typography>
                                      <Typography variant="caption">0.6</Typography>
                                      <Typography variant="caption">0.4</Typography>
                                      <Typography variant="caption">0.2</Typography>
                                      <Typography variant="caption">0.0</Typography>
                                    </Box>
                                    
                                    {/* X-axis labels */}
                                    <Box sx={{ position: 'absolute', left: 50, right: 0, bottom: 0, height: 20, display: 'flex', justifyContent: 'space-around', alignItems: 'center' }}>
                                      <Typography variant="caption">ADS vs Google Scholar</Typography>
                                      <Typography variant="caption">ADS vs Semantic Scholar</Typography>
                                      <Typography variant="caption">ADS vs Web of Science</Typography>
                                    </Box>
                                    
                                    {/* Grid lines */}
                                    <Box sx={{ position: 'absolute', left: 50, right: 0, top: 0, bottom: 20, display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
                                      {[0, 0.2, 0.4, 0.6, 0.8, 1].map((line) => (
                                        <Box key={line} sx={{ borderBottom: line < 1 ? '1px dashed #ddd' : 'none', width: '100%', height: 0 }} />
                                      ))}
                                    </Box>
                                    
                                    {/* Bar Chart area */}
                                    <Box sx={{ position: 'absolute', left: 50, right: 0, top: 0, bottom: 20, display: 'flex', alignItems: 'flex-end', justifyContent: 'space-around' }}>
                                      {/* Process data for bar chart */}
                                      {(() => {
                                        // Define the comparison pairs we want to show
                                        const comparisonPairs = [
                                          { key: 'ads_vs_scholar', label: 'ADS vs Google Scholar', color: 'error.main' },
                                          { key: 'ads_vs_semanticScholar', label: 'ADS vs Semantic Scholar', color: 'warning.main' },
                                          { key: 'ads_vs_webOfScience', label: 'ADS vs Web of Science', color: 'success.main' }
                                        ];
                                        
                                        return comparisonPairs.map(pair => {
                                          // Handle both directions (ads_vs_x or x_vs_ads)
                                          const alt1 = pair.key;
                                          const alt2 = pair.key.split('_vs_').reverse().join('_vs_');
                                          
                                          // Get value from either direction
                                          const value = results.comparison.similarity.rankBiased?.[alt1] || 
                                                       results.comparison.similarity.rankBiased?.[alt2] || 
                                                       0;
                                          
                                          // Calculate bar height based on value
                                          const barHeight = `${value * 100}%`;
                                          
                                          return (
                                            <Tooltip
                                              key={pair.key}
                                              title={`${pair.label}: ${value.toFixed(4)} (Query: "${results.query}")`}
                                              placement="top"
                                            >
                                              <Box
                                                sx={{
                                                  width: '20%',
                                                  height: barHeight,
                                                  bgcolor: pair.color,
                                                  borderRadius: '4px 4px 0 0',
                                                  transition: 'transform 0.2s',
                                                  cursor: 'pointer',
                                                  '&:hover': {
                                                    transform: 'scaleY(1.05)',
                                                    filter: 'brightness(1.1)'
                                                  }
                                                }}
                                              />
                                            </Tooltip>
                                          );
                                        });
                                      })()}
                                    </Box>
                                  </Box>
                                  
                                  {/* Legend */}
                                  <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 2, justifyContent: 'center', mt: 2 }}>
                                    <Box sx={{ display: 'flex', alignItems: 'center' }}>
                                      <Box sx={{ width: 16, height: 10, bgcolor: 'error.main', mr: 1 }} />
                                      <Typography variant="caption">ADS vs Google Scholar</Typography>
                                    </Box>
                                    <Box sx={{ display: 'flex', alignItems: 'center' }}>
                                      <Box sx={{ width: 16, height: 10, bgcolor: 'warning.main', mr: 1 }} />
                                      <Typography variant="caption">ADS vs Semantic Scholar</Typography>
                                    </Box>
                                    <Box sx={{ display: 'flex', alignItems: 'center' }}>
                                      <Box sx={{ width: 16, height: 10, bgcolor: 'success.main', mr: 1 }} />
                                      <Typography variant="caption">ADS vs Web of Science</Typography>
                                    </Box>
                                  </Box>
                                </Paper>
                              </Box>
                            )}
                            
                            {(!results.comparison || !results.comparison.similarity) && (
                              <Box sx={{ height: 300, display: 'flex', justifyContent: 'center', alignItems: 'center', flexDirection: 'column' }}>
                                <Typography variant="h6" color="text.secondary" gutterBottom>
                                  No data to visualize
                                </Typography>
                                <Typography variant="body2" color="text.secondary">
                                  Run a search across multiple sources to see similarity metrics visualized here.
                                </Typography>
                              </Box>
                            )}
                          </Box>
                        )}
                      </Box>
                    </Paper>
                  </Box>
                )}
                {Object.keys(results.results).length === 0 && (
                  <Alert severity="info">No results found for the given query and sources.</Alert>
                )}
              </Box>
            )}
          </Box>
        )}

        {/* Experiments Tab */}
        {mainTab === 1 && (
          <Box my={4}>
            <Paper elevation={3} sx={{ p: 3, mb: 4 }}>
              <Typography variant="h5" gutterBottom color="primary">
                Search Experiments
              </Typography>
              <Typography paragraph>
                Select an experiment type from the tabs below:
              </Typography>
              {renderExperimentTabs()}
            </Paper>
          </Box>
        )}

        {/* About Tab */}
        {mainTab === 2 && (
          <Box my={4}>
            <Paper elevation={3} sx={{ p: 3 }}>
              <Typography variant="h5" gutterBottom>
                About Search Comparisons
              </Typography>
              <Typography variant="body1" paragraph>
                This application allows you to compare search results across multiple academic search engines,
                including ADS/SciX, Google Scholar, Semantic Scholar, and Web of Science.
              </Typography>
              <Typography variant="body1" paragraph>
                Features include:
              </Typography>
              <ul>
                <li>Compare results across multiple sources</li>
                <li>Analyze similarity between result sets</li>
                <li>Experiment with boosting factors to improve rankings</li>
                <li>Perform A/B testing of different search algorithms</li>
                <li>Debug tools for API testing and diagnostics</li>
              </ul>
              <Typography variant="body1" paragraph>
                Version: {APP_VERSION}
              </Typography>
              <Typography variant="body1">
                Backend API: {API_URL}
              </Typography>
            </Paper>
          </Box>
        )}
      </Container>
    </>
  );

  return (
    <Routes>
      <Route path="/login" element={
        isAuthenticated ? <Navigate to="/" /> : <Login onLogin={login} correctPassword={DEFAULT_PASSWORD} />
      } />
      <Route path="/" element={
        <ProtectedRoute>
          <Container maxWidth="xl">
            <AppContent />
          </Container>
        </ProtectedRoute>
      } />
      <Route path="*" element={<Navigate to="/" />} />
    </Routes>
  );
}

export default App; 
import React, { useState, useEffect } from 'react';
import { 
  Container, Box, Typography, TextField, Button, 
  Checkbox, FormControlLabel, FormGroup, Grid, 
  CircularProgress, Paper, Tabs, Tab, Divider, Alert,
  IconButton, AppBar, Toolbar
} from '@mui/material';
import InfoIcon from '@mui/icons-material/Info';
import BugReportIcon from '@mui/icons-material/BugReport';
import ScienceIcon from '@mui/icons-material/Science';
import SearchIcon from '@mui/icons-material/Search';
import GitHubIcon from '@mui/icons-material/GitHub';

import { searchService, experimentService, debugService } from './services/api';

// Import components as needed
// These will be created in separate files

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';
const APP_VERSION = "1.0.0";
const DEBUG = process.env.REACT_APP_DEBUG === 'true';

function App() {
  // State for search query and options
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState(null);
  const [error, setError] = useState(null);
  const [mainTab, setMainTab] = useState(0);
  const [experimentTab, setExperimentTab] = useState(0);
  const [debugTab, setDebugTab] = useState(0);
  const [environmentInfo, setEnvironmentInfo] = useState(null);
  
  // State for source selection
  const [sources, setSources] = useState({
    ads: true,
    scholar: true,
    semanticScholar: false,
    webOfScience: false
  });
  
  // State for similarity metrics selection
  const [metrics, setMetrics] = useState({
    exact_match: true,
    rank_correlation: true,
    content_similarity: false
  });
  
  // State for metadata fields to compare
  const [fields, setFields] = useState({
    title: true,
    abstract: true,
    authors: false,
    doi: true,
    year: false
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
  
  // A/B test state
  const [abTestVariation, setAbTestVariation] = useState('B');

  // Debug state
  const [sourcesList, setSourcesList] = useState(null);
  const [pingResults, setPingResults] = useState({});
  const [testSearchResults, setTestSearchResults] = useState(null);

  // Load environment info on startup
  useEffect(() => {
    const fetchEnvironmentInfo = async () => {
      try {
        const envInfo = await debugService.getEnvironmentInfo();
        if (!envInfo.error) {
          setEnvironmentInfo(envInfo);
        }
      } catch (error) {
        console.error("Failed to fetch environment info:", error);
      }
    };

    if (DEBUG) {
      fetchEnvironmentInfo();
    }
  }, []);

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
    setExperimentTab(newValue);
  };

  const handleDebugTabChange = (event, newValue) => {
    setDebugTab(newValue);
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
      const selectedFields = Object.keys(fields).filter(key => fields[key]);
      
      const requestBody = {
        query,
        sources: selectedSources,
        metrics: selectedMetrics,
        fields: selectedFields
      };

      if (DEBUG) {
        console.log('Making search request:', requestBody);
      }
      
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
      if (DEBUG) {
        console.log('Running boost experiment with config:', boostConfig);
      }
      
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

  // Run A/B test
  const handleRunAbTest = async () => {
    if (!query.trim()) {
      setError("Please enter a search query for the A/B test");
      return;
    }
    
    setLoading(true);
    setError(null);
    
    try {
      const selectedSources = Object.keys(sources).filter(key => sources[key]);
      const selectedMetrics = Object.keys(metrics).filter(key => metrics[key]);
      const selectedFields = Object.keys(fields).filter(key => fields[key]);
      
      const requestBody = {
        query,
        sources: selectedSources,
        metrics: selectedMetrics,
        fields: selectedFields
      };

      if (DEBUG) {
        console.log('Running A/B test with config:', requestBody, 'Variation:', abTestVariation);
      }
      
      const response = await experimentService.runAbTest(requestBody, abTestVariation);
      
      if (response.error) {
        setError(response.message);
      } else {
        // Set results in a format that can be displayed
        setResults({
          type: 'abTest',
          ...response
        });
      }
    } catch (err) {
      console.error('A/B test error:', err);
      setError(`Failed to run A/B test: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  // List sources for debug
  const handleListSources = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await debugService.listSources();
      
      if (response.error) {
        setError(response.message);
      } else {
        setSourcesList(response);
      }
    } catch (err) {
      console.error('List sources error:', err);
      setError(`Failed to list sources: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  // Ping source for debug
  const handlePingSource = async (source) => {
    setLoading(true);
    setError(null);
    
    try {
      setPingResults({
        ...pingResults,
        [source]: { loading: true }
      });
      
      const response = await debugService.pingSource(source);
      
      if (response.error) {
        setPingResults({
          ...pingResults,
          [source]: { error: response.message }
        });
      } else {
        setPingResults({
          ...pingResults,
          [source]: response
        });
      }
    } catch (err) {
      console.error(`Ping source ${source} error:`, err);
      setPingResults({
        ...pingResults,
        [source]: { error: err.message }
      });
    } finally {
      setLoading(false);
    }
  };

  // Test search for debug
  const handleTestSearch = async (source) => {
    if (!query.trim()) {
      setError("Please enter a search query for testing");
      return;
    }
    
    setLoading(true);
    setError(null);
    
    try {
      const response = await debugService.testSearch(source, query);
      
      if (response.error) {
        setError(response.message);
      } else {
        setTestSearchResults(response);
      }
    } catch (err) {
      console.error('Test search error:', err);
      setError(`Failed to test search: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box sx={{ flexGrow: 1 }}>
      <AppBar position="static">
        <Toolbar>
          <SearchIcon sx={{ mr: 2 }} />
          <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
            Academic Search Engine Comparisons
          </Typography>
          {environmentInfo && (
            <Typography variant="caption" component="div" sx={{ mr: 2 }}>
              {environmentInfo.environment} v{APP_VERSION}
            </Typography>
          )}
          <IconButton 
            color="inherit" 
            href="https://github.com/yourusername/search-comparisons" 
            target="_blank"
            aria-label="GitHub repository"
          >
            <GitHubIcon />
          </IconButton>
        </Toolbar>
        <Tabs 
          value={mainTab} 
          onChange={handleMainTabChange}
          variant="fullWidth"
          textColor="inherit"
          indicatorColor="secondary"
        >
          <Tab icon={<SearchIcon />} label="SEARCH" id="tab-0" />
          <Tab icon={<ScienceIcon />} label="EXPERIMENTS" id="tab-1" />
          <Tab icon={<BugReportIcon />} label="DEBUG" id="tab-2" />
          <Tab icon={<InfoIcon />} label="ABOUT" id="tab-3" />
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
                    <TextField
                      fullWidth
                      label="Search Query"
                      variant="outlined"
                      value={query}
                      onChange={(e) => setQuery(e.target.value)}
                      placeholder="Enter your academic search query"
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
                        control={<Checkbox checked={metrics.exact_match} onChange={handleMetricsChange} name="exact_match" />}
                        label="Exact Match"
                      />
                      <FormControlLabel
                        control={<Checkbox checked={metrics.rank_correlation} onChange={handleMetricsChange} name="rank_correlation" />}
                        label="Rank Correlation"
                      />
                      <FormControlLabel
                        control={<Checkbox checked={metrics.content_similarity} onChange={handleMetricsChange} name="content_similarity" />}
                        label="Content Similarity"
                      />
                    </FormGroup>
                  </Grid>
                  
                  <Grid item xs={12} sm={4}>
                    <Typography variant="subtitle1">Metadata Fields</Typography>
                    <FormGroup>
                      <FormControlLabel
                        control={<Checkbox checked={fields.title} onChange={handleFieldsChange} name="title" />}
                        label="Title"
                      />
                      <FormControlLabel
                        control={<Checkbox checked={fields.abstract} onChange={handleFieldsChange} name="abstract" />}
                        label="Abstract"
                      />
                      <FormControlLabel
                        control={<Checkbox checked={fields.authors} onChange={handleFieldsChange} name="authors" />}
                        label="Authors"
                      />
                      <FormControlLabel
                        control={<Checkbox checked={fields.doi} onChange={handleFieldsChange} name="doi" />}
                        label="DOI"
                      />
                      <FormControlLabel
                        control={<Checkbox checked={fields.year} onChange={handleFieldsChange} name="year" />}
                        label="Publication Year"
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

            {/* Search Results would be displayed here */}
            {results && results.type !== 'boost' && results.type !== 'abTest' && (
              <Box mt={4}>
                <Typography variant="h5" gutterBottom>
                  Search Results
                </Typography>
                <Paper elevation={2} sx={{ p: 2 }}>
                  <pre>{JSON.stringify(results, null, 2)}</pre>
                </Paper>
              </Box>
            )}
          </Box>
        )}

        {/* Experiments Tab */}
        {mainTab === 1 && (
          <Box my={4}>
            <Paper elevation={3} sx={{ p: 3, mb: 4 }}>
              <Tabs
                value={experimentTab}
                onChange={handleExperimentTabChange}
                variant="fullWidth"
                textColor="primary"
                indicatorColor="primary"
              >
                <Tab label="Boost Search Results" id="exp-tab-0" />
                <Tab label="A/B Testing" id="exp-tab-1" />
                <Tab label="Log Analysis" id="exp-tab-2" />
              </Tabs>

              {/* Boost Experiment */}
              {experimentTab === 0 && (
                <Box mt={2}>
                  <Grid container spacing={2}>
                    <Grid item xs={12}>
                      <TextField
                        fullWidth
                        label="Search Query"
                        variant="outlined"
                        value={boostConfig.query}
                        onChange={(e) => setBoostConfig({...boostConfig, query: e.target.value})}
                        placeholder="Enter query for boost experiment"
                      />
                    </Grid>
                    
                    <Grid item xs={12} sm={6}>
                      <Typography variant="subtitle1">Boost Fields</Typography>
                      <FormGroup>
                        <FormControlLabel
                          control={
                            <Checkbox 
                              checked={boostConfig.boost_fields.includes('citation_count')} 
                              onChange={(e) => {
                                const fields = e.target.checked 
                                  ? [...boostConfig.boost_fields, 'citation_count']
                                  : boostConfig.boost_fields.filter(f => f !== 'citation_count');
                                setBoostConfig({...boostConfig, boost_fields: fields});
                              }} 
                            />
                          }
                          label="Citation Count"
                        />
                        <FormControlLabel
                          control={
                            <Checkbox 
                              checked={boostConfig.boost_fields.includes('year')} 
                              onChange={(e) => {
                                const fields = e.target.checked 
                                  ? [...boostConfig.boost_fields, 'year']
                                  : boostConfig.boost_fields.filter(f => f !== 'year');
                                setBoostConfig({...boostConfig, boost_fields: fields});
                              }} 
                            />
                          }
                          label="Publication Year"
                        />
                      </FormGroup>
                    </Grid>
                    
                    <Grid item xs={12} sm={6}>
                      <Typography variant="subtitle1">Boost Weights and Limits</Typography>
                      <Box mt={2}>
                        <TextField
                          label="Citation Count Weight"
                          type="number"
                          InputProps={{ inputProps: { min: 0, max: 1, step: 0.1 } }}
                          value={boostConfig.boost_weights.citation_count}
                          onChange={(e) => setBoostConfig({
                            ...boostConfig, 
                            boost_weights: {
                              ...boostConfig.boost_weights,
                              citation_count: Number(e.target.value)
                            }
                          })}
                          sx={{ mr: 2 }}
                        />
                        <TextField
                          label="Year Weight"
                          type="number"
                          InputProps={{ inputProps: { min: 0, max: 1, step: 0.1 } }}
                          value={boostConfig.boost_weights.year}
                          onChange={(e) => setBoostConfig({
                            ...boostConfig, 
                            boost_weights: {
                              ...boostConfig.boost_weights,
                              year: Number(e.target.value)
                            }
                          })}
                        />
                      </Box>
                      <Box mt={2}>
                        <TextField
                          label="Maximum Boost Factor"
                          type="number"
                          InputProps={{ inputProps: { min: 1, max: 10, step: 0.5 } }}
                          value={boostConfig.max_boost}
                          onChange={(e) => setBoostConfig({
                            ...boostConfig,
                            max_boost: Number(e.target.value)
                          })}
                        />
                      </Box>
                    </Grid>
                    
                    <Grid item xs={12}>
                      <Button
                        variant="contained"
                        color="primary"
                        onClick={handleRunBoostExperiment}
                        disabled={loading}
                        fullWidth
                      >
                        {loading ? <CircularProgress size={24} /> : "Run Boost Experiment"}
                      </Button>
                    </Grid>
                  </Grid>

                  {/* Boost Results would be displayed here */}
                  {results && results.type === 'boost' && (
                    <Box mt={4}>
                      <Typography variant="h5" gutterBottom>
                        Boost Experiment Results
                      </Typography>
                      <Paper elevation={2} sx={{ p: 2 }}>
                        <pre>{JSON.stringify(results, null, 2)}</pre>
                      </Paper>
                    </Box>
                  )}
                </Box>
              )}

              {/* A/B Testing */}
              {experimentTab === 1 && (
                <Box mt={2}>
                  <Grid container spacing={2}>
                    <Grid item xs={12}>
                      <TextField
                        fullWidth
                        label="Search Query"
                        variant="outlined"
                        value={query}
                        onChange={(e) => setQuery(e.target.value)}
                        placeholder="Enter query for A/B test"
                      />
                    </Grid>
                    
                    <Grid item xs={12} sm={6}>
                      <Typography variant="subtitle1">Test Variation</Typography>
                      <FormGroup>
                        <FormControlLabel
                          control={
                            <Checkbox 
                              checked={abTestVariation === 'A'} 
                              onChange={(e) => setAbTestVariation(e.target.checked ? 'A' : 'B')} 
                            />
                          }
                          label="Variation A (Default)"
                        />
                        <FormControlLabel
                          control={
                            <Checkbox 
                              checked={abTestVariation === 'B'} 
                              onChange={(e) => setAbTestVariation(e.target.checked ? 'B' : 'A')} 
                            />
                          }
                          label="Variation B (Experimental)"
                        />
                      </FormGroup>
                    </Grid>
                    
                    <Grid item xs={12} sm={6}>
                      <Typography variant="subtitle1">Source Selection</Typography>
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
                      </FormGroup>
                    </Grid>
                    
                    <Grid item xs={12}>
                      <Button
                        variant="contained"
                        color="primary"
                        onClick={handleRunAbTest}
                        disabled={loading}
                        fullWidth
                      >
                        {loading ? <CircularProgress size={24} /> : "Run A/B Test"}
                      </Button>
                    </Grid>
                  </Grid>

                  {/* A/B Test Results would be displayed here */}
                  {results && results.type === 'abTest' && (
                    <Box mt={4}>
                      <Typography variant="h5" gutterBottom>
                        A/B Test Results (Variation {results.variation})
                      </Typography>
                      <Paper elevation={2} sx={{ p: 2 }}>
                        <pre>{JSON.stringify(results, null, 2)}</pre>
                      </Paper>
                    </Box>
                  )}
                </Box>
              )}

              {/* Log Analysis */}
              {experimentTab === 2 && (
                <Box mt={2}>
                  <Grid container spacing={2}>
                    <Grid item xs={12}>
                      <Typography variant="body1">
                        This feature analyzes search logs to identify patterns, performance metrics, and user behavior.
                      </Typography>
                    </Grid>
                    
                    <Grid item xs={12}>
                      <Button
                        variant="contained"
                        color="primary"
                        onClick={async () => {
                          setLoading(true);
                          try {
                            const response = await experimentService.getLogAnalysis();
                            if (response.error) {
                              setError(response.message);
                            } else {
                              setResults({
                                type: 'logAnalysis',
                                ...response
                              });
                            }
                          } catch (err) {
                            setError(`Failed to get log analysis: ${err.message}`);
                          } finally {
                            setLoading(false);
                          }
                        }}
                        disabled={loading}
                        fullWidth
                      >
                        {loading ? <CircularProgress size={24} /> : "Analyze Logs"}
                      </Button>
                    </Grid>
                  </Grid>

                  {/* Log Analysis Results would be displayed here */}
                  {results && results.type === 'logAnalysis' && (
                    <Box mt={4}>
                      <Typography variant="h5" gutterBottom>
                        Log Analysis Results
                      </Typography>
                      <Paper elevation={2} sx={{ p: 2 }}>
                        <pre>{JSON.stringify(results, null, 2)}</pre>
                      </Paper>
                    </Box>
                  )}
                </Box>
              )}
            </Paper>
          </Box>
        )}

        {/* Debug Tab */}
        {mainTab === 2 && (
          <Box my={4}>
            <Paper elevation={3} sx={{ p: 3, mb: 4 }}>
              <Tabs
                value={debugTab}
                onChange={handleDebugTabChange}
                variant="fullWidth"
                textColor="primary"
                indicatorColor="primary"
              >
                <Tab label="Environment" id="debug-tab-0" />
                <Tab label="Sources" id="debug-tab-1" />
                <Tab label="Test Search" id="debug-tab-2" />
              </Tabs>

              {/* Environment Info */}
              {debugTab === 0 && (
                <Box mt={2}>
                  <Button
                    variant="contained"
                    color="primary"
                    onClick={async () => {
                      setLoading(true);
                      try {
                        const response = await debugService.getEnvironmentInfo();
                        if (response.error) {
                          setError(response.message);
                        } else {
                          setEnvironmentInfo(response);
                        }
                      } catch (err) {
                        setError(`Failed to get environment info: ${err.message}`);
                      } finally {
                        setLoading(false);
                      }
                    }}
                    disabled={loading}
                    sx={{ mb: 2 }}
                  >
                    {loading ? <CircularProgress size={24} /> : "Refresh Environment Info"}
                  </Button>

                  {environmentInfo && (
                    <Paper elevation={2} sx={{ p: 2 }}>
                      <Typography variant="h6" gutterBottom>
                        Environment Information
                      </Typography>
                      <pre>{JSON.stringify(environmentInfo, null, 2)}</pre>
                    </Paper>
                  )}
                </Box>
              )}

              {/* Sources Info */}
              {debugTab === 1 && (
                <Box mt={2}>
                  <Button
                    variant="contained"
                    color="primary"
                    onClick={handleListSources}
                    disabled={loading}
                    sx={{ mb: 2, mr: 2 }}
                  >
                    {loading ? <CircularProgress size={24} /> : "List Sources"}
                  </Button>

                  {sourcesList && sourcesList.sources && (
                    <Box>
                      <Typography variant="h6" gutterBottom>
                        Available Sources
                      </Typography>
                      <Paper elevation={2} sx={{ p: 2, mb: 2 }}>
                        <pre>{JSON.stringify(sourcesList.sources, null, 2)}</pre>
                      </Paper>
                      
                      <Typography variant="h6" gutterBottom>
                        Ping Sources
                      </Typography>
                      <Box display="flex" flexWrap="wrap" gap={2} mb={2}>
                        {Object.keys(sourcesList.sources).map(source => (
                          <Button
                            key={source}
                            variant="outlined"
                            onClick={() => handlePingSource(source)}
                            disabled={pingResults[source]?.loading}
                          >
                            {pingResults[source]?.loading ? (
                              <CircularProgress size={24} />
                            ) : (
                              `Ping ${source}`
                            )}
                          </Button>
                        ))}
                      </Box>
                      
                      {Object.keys(pingResults).length > 0 && (
                        <Paper elevation={2} sx={{ p: 2 }}>
                          <Typography variant="subtitle1" gutterBottom>
                            Ping Results
                          </Typography>
                          <pre>{JSON.stringify(pingResults, null, 2)}</pre>
                        </Paper>
                      )}
                    </Box>
                  )}
                </Box>
              )}

              {/* Test Search */}
              {debugTab === 2 && (
                <Box mt={2}>
                  <Grid container spacing={2}>
                    <Grid item xs={12}>
                      <TextField
                        fullWidth
                        label="Test Search Query"
                        variant="outlined"
                        value={query}
                        onChange={(e) => setQuery(e.target.value)}
                        placeholder="Enter query for testing"
                      />
                    </Grid>
                    
                    <Grid item xs={12}>
                      <Typography variant="subtitle1">Select Source to Test</Typography>
                      <Box display="flex" flexWrap="wrap" gap={2} mt={1}>
                        <Button
                          variant="outlined"
                          onClick={() => handleTestSearch('ads')}
                          disabled={loading}
                        >
                          Test ADS/SciX
                        </Button>
                        <Button
                          variant="outlined"
                          onClick={() => handleTestSearch('scholar')}
                          disabled={loading}
                        >
                          Test Google Scholar
                        </Button>
                        <Button
                          variant="outlined"
                          onClick={() => handleTestSearch('semanticScholar')}
                          disabled={loading}
                        >
                          Test Semantic Scholar
                        </Button>
                        <Button
                          variant="outlined"
                          onClick={() => handleTestSearch('webOfScience')}
                          disabled={loading}
                        >
                          Test Web of Science
                        </Button>
                      </Box>
                    </Grid>
                  </Grid>

                  {/* Test Search Results */}
                  {testSearchResults && (
                    <Box mt={4}>
                      <Typography variant="h5" gutterBottom>
                        Test Search Results for {testSearchResults.source}
                      </Typography>
                      <Paper elevation={2} sx={{ p: 2 }}>
                        <Typography variant="subtitle1">
                          Query: {testSearchResults.query} | 
                          Results: {testSearchResults.count} | 
                          Time: {testSearchResults.response_time_ms}ms
                        </Typography>
                        <Divider sx={{ my: 2 }} />
                        <pre>{JSON.stringify(testSearchResults.results, null, 2)}</pre>
                      </Paper>
                    </Box>
                  )}
                </Box>
              )}
            </Paper>
          </Box>
        )}

        {/* About Tab */}
        {mainTab === 3 && (
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
              {environmentInfo && environmentInfo.environment && (
                <Typography variant="body1">
                  Environment: {environmentInfo.environment}
                </Typography>
              )}
            </Paper>
          </Box>
        )}
      </Container>
    </Box>
  );
}

export default App; 
import React, { useState, useEffect, useCallback } from 'react';
import {
  Box, Paper, Grid, Button,
  Slider, FormControlLabel, Switch, Typography, FormControl,
  InputLabel, Select, MenuItem, Table, TableBody, TableCell,
  TableContainer, TableHead, TableRow, Chip, Divider,
  CircularProgress, Alert, Tooltip, IconButton, Collapse, List, ListItem, ListItemText
} from '@mui/material';
import ArrowUpwardIcon from '@mui/icons-material/ArrowUpward';
import ArrowDownwardIcon from '@mui/icons-material/ArrowDownward';
import ReplayIcon from '@mui/icons-material/Replay';
import HelpOutlineIcon from '@mui/icons-material/HelpOutline';
import BugReportIcon from '@mui/icons-material/BugReport';
import ArrowUpward from '@mui/icons-material/ArrowUpward';
import ArrowDownward from '@mui/icons-material/ArrowDownward';
import SearchIcon from '@mui/icons-material/Search';

/**
 * Component for experimenting with different boost factors and their impact on ranking
 * 
 * @param {Object} props - Component props
 * @param {Array} props.originalResults - The original search results to re-rank
 * @param {string} props.query - The search query used to retrieve results
 * @param {function} props.onRunNewSearch - Callback function when user wants to run a new search
 */
const BoostExperiment = ({ originalResults, query, API_URL = 'http://localhost:8000', onRunNewSearch }) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [boostedResults, setBoostedResults] = useState(null);
  const [debugMode, setDebugMode] = useState(false);
  const [debugInfo, setDebugInfo] = useState(null);
  const [searchLoading, setSearchLoading] = useState(false);
  
  // Boost configuration state
  const [boostConfig, setBoostConfig] = useState({
    // Citation boost
    enableCiteBoost: true,
    citeBoostWeight: 1.0,
    
    // Recency boost
    enableRecencyBoost: true,
    recencyBoostWeight: 1.0,
    recencyFunction: "exponential", // Changed to match backend default
    recencyMultiplier: 0.01, // Changed to match backend default
    recencyMidpoint: 36,
    
    // Document type boost
    enableDoctypeBoost: true,
    doctypeBoostWeight: 1.0,
    
    // Refereed boost
    enableRefereedBoost: true,
    refereedBoostWeight: 1.0,
    
    // Combination method
    combinationMethod: "sum",
    
    // Field-specific query boosts (new addition)
    enableFieldBoosts: true,
    fieldBoosts: {
      title: 2.0,
      abstract: 3.0,
      author: 1.5,
      year: 0.5,
    },
    
    // Query transformation options (new addition)
    queryTransformation: {
      enableTermSplitting: true,
      enablePhrasePreservation: true,
    }
  });
  
  // Function to transform the query based on the field boosts
  const transformQuery = useCallback((originalQuery) => {
    if (!boostConfig.enableFieldBoosts) {
      return originalQuery;
    }
    
    // Clean the original query
    const cleanQuery = originalQuery.trim();
    if (!cleanQuery) return "";
    
    console.log("Transforming query:", cleanQuery, "with config:", boostConfig.queryTransformation);
    
    // Extract terms and phrases based on configuration
    let terms = [];
    let phrases = [];
    
    // First, extract any quoted phrases from the query
    if (boostConfig.queryTransformation.enablePhrasePreservation) {
      const phraseRegex = /"([^"]+)"/g;
      let match;
      let remainingText = cleanQuery;
      
      // Extract explicitly quoted phrases
      while ((match = phraseRegex.exec(cleanQuery)) !== null) {
        phrases.push(match[1]);
        remainingText = remainingText.replace(match[0], ' ');
      }
      
      console.log("Extracted explicit phrases:", phrases);
      
      // If no explicit phrases but the query has multiple words,
      // treat the whole query as an implicit phrase
      if (phrases.length === 0 && remainingText.includes(' ')) {
        phrases.push(remainingText.trim());
        console.log("Added implicit phrase:", remainingText.trim());
      }
      
      // If term splitting is enabled, also add individual terms
      if (boostConfig.queryTransformation.enableTermSplitting) {
        // Split the remaining text into individual terms
        const individualTerms = remainingText.split(/\s+/).filter(term => term.length > 0);
        terms.push(...individualTerms);
        console.log("Added individual terms:", terms);
      }
    } else if (boostConfig.queryTransformation.enableTermSplitting) {
      // If phrase preservation is disabled but term splitting is enabled,
      // just split the query into individual terms
      terms = cleanQuery.split(/\s+/).filter(term => term.length > 0);
      console.log("Split query into terms only:", terms);
    } else {
      // If both phrase preservation and term splitting are disabled,
      // use the entire query as a single term
      terms.push(cleanQuery);
      console.log("Using entire query as a single term:", cleanQuery);
    }
    
    // Create a simplified query structure that works better with search APIs
    let parts = [];
    
    // Add field-specific boosts for individual terms
    terms.forEach(term => {
      if (term && term.trim()) {
        Object.entries(boostConfig.fieldBoosts).forEach(([field, boost]) => {
          // Format the boost with one decimal place for readability
          const formattedBoost = parseFloat(boost).toFixed(1);
          parts.push(`(${field}:${term})^${formattedBoost}`);
        });
      }
    });
    
    // Add field-specific boosts for phrases
    phrases.forEach(phrase => {
      if (phrase && phrase.trim()) {
        Object.entries(boostConfig.fieldBoosts).forEach(([field, boost]) => {
          // Format the boost with one decimal place for readability
          const formattedBoost = parseFloat(boost).toFixed(1);
          parts.push(`(${field}:"${phrase}")^${formattedBoost}`);
        });
      }
    });
    
    // Join all parts with OR operators
    const result = parts.join(" OR ");
    console.log("Final transformed query:", result);
    return result;
  }, [boostConfig]);
  
  // Debug logging
  useEffect(() => {
    console.log('BoostExperiment mounted with:', {
      originalResultsLength: originalResults?.length,
      query,
      boostConfig
    });
    
    // Log the transformed query for debugging
    if (query) {
      const transformedQuery = transformQuery(query);
      console.log('Transformed query:', transformedQuery);
    }
    
    if (originalResults?.length > 0) {
      // COMPREHENSIVE LOGGING: Log the entire first result to see the complete structure
      console.log("CRITICAL: Complete structure of first result:", JSON.stringify(originalResults[0], null, 2));
      
      // Log much more detailed information about the original search results
      const yearTypes = originalResults.map(r => typeof r.year).filter((v, i, a) => a.indexOf(v) === i);
      const sampleYears = originalResults.slice(0, 5).map(r => r.year);
      const hasArrayYears = originalResults.some(r => Array.isArray(r.year));
      const yearStructure = {
        types_present: yearTypes,
        sample_values: sampleYears,
        any_arrays: hasArrayYears,
        original_display: originalResults.slice(0, 5).map(r => ({
          title: truncateText(r.title, 30),
          year_display: r.year,
          year_type: typeof r.year,
          year_json: JSON.stringify(r.year)
        }))
      };
      
      console.log("CRITICAL DEBUGGING - Years in original results:", yearStructure);
      
      // Check for alternative fields that might contain year information
      const alternativeFields = originalResults.slice(0, 3).map(r => ({
        title: truncateText(r.title, 30),
        pub_year: r.pub_year,
        date: r.date,
        pubdate: r.pubdate,
        publication_year: r.publication_year,
        year_of_publication: r.year_of_publication
      }));
      console.log("CHECKING ALTERNATIVE YEAR FIELDS:", alternativeFields);
      
      console.log("Sample result metadata:", {
        citation: originalResults[0].citation_count,
        year: originalResults[0].year,
        year_type: typeof originalResults[0].year,
        doctype: originalResults[0].doctype,
        properties: originalResults[0].property
      });
    }
  }, [originalResults, query, boostConfig]);
  
  // Apply the boost experiment
  const applyBoosts = useCallback(async () => {
    if (!originalResults || originalResults.length === 0) {
      setError('No original results to modify');
      return;
    }
    
    setLoading(true);
    setError(null);
    setDebugInfo(null);
    
    try {
      // CRITICAL DEBUG: Log what we're actually receiving
      console.log("CRITICAL DEBUG - Starting boost process with:", {
        result_count: originalResults.length,
        all_years: originalResults.slice(0, 5).map(r => r.year),
        all_year_types: originalResults.slice(0, 5).map(r => typeof r.year),
        sample_full_results: originalResults.slice(0, 3),
        has_undefined_years: originalResults.some(r => r.year === undefined),
        has_null_years: originalResults.some(r => r.year === null),
      });
      
      // Generate the transformed query
      const transformedQuery = transformQuery(query);
      console.log("Using transformed query:", transformedQuery);
      
      // Log boost configuration values to verify they're being sent correctly
      console.log("CRITICAL DEBUG - Sending boost config:", {
        enableCiteBoost: boostConfig.enableCiteBoost,
        citeBoostWeight: boostConfig.citeBoostWeight,
        enableRecencyBoost: boostConfig.enableRecencyBoost,
        recencyBoostWeight: boostConfig.recencyBoostWeight,
        enableDoctypeBoost: boostConfig.enableDoctypeBoost,
        doctypeBoostWeight: boostConfig.doctypeBoostWeight,
        enableRefereedBoost: boostConfig.enableRefereedBoost,
        refereedBoostWeight: boostConfig.refereedBoostWeight,
        combinationMethod: boostConfig.combinationMethod,
        fieldBoosts: boostConfig.fieldBoosts
      });
      
      // Ensure all weight values are properly converted to numbers
      const normalizedBoostConfig = {
        ...boostConfig,
        citeBoostWeight: Number(boostConfig.citeBoostWeight),
        recencyBoostWeight: Number(boostConfig.recencyBoostWeight),
        doctypeBoostWeight: Number(boostConfig.doctypeBoostWeight),
        refereedBoostWeight: Number(boostConfig.refereedBoostWeight),
        fieldBoosts: {
          title: Number(boostConfig.fieldBoosts.title),
          abstract: Number(boostConfig.fieldBoosts.abstract),
          author: Number(boostConfig.fieldBoosts.author),
          year: Number(boostConfig.fieldBoosts.year)
        }
      };
      
      console.log("Normalized boost config with number values:", normalizedBoostConfig);
      
      // Extensive logging to debug the metadata fields
      if (originalResults.length > 0) {
        console.log("DEBUGGING METADATA FIELDS - First 3 results:", originalResults.slice(0, 3).map(result => ({
          title: truncateText(result.title, 30),
          year_type: typeof result.year,
          year_value: result.year,
          year_stringified: JSON.stringify(result.year),
          doctype_type: typeof result.doctype,
          doctype_value: result.doctype,
          property_type: typeof result.property,
          property_value: result.property,
          property_is_array: Array.isArray(result.property),
        })));
      }
      
      // CRITICAL FIX: Extract year from bibcode if available and year is null
      const processedResults = originalResults.map(result => {
        // For debugging, log the first few results
        if (result.rank && result.rank <= 5) {
          console.log(`Processing result rank ${result.rank} - RAW DATA:`, result);
        }
        
        // Extract year from bibcode if possible and year is missing
        let extractedYear = null;
        if ((result.year === null || result.year === undefined) && result.bibcode) {
          // ADS bibcodes typically have year as the first 4 digits
          const yearMatch = result.bibcode.match(/^(\d{4})/);
          if (yearMatch && yearMatch[1]) {
            extractedYear = parseInt(yearMatch[1], 10);
            console.log(`Successfully extracted year ${extractedYear} from bibcode ${result.bibcode} for "${truncateText(result.title, 30)}"`);
          }
        }
        
        // Extract year from the URL if we still don't have a year
        if (extractedYear === null && result.url) {
          const urlYearMatch = result.url.match(/\/abs\/(\d{4})/);
          if (urlYearMatch && urlYearMatch[1]) {
            extractedYear = parseInt(urlYearMatch[1], 10);
            console.log(`Successfully extracted year ${extractedYear} from URL ${result.url} for "${truncateText(result.title, 30)}"`);
          }
        }
        
        // Check if year is embedded in the title (sometimes in parentheses at the end)
        if (extractedYear === null && result.title) {
          const titleYearMatch = result.title.match(/\((\d{4})\)/);
          if (titleYearMatch && titleYearMatch[1]) {
            extractedYear = parseInt(titleYearMatch[1], 10);
            console.log(`Successfully extracted year ${extractedYear} from title for "${truncateText(result.title, 30)}"`);
          }
        }
        
        // Last fallback - use a reasonable default if still needed
        if (extractedYear === null) {
          // Use current year minus 3 as a more reasonable default (not too recent, not too old)
          extractedYear = new Date().getFullYear() - 3;
          console.log(`Using fallback year ${extractedYear} for "${truncateText(result.title, 30)}"`);
        }
        
        return {
          ...result,
          citation_count: typeof result.citation_count === 'number' ? result.citation_count : 0,
          // IMPORTANT: Use extracted year if original is null, preserving original otherwise
          year: (result.year === null || result.year === undefined) ? extractedYear : result.year,
          doctype: result.doctype || '',
          property: Array.isArray(result.property) ? result.property : 
                  (result.property ? [result.property] : [])
        };
      });
      
      console.log('Sending boost experiment request with the first 3 results:', {
        first_three_processed: processedResults.slice(0, 3).map(r => ({
          title: truncateText(r.title, 30),
          original_year: originalResults.find(or => or.title === r.title)?.year,
          processed_year: r.year
        }))
      });
      
      const response = await fetch(`${API_URL}/api/boost-experiment`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          query,
          transformedQuery,
          results: processedResults,
          boostConfig: normalizedBoostConfig
        })
      });
      
      console.log('Boost experiment response status:', response.status);
      
      if (!response.ok) {
        const errorText = await response.text();
        console.error('Boost experiment error:', errorText);
        throw new Error(`Failed to apply boosts: ${errorText}`);
      }
      
      const data = await response.json();
      console.log('Received boosted results:', data);
      setBoostedResults(data);
      
      // Store debug info about the first result for debugging panel
      if (data.results && data.results.length > 0) {
        const firstResult = data.results[0];
        setDebugInfo({
          firstResult,
          citationFields: {
            citations: firstResult.citations,
            citation_count: firstResult.citation_count,
            citationCount: firstResult.citationCount,
          },
          boostFields: {
            boostFactors: firstResult.boostFactors,
            citeBoost: firstResult.citeBoost || firstResult.boostFactors?.citeBoost || 0,
            recencyBoost: firstResult.recencyBoost || firstResult.boostFactors?.recencyBoost || 0,
            doctypeBoost: firstResult.doctypeBoost || firstResult.boostFactors?.doctypeBoost || 0,
            refereedBoost: firstResult.refereedBoost || firstResult.boostFactors?.refereedBoost || 0,
            totalBoost: firstResult.totalBoost,
            finalBoost: firstResult.finalBoost,
          },
          metadataFields: {
            year: firstResult.year,
            doctype: firstResult.doctype,
            property: firstResult.property,
          }
        });
      }
      
    } catch (err) {
      console.error('Error in boost experiment:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [API_URL, boostConfig, originalResults, query]);
  
  // Function to run a completely new search with current field weights
  const runNewSearch = useCallback(() => {
    if (!query) {
      setError('No query to search with');
      return;
    }
    
    // Show loading indicator
    setSearchLoading(true);
    
    // Generate the transformed query with current field weights
    const transformedQuery = transformQuery(query);
    console.log("Running new search with transformed query:", transformedQuery);
    
    // Call the parent component's onRunNewSearch function if provided
    if (onRunNewSearch && typeof onRunNewSearch === 'function') {
      // Pass the transformed query and current boost configuration to the parent
      onRunNewSearch(transformedQuery, boostConfig)
        .then(() => {
          setSearchLoading(false);
        })
        .catch(err => {
          console.error("Error running new search:", err);
          setError("Failed to run new search: " + (err.message || 'Unknown error'));
          setSearchLoading(false);
        });
    } else {
      console.error("No onRunNewSearch function provided");
      setError("Cannot run new search - feature not implemented by parent component");
      setSearchLoading(false);
    }
  }, [query, transformQuery, boostConfig, onRunNewSearch]);
  
  // Helper functions
  const truncateText = (text, maxLength) => {
    if (!text) return '';
    return text.length > maxLength ? `${text.substring(0, maxLength)}...` : text;
  };

  const formatAuthors = (authors) => {
    if (!authors) return 'Unknown';
    
    if (typeof authors === 'string') {
      return authors;
    }
    
    if (Array.isArray(authors)) {
      return authors.slice(0, 3).join(', ') + (authors.length > 3 ? ', et al.' : '');
    }
    
    return 'Unknown';
  };
  
  // Format rank change display
  const formatRankChange = (change) => {
    if (change > 0) {
      return (
        <Box sx={{ display: 'flex', alignItems: 'center', color: 'success.main' }}>
          <ArrowUpwardIcon fontSize="small" sx={{ mr: 0.5 }} />
          {change}
        </Box>
      );
    } else if (change < 0) {
      return (
        <Box sx={{ display: 'flex', alignItems: 'center', color: 'error.main' }}>
          <ArrowDownwardIcon fontSize="small" sx={{ mr: 0.5 }} />
          {Math.abs(change)}
        </Box>
      );
    } else {
      return '—';
    }
  };
  
  // Format boost factor display
  const formatBoostFactor = (value) => {
    if (value === undefined || value === null) return '—';
    return value.toFixed(2);
  };
  
  // Apply boosts whenever configuration changes
  useEffect(() => {
    if (originalResults && originalResults.length > 0) {
      applyBoosts();
    } else {
      console.log('No original results to boost');
    }
  }, [boostConfig, originalResults, applyBoosts]);
  
  // Enhanced debug component to inspect fields and values
  const renderDebugPanel = () => {
    if (!debugInfo) return null;
    
    return (
      <Box sx={{ mt: 2, mb: 2, border: 1, borderColor: 'warning.light', p: 2, borderRadius: 1 }}>
        <Typography variant="h6" color="warning.main" gutterBottom>
          Debug Information
        </Typography>
        
        <Typography variant="subtitle2" gutterBottom>Metadata Fields (Required for Boosts)</Typography>
        <TableContainer component={Paper} variant="outlined" sx={{ mb: 2 }}>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Field Name</TableCell>
                <TableCell>Present</TableCell>
                <TableCell>Value</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              <TableRow>
                <TableCell>citation_count</TableCell>
                <TableCell>
                  {debugInfo.firstResult.citation_count !== undefined ? (
                    <Chip label="Yes" size="small" color="success" />
                  ) : (
                    <Chip label="No" size="small" color="error" />
                  )}
                </TableCell>
                <TableCell>{debugInfo.firstResult.citation_count !== undefined ? String(debugInfo.firstResult.citation_count) : 'N/A'}</TableCell>
              </TableRow>
              <TableRow>
                <TableCell>year</TableCell>
                <TableCell>
                  {debugInfo.firstResult.year !== undefined ? (
                    <Chip label="Yes" size="small" color="success" />
                  ) : (
                    <Chip label="No" size="small" color="error" />
                  )}
                </TableCell>
                <TableCell>{debugInfo.firstResult.year !== undefined ? String(debugInfo.firstResult.year) : 'N/A'}</TableCell>
              </TableRow>
              <TableRow>
                <TableCell>doctype</TableCell>
                <TableCell>
                  {debugInfo.firstResult.doctype !== undefined ? (
                    <Chip label="Yes" size="small" color="success" />
                  ) : (
                    <Chip label="No" size="small" color="error" />
                  )}
                </TableCell>
                <TableCell>{debugInfo.firstResult.doctype !== undefined ? String(debugInfo.firstResult.doctype) : 'N/A'}</TableCell>
              </TableRow>
              <TableRow>
                <TableCell>property</TableCell>
                <TableCell>
                  {debugInfo.firstResult.property !== undefined ? (
                    <Chip label="Yes" size="small" color="success" />
                  ) : (
                    <Chip label="No" size="small" color="error" />
                  )}
                </TableCell>
                <TableCell>{debugInfo.firstResult.property !== undefined ? 
                  (Array.isArray(debugInfo.firstResult.property) ? 
                    debugInfo.firstResult.property.join(', ') : 
                    String(debugInfo.firstResult.property)) : 
                  'N/A'}</TableCell>
              </TableRow>
            </TableBody>
          </Table>
        </TableContainer>

        <Typography variant="subtitle2" gutterBottom>Citation Fields</Typography>
        <TableContainer component={Paper} variant="outlined" sx={{ mb: 2 }}>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Field Name</TableCell>
                <TableCell>Present</TableCell>
                <TableCell>Value</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {Object.entries(debugInfo.citationFields).map(([field, value]) => (
                <TableRow key={field}>
                  <TableCell>{field}</TableCell>
                  <TableCell>
                    {value !== undefined && value !== null ? (
                      <Chip label="Yes" size="small" color="success" />
                    ) : (
                      <Chip label="No" size="small" color="error" />
                    )}
                  </TableCell>
                  <TableCell>{value !== undefined && value !== null ? String(value) : 'N/A'}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
        
        <Typography variant="subtitle2" gutterBottom>Boost Fields</Typography>
        <TableContainer component={Paper} variant="outlined" sx={{ mb: 2 }}>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Field Name</TableCell>
                <TableCell>Present</TableCell>
                <TableCell>Value</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {Object.entries(debugInfo.boostFields).map(([field, value]) => (
                <TableRow key={field}>
                  <TableCell>{field}</TableCell>
                  <TableCell>
                    {value !== undefined && value !== null ? (
                      <Chip label="Yes" size="small" color="success" />
                    ) : (
                      <Chip label="No" size="small" color="error" />
                    )}
                  </TableCell>
                  <TableCell>
                    {field === 'boostFactors' && typeof value === 'object' ? (
                      <Typography variant="caption" component="pre" sx={{ maxHeight: 100, overflow: 'auto' }}>
                        {JSON.stringify(value, null, 2)}
                      </Typography>
                    ) : (
                      value !== undefined && value !== null ? String(value) : 'N/A'
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
        
        <Typography variant="subtitle2" gutterBottom>First Result Raw Data</Typography>
        <Box 
          component="pre" 
          sx={{ 
            maxHeight: 200, 
            overflow: 'auto', 
            fontSize: '0.75rem', 
            bgcolor: 'grey.100', 
            p: 1, 
            borderRadius: 1 
          }}
        >
          {JSON.stringify(debugInfo.firstResult, null, 2)}
        </Box>
      </Box>
    );
  };
  
  if (!originalResults || originalResults.length === 0) {
    return (
      <Alert severity="warning">
        No results available for boost experiment. Please perform a search first.
      </Alert>
    );
  }
  
  const handleConfigChange = (field, value) => {
    setBoostConfig(prev => ({
      ...prev,
      [field]: value
    }));
  };
  
  // New handler for field boost changes
  const handleFieldBoostChange = (field, value) => {
    setBoostConfig(prev => ({
      ...prev,
      fieldBoosts: {
        ...prev.fieldBoosts,
        [field]: value
      }
    }));
  };
  
  // New handler for query transformation options
  const handleQueryTransformationChange = (option, value) => {
    setBoostConfig(prev => ({
      ...prev,
      queryTransformation: {
        ...prev.queryTransformation,
        [option]: value
      }
    }));
  };
  
  // New handler for text input changes - allow much higher values now
  const handleTextInputChange = (field, event) => {
    const value = parseFloat(event.target.value);
    if (!isNaN(value) && value >= 0) {
      console.log(`Updating ${field} to ${value}`);
      handleConfigChange(field, value);
    }
  };
  
  // New handler for field boost text input changes - allow much higher values now
  const handleFieldBoostTextInputChange = (field, event) => {
    const value = parseFloat(event.target.value);
    if (!isNaN(value) && value >= 0) {
      console.log(`Updating field boost ${field} to ${value}`);
      handleFieldBoostChange(field, value);
    }
  };
  
  // Render the boost controls section
  const renderBoostControls = () => (
    <Paper sx={{ p: 2, mb: 2 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Typography variant="h6">Boost Configuration</Typography>
        <Box>
          <Button
            variant="contained"
            color="primary"
            size="small"
            onClick={runNewSearch}
            disabled={searchLoading}
            sx={{ ml: 1 }}
          >
            {searchLoading ? <CircularProgress size={20} sx={{ mr: 1 }} color="inherit" /> : null}
            Apply Changes
          </Button>
        </Box>
      </Box>
      
      <Grid container spacing={2}>
        {/* Field Boost Controls */}
        <Grid item xs={12} md={6}>
          <Typography variant="subtitle1" gutterBottom>Field Boost Weights</Typography>
          
          <Box sx={{ mb: 2 }}>
            <Typography variant="body2" gutterBottom>Title Weight: {boostConfig.fieldBoosts.title.toFixed(1)}</Typography>
            <Slider
              value={boostConfig.fieldBoosts.title}
              onChange={(e, value) => handleFieldBoostChange('title', value)}
              min={0}
              max={20}
              step={0.1}
              valueLabelDisplay="auto"
            />
          </Box>
          
          <Box sx={{ mb: 2 }}>
            <Typography variant="body2" gutterBottom>Abstract Weight: {boostConfig.fieldBoosts.abstract.toFixed(1)}</Typography>
            <Slider
              value={boostConfig.fieldBoosts.abstract}
              onChange={(e, value) => handleFieldBoostChange('abstract', value)}
              min={0}
              max={20}
              step={0.1}
              valueLabelDisplay="auto"
            />
          </Box>
          
          <Box sx={{ mb: 2 }}>
            <Typography variant="body2" gutterBottom>Author Weight: {boostConfig.fieldBoosts.author.toFixed(1)}</Typography>
            <Slider
              value={boostConfig.fieldBoosts.author}
              onChange={(e, value) => handleFieldBoostChange('author', value)}
              min={0}
              max={20}
              step={0.1}
              valueLabelDisplay="auto"
            />
          </Box>
        </Grid>
        
        {/* Other Boost Controls */}
        <Grid item xs={12} md={6}>
          <Typography variant="subtitle1" gutterBottom>Citation & Recency Boost</Typography>
          
          <Box sx={{ mb: 2 }}>
            <Typography variant="body2" gutterBottom>Citation Boost: {boostConfig.citeBoostWeight.toFixed(1)}</Typography>
            <Slider
              value={boostConfig.citeBoostWeight}
              onChange={(e, value) => handleTextInputChange('citeBoostWeight', e)}
              min={0}
              max={5}
              step={0.1}
              valueLabelDisplay="auto"
            />
          </Box>
          
          <Box sx={{ mb: 2 }}>
            <Typography variant="body2" gutterBottom>Recency Boost: {boostConfig.recencyBoostWeight.toFixed(1)}</Typography>
            <Slider
              value={boostConfig.recencyBoostWeight}
              onChange={(e, value) => handleTextInputChange('recencyBoostWeight', e)}
              min={0}
              max={5}
              step={0.1}
              valueLabelDisplay="auto"
            />
          </Box>
        </Grid>
      </Grid>
    </Paper>
  );
  
  return (
    <Box sx={{ width: '100%', p: 2 }}>
      {!originalResults || originalResults.length === 0 ? (
        <Alert severity="warning">
          No results available for boost experiment. Please perform a search first.
        </Alert>
      ) : (
        <Grid container spacing={2}>
          {/* Boost Controls */}
          <Grid item xs={12} md={4}>
            {renderBoostControls()}
          </Grid>

          {/* Results Panel */}
          <Grid item xs={12} md={8}>
            <Paper sx={{ p: 2 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                <Typography variant="h6" sx={{ flexGrow: 1 }}>
                  Ranking Results
                </Typography>
                {loading && <CircularProgress size={24} sx={{ ml: 2 }} />}
                <Button
                  startIcon={<BugReportIcon />}
                  variant="outlined"
                  size="small"
                  color="warning"
                  onClick={() => setDebugMode(!debugMode)}
                  sx={{ ml: 2 }}
                >
                  {debugMode ? 'Hide Debug' : 'Debug Mode'}
                </Button>
              </Box>

              {error && (
                <Alert severity="error" sx={{ mb: 2 }}>
                  {error}
                </Alert>
              )}

              {searchLoading && (
                <Alert severity="info" sx={{ mb: 2 }}>
                  Fetching new results with updated field weights...
                </Alert>
              )}

              <Collapse in={debugMode}>
                {renderDebugPanel()}
              </Collapse>

              {boostedResults && boostedResults.results ? (
                <>
                  <Box sx={{ display: 'flex', mb: 2 }}>
                    {/* Title Headers */}
                    <Box sx={{ width: '50%', pr: 1 }}>
                      <Paper sx={{ p: 1, bgcolor: 'grey.100', borderRadius: 1 }}>
                        <Typography variant="subtitle1" align="center" fontWeight="bold">
                          Original Results
                        </Typography>
                        <Typography variant="caption" align="center" display="block" color="text.secondary">
                          Default ranking without boosts
                        </Typography>
                      </Paper>
                    </Box>
                    <Box sx={{ width: '50%', pl: 1 }}>
                      <Paper sx={{ p: 1, bgcolor: 'primary.light', color: 'primary.contrastText', borderRadius: 1 }}>
                        <Typography variant="subtitle1" align="center" fontWeight="bold">
                          Boosted Results
                        </Typography>
                        <Typography variant="caption" align="center" display="block" sx={{ color: 'rgba(255,255,255,0.8)' }}>
                          Re-ranked based on current boost settings
                        </Typography>
                      </Paper>
                    </Box>
                  </Box>
                  
                  <Box sx={{ mb: 2 }}>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', px: 1 }}>
                      <Typography variant="caption" fontStyle="italic">
                        <strong>Note:</strong> Items with significant rank changes have colored borders and indicators.
                      </Typography>
                    </Box>
                  </Box>
                  
                  <Box sx={{ display: 'flex' }}>
                    {/* Original Results */}
                    <Box sx={{ width: '50%', pr: 1, height: '65vh', overflow: 'auto' }}>
                      <List sx={{ bgcolor: 'background.paper', border: '1px solid', borderColor: 'divider', borderRadius: 1 }}>
                        {originalResults.map((result, index) => {
                          // Find matching boosted result to determine rank change
                          const boostedIndex = boostedResults.results.findIndex(
                            r => r.bibcode === result.bibcode || r.title === result.title
                          );
                          const rankChange = boostedIndex !== -1 ? index - boostedIndex : 0;
                          
                          return (
                            <Tooltip
                              key={result.bibcode || index}
                              title={
                                <Box>
                                  <Typography variant="subtitle2">{result.title}</Typography>
                                  <Typography variant="body2">
                                    <strong>Authors:</strong> {formatAuthors(result.author)}
                                  </Typography>
                                  {result.abstract && (
                                    <Typography variant="body2">
                                      <strong>Abstract:</strong> {truncateText(result.abstract, 200)}
                                    </Typography>
                                  )}
                                </Box>
                              }
                              placement="left"
                            >
                              <ListItem 
                                key={result.bibcode || result.title} 
                                divider
                                sx={{ 
                                  px: 2, 
                                  py: 1,
                                  position: 'relative'
                                }}
                              >
                                <ListItemText
                                  primary={
                                    <Box sx={{ display: 'flex', alignItems: 'flex-start' }}>
                                      <Typography 
                                        variant="body2" 
                                        component="span"
                                        sx={{ 
                                          minWidth: '24px',
                                          fontWeight: 'bold',
                                          mr: 1
                                        }}
                                      >
                                        {index + 1}
                                      </Typography>
                                      <Box>
                                        <Typography variant="body2" sx={{ fontWeight: 'medium' }}>
                                          {truncateText(result.title, 60)}
                                        </Typography>
                                        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5, mt: 0.5 }}>
                                          {result.year && (
                                            <Chip 
                                              label={`${result.year}`} 
                                              size="small" 
                                              variant="outlined"
                                              sx={{ height: 20, '& .MuiChip-label': { px: 1, fontSize: '0.7rem' } }}
                                            />
                                          )}
                                          {result.citation_count !== undefined && (
                                            <Chip 
                                              label={`Citations: ${result.citation_count}`} 
                                              size="small"
                                              variant="outlined"
                                              sx={{ height: 20, '& .MuiChip-label': { px: 1, fontSize: '0.7rem' } }}
                                            />
                                          )}
                                        </Box>
                                      </Box>
                                    </Box>
                                  }
                                />
                              </ListItem>
                            </Tooltip>
                          );
                        })}
                      </List>
                    </Box>
                    
                    {/* Boosted Results */}
                    <Box sx={{ width: '50%', pl: 1, height: '65vh', overflow: 'auto' }}>
                      <List sx={{ bgcolor: 'background.paper', border: '1px solid', borderColor: 'primary.light', borderRadius: 1 }}>
                        {boostedResults.results.map((result, index) => {
                          // Find matching original result to determine rank change
                          const originalIndex = originalResults.findIndex(
                            r => r.bibcode === result.bibcode || r.title === result.title
                          );
                          const rankChange = originalIndex !== -1 ? originalIndex - index : 0;
                          
                          // Get boost factors for this result
                          const boostFactors = {};
                          if (result.boostFactors) {
                            Object.entries(result.boostFactors).forEach(([key, value]) => {
                              boostFactors[key] = value;
                            });
                          }
                          
                          return (
                            <Tooltip
                              key={result.bibcode || index}
                              title={
                                <Box>
                                  <Typography variant="subtitle2">{result.title}</Typography>
                                  <Typography variant="body2">
                                    <strong>Authors:</strong> {formatAuthors(result.author)}
                                  </Typography>
                                  {result.abstract && (
                                    <Typography variant="body2">
                                      <strong>Abstract:</strong> {truncateText(result.abstract, 200)}
                                    </Typography>
                                  )}
                                  <Divider sx={{ my: 1 }} />
                                  <Typography variant="body2">
                                    <strong>Original Rank:</strong> {originalIndex + 1}
                                  </Typography>
                                  <Typography variant="body2">
                                    <strong>Rank Change:</strong> {rankChange > 0 ? '+' : ''}{rankChange}
                                  </Typography>
                                  <Typography variant="body2">
                                    <strong>Boost Score:</strong> {result.finalBoost ? result.finalBoost.toFixed(2) : 'N/A'}
                                  </Typography>
                                  <Typography variant="body2">
                                    <strong>Applied Boosts:</strong>
                                  </Typography>
                                  <Box component="ul" sx={{ mt: 0.5, pl: 2 }}>
                                    {Object.entries(boostFactors).map(([key, value]) => (
                                      <Typography component="li" variant="caption" key={key}>
                                        {key}: {value && value.toFixed ? value.toFixed(2) : value}
                                      </Typography>
                                    ))}
                                  </Box>
                                </Box>
                              }
                              placement="right"
                            >
                              <ListItem 
                                key={result.bibcode || result.title} 
                                divider
                                sx={{ 
                                  px: 2, 
                                  py: 1,
                                  position: 'relative',
                                  borderLeft: rankChange !== 0 ? '4px solid' : 'none',
                                  borderLeftColor: rankChange > 0 ? 'success.main' : rankChange < 0 ? 'error.main' : 'transparent'
                                }}
                              >
                                <ListItemText
                                  primary={
                                    <Box sx={{ display: 'flex', alignItems: 'flex-start' }}>
                                      <Typography 
                                        variant="body2" 
                                        component="span"
                                        sx={{ 
                                          minWidth: '24px',
                                          fontWeight: 'bold',
                                          mr: 1
                                        }}
                                      >
                                        {index + 1}
                                      </Typography>
                                      <Box>
                                        <Typography variant="body2" sx={{ fontWeight: 'medium' }}>
                                          {truncateText(result.title, 60)}
                                        </Typography>
                                        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5, mt: 0.5 }}>
                                          {result.year && (
                                            <Chip 
                                              label={`${result.year}`} 
                                              size="small" 
                                              variant="outlined"
                                              sx={{ height: 20, '& .MuiChip-label': { px: 1, fontSize: '0.7rem' } }}
                                            />
                                          )}
                                          {result.citation_count !== undefined && (
                                            <Chip 
                                              label={`Citations: ${result.citation_count}`} 
                                              size="small"
                                              variant="outlined"
                                              sx={{ height: 20, '& .MuiChip-label': { px: 1, fontSize: '0.7rem' } }}
                                            />
                                          )}
                                          {rankChange !== 0 && (
                                            <Chip 
                                              icon={rankChange > 0 ? <ArrowUpward fontSize="small" /> : <ArrowDownward fontSize="small" />}
                                              label={`${rankChange > 0 ? '+' : ''}${rankChange}`}
                                              size="small"
                                              color={rankChange > 0 ? 'success' : 'error'}
                                              sx={{ height: 20, '& .MuiChip-label': { px: 1, fontSize: '0.7rem' } }}
                                            />
                                          )}
                                          {result.finalBoost !== undefined && (
                                            <Chip 
                                              label={`Boost: ${result.finalBoost.toFixed(1)}`} 
                                              size="small"
                                              color="primary"
                                              sx={{ 
                                                height: 20, 
                                                '& .MuiChip-label': { px: 1, fontSize: '0.7rem' },
                                                fontWeight: 'bold', 
                                                bgcolor: `rgba(25, 118, 210, ${Math.min(result.finalBoost / 20, 1)})`
                                              }}
                                            />
                                          )}
                                        </Box>
                                      </Box>
                                    </Box>
                                  }
                                />
                              </ListItem>
                            </Tooltip>
                          );
                        })}
                      </List>
                    </Box>
                  </Box>
                </>
              ) : (
                <Alert severity="info">
                  Configure and apply boost factors to see how they affect the ranking.
                </Alert>
              )}
            </Paper>
          </Grid>
        </Grid>
      )}
    </Box>
  );
};

export default BoostExperiment; 
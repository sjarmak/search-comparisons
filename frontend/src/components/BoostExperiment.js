import React, { useState, useEffect, useCallback } from 'react';
import {
  Box, Paper, Grid, Button,
  Slider, FormControlLabel, Switch, Typography, FormControl,
  InputLabel, Select, MenuItem, Table, TableBody, TableCell,
  TableContainer, TableHead, TableRow, Chip, Divider,
  CircularProgress, Alert, Tooltip, IconButton, List, ListItem, ListItemText, TextField,
  Dialog, DialogTitle, DialogContent, DialogActions
} from '@mui/material';
import ArrowUpwardIcon from '@mui/icons-material/ArrowUpward';
import ArrowDownwardIcon from '@mui/icons-material/ArrowDownward';
import ReplayIcon from '@mui/icons-material/Replay';
import HelpOutlineIcon from '@mui/icons-material/HelpOutline';
import SearchIcon from '@mui/icons-material/Search';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';
import FileDownloadIcon from '@mui/icons-material/FileDownload';
import { experimentService, API_URL as DEFAULT_API_URL } from '../services/api';
import { List as ListIcon } from '@mui/icons-material';
import LaunchIcon from '@mui/icons-material/Launch';
import { TransformedQuery } from './TransformedQuery';

/**
 * Component for experimenting with different boost factors and their impact on ranking
 * 
 * @param {Object} props - Component props
 * @param {string} props.API_URL - The API URL for making requests
 */
const BoostExperiment = ({ API_URL = DEFAULT_API_URL }) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [boostedResults, setBoostedResults] = useState(null);
  const [searchLoading, setSearchLoading] = useState(false);
  const [transformedQuery, setTransformedQuery] = useState(null);
  const [searchQuery, setSearchQuery] = useState('triton');
  const [informationNeed, setInformationNeed] = useState('');
  const [quepidCaseId, setQuepidCaseId] = useState('8914');
  const [searchResults, setSearchResults] = useState(null);
  const [quepidResults, setQuepidResults] = useState(null);
  const [judgmentMap, setJudgmentMap] = useState({});
  const [expandedRecords, setExpandedRecords] = useState({});
  const [localJudgments, setLocalJudgments] = useState({});
  const [judgmentCounts, setJudgmentCounts] = useState({
    original: { quepid: 0, manual: 0, total: 0 },
    boosted: { quepid: 0, manual: 0, total: 0 },
    scholar: { quepid: 0, manual: 0, total: 0 },
    quepid: { quepid: 0, manual: 0, total: 0 }
  });
  const [exportDialogOpen, setExportDialogOpen] = useState(false);
  const [showBoostControls, setShowBoostControls] = useState(true);
  const [selectedRecord, setSelectedRecord] = useState(null);
  const [detailsDialogOpen, setDetailsDialogOpen] = useState(false);
  const [judgmentNoteDialogOpen, setJudgmentNoteDialogOpen] = useState(false);
  const [currentJudgmentData, setCurrentJudgmentData] = useState(null);
  const [visibleResults, setVisibleResults] = useState({
    original: 10,
    boosted: 10,
    scholar: 10,
    quepid: 10
  });
  
  // State for boost configuration
  const [boostConfig, setBoostConfig] = useState({
    enableFieldBoosts: true,
    fieldBoosts: {
      title: 0.0,  // Set default to 0
      abstract: 0.0,
      authors: 0.0,
      year: 0.0,
    },
    citationBoost: 0.0,  // Set default to 0
    recencyBoost: 0.0,  // Set default to 0
    referenceYear: new Date().getFullYear(),
    doctypeBoosts: {
      journal: 0.0,  // Set default to 0
      conference: 0.0,
      book: 0.0,
      thesis: 0.0,
    }
  });
  
  // Function to handle boost changes
  const handleBoostChange = (type, field, value) => {
    setBoostConfig(prev => {
      if (type === 'fieldBoosts' || type === 'doctypeBoosts') {
        return {
          ...prev,
          [type]: {
            ...prev[type],
            [field]: value
          }
        };
      }
      return {
        ...prev,
        [type]: value
      };
    });
  };
  
  // Function to transform the query based on the field boosts
  const transformQuery = useCallback((originalQuery) => {
    if (!boostConfig.enableFieldBoosts) {
      return originalQuery;
    }
    
    // Clean the original query - important to strip any existing field boosts
    let cleanQuery = originalQuery.trim();
    
    // If the query already has field boosts, extract the base query
    // This prevents nesting of field boosts when applying changes multiple times
    if (cleanQuery.includes("^") || cleanQuery.includes(":")) {
      // Try to extract the original search term
      const originalTermMatch = cleanQuery.match(/^[^:]*:([^"]*)["\^]/) || 
                               cleanQuery.match(/^[^:]*:"([^"]*)"/) ||
                               cleanQuery.match(/^([^:]+)$/);
      
      if (originalTermMatch && originalTermMatch[1]) {
        cleanQuery = originalTermMatch[1].trim();
        console.log("Extracted original query term:", cleanQuery);
      } else {
        // If we can't extract the original term, use the original query from props
        cleanQuery = searchQuery;
        console.log("Using original prop query:", cleanQuery);
      }
    }
    
    if (!cleanQuery) return "";
    
    console.log("Transforming query:", cleanQuery, "with config:", boostConfig);
    
    // Sort fields by boost value in descending order
    const sortedFields = Object.entries(boostConfig.fieldBoosts)
      .filter(([_, boost]) => boost !== '' && boost !== null && boost !== undefined && boost > 0)
      .sort(([_, a], [__, b]) => parseFloat(b) - parseFloat(a))
      .map(([field]) => field);
    
    if (sortedFields.length === 0) {
      return cleanQuery;
    }
    
    const parts = [];
    
    // Process each field in order of highest boost first
    for (const field of sortedFields) {
      const boost = parseFloat(boostConfig.fieldBoosts[field]).toFixed(1);
      
      // Split query into terms and phrases
      const terms = [];
      const phrases = [];
      let currentTerm = [];
      let inPhrase = false;
      
      // Split the query into terms and phrases
      const words = cleanQuery.split(/\s+/);
      for (let i = 0; i < words.length; i++) {
        const word = words[i];
        
        if (word.startsWith('"')) {
          inPhrase = true;
          currentTerm = [word.slice(1)];
        } else if (word.endsWith('"')) {
          inPhrase = false;
          currentTerm.push(word.slice(0, -1));
          phrases.push(currentTerm.join(' '));
          currentTerm = [];
        } else if (inPhrase) {
          currentTerm.push(word);
        } else {
          terms.push(word);
        }
      }
      
      // Add single terms
      for (const term of terms) {
        parts.push(`${field}:${term}^${boost}`);
      }
      
      // Add phrases
      for (const phrase of phrases) {
        parts.push(`${field}:"${phrase}"^${boost}`);
      }
      
      // Generate combinations of non-phrase terms if we have at least 2
      if (terms.length >= 2) {
        // Generate combinations of size 2 to n
        for (let size = 2; size <= terms.length; size++) {
          const combinations = getCombinations(terms, size);
          for (const combo of combinations) {
            parts.push(`${field}:"${combo.join(' ')}"^${boost}`);
          }
        }
      }
      
      // Handle mixed terms and phrases
      if (terms.length > 0 && phrases.length > 0) {
        for (const phrase of phrases) {
          for (const term of terms) {
            parts.push(`${field}:"${phrase} ${term}"^${boost}`);
            parts.push(`${field}:"${term} ${phrase}"^${boost}`);
          }
        }
      }
    }
    
    // Join all parts with OR operators
    const result = parts.join(" OR ");
    console.log("Final transformed query:", result);
    return result;
  }, [boostConfig, searchQuery]);
  
  // Helper function to generate combinations
  const getCombinations = (arr, size) => {
    const result = [];
    
    function combine(start, current) {
      if (current.length === size) {
        result.push([...current]);
        return;
      }
      
      for (let i = start; i < arr.length; i++) {
        current.push(arr[i]);
        combine(i + 1, current);
        current.pop();
      }
    }
    
    combine(0, []);
    return result;
  };
  
  // Debug logging
  useEffect(() => {
    console.log('BoostExperiment mounted with:', {
      searchQuery,
      boostConfig
    });
    
    // Log the transformed query for debugging
    if (searchQuery) {
      const transformedQuery = transformQuery(searchQuery);
      console.log('Transformed query:', transformedQuery);
    }
    
    if (searchResults?.results?.ads?.length > 0) {
      // COMPREHENSIVE LOGGING: Log the entire first result to see the complete structure
      console.log("CRITICAL: Complete structure of first result:", JSON.stringify(searchResults.results.ads[0], null, 2));
      
      // Log much more detailed information about the original search results
      const yearTypes = searchResults.results.ads.map(r => typeof r.year).filter((v, i, a) => a.indexOf(v) === i);
      const sampleYears = searchResults.results.ads.slice(0, 5).map(r => r.year);
      const hasArrayYears = searchResults.results.ads.some(r => Array.isArray(r.year));
      const yearStructure = {
        types_present: yearTypes,
        sample_values: sampleYears,
        any_arrays: hasArrayYears,
        original_display: searchResults.results.ads.slice(0, 5).map(r => ({
          title: truncateText(r.title, 30),
          year_display: r.year,
          year_type: typeof r.year,
          year_json: JSON.stringify(r.year)
        }))
      };
      
      console.log("CRITICAL DEBUGGING - Years in original results:", yearStructure);
      
      // Check for alternative fields that might contain year information
      const alternativeFields = searchResults.results.ads.slice(0, 3).map(r => ({
        title: truncateText(r.title, 30),
        pub_year: r.pub_year,
        date: r.date,
        pubdate: r.pubdate,
        publication_year: r.publication_year,
        year_of_publication: r.year_of_publication
      }));
      console.log("CHECKING ALTERNATIVE YEAR FIELDS:", alternativeFields);
      
      console.log("Sample result metadata:", {
        citation: searchResults.results.ads[0].citation_count,
        year: searchResults.results.ads[0].year,
        year_type: typeof searchResults.results.ads[0].year,
        doctype: searchResults.results.ads[0].doctype,
        properties: searchResults.results.ads[0].property
      });
    }
  }, [searchResults, searchQuery, boostConfig]);
  
  // Helper functions for title comparison
  const normalizeTitle = (title) => {
    if (!title) return '';
    
    // Convert to string if not already
    const titleStr = String(title);
    
    // Remove special characters, extra spaces, lowercase everything
    return titleStr.toLowerCase()
      .replace(/[^\w\s]/g, '') // Remove special chars
      .replace(/\s+/g, ' ')    // Replace multiple spaces with single space
      .trim();
  };
  
  const calculateTitleSimilarity = (title1, title2) => {
    if (!title1 || !title2) return 0;
    
    const t1 = normalizeTitle(title1);
    const t2 = normalizeTitle(title2);
    
    // Simple Jaccard similarity for words
    const words1 = t1.split(' ');
    const words2 = t2.split(' ');
    
    const set1 = new Set(words1);
    const set2 = new Set(words2);
    
    const intersection = new Set([...set1].filter(x => set2.has(x)));
    const union = new Set([...set1, ...set2]);
    
    return intersection.size / union.size;
  };
  
  // Helper function to calculate rank changes with improved title matching
  const calculateRankChanges = useCallback((originalResults, boostedResults) => {
    console.log("Calculating rank changes with improved matching...");
    
    if (!originalResults || !boostedResults || 
        originalResults.length === 0 || boostedResults.length === 0) {
      console.warn("Missing results for comparison");
      return boostedResults;
    }
    
    // Create a map of original results for quick lookup
    const originalResultsMap = {};
    originalResults.forEach((result, index) => {
      if (result.title) {
        // Store by normalized title
        const normalizedTitle = normalizeTitle(result.title);
        originalResultsMap[normalizedTitle] = { result, index };
      }
      
      // Also store by bibcode if available
      if (result.bibcode) {
        originalResultsMap[result.bibcode] = { result, index };
      }
    });
    
    console.log(`Created mapping for ${Object.keys(originalResultsMap).length} original results`);
    
    // Process boosted results to add rank change information
    return boostedResults.map((result, newIndex) => {
      let originalData = null;
      
      // Try matching by bibcode first
      if (result.bibcode && originalResultsMap[result.bibcode]) {
        originalData = originalResultsMap[result.bibcode];
        console.log(`Match by bibcode for "${truncateText(result.title, 30)}"`);
      }
      
      // Then try normalized title
      if (!originalData && result.title) {
        const normalizedTitle = normalizeTitle(result.title);
        if (originalResultsMap[normalizedTitle]) {
          originalData = originalResultsMap[normalizedTitle];
          console.log(`Match by normalized title for "${truncateText(result.title, 30)}"`);
        }
      }
      
      // If still no match, try fuzzy title matching
      if (!originalData && result.title) {
        let bestMatchKey = null;
        let bestMatchScore = 0;
        
        // Check similarity with all original results
        Object.keys(originalResultsMap).forEach(key => {
          const original = originalResultsMap[key].result;
          if (original.title) {
            const score = calculateTitleSimilarity(result.title, original.title);
            if (score > 0.8 && score > bestMatchScore) {
              bestMatchScore = score;
              bestMatchKey = key;
            }
          }
        });
        
        if (bestMatchKey) {
          originalData = originalResultsMap[bestMatchKey];
          console.log(`Fuzzy match (${bestMatchScore.toFixed(2)}) for "${truncateText(result.title, 30)}"`);
        }
      }
      
      if (originalData) {
        const originalIndex = originalData.index;
        const rankChange = originalIndex - newIndex;
        
        return {
          ...result,
          originalRank: originalIndex + 1,
          rankChange: rankChange
        };
      } else {
        console.warn(`No match found for "${truncateText(result.title, 30)}"`);
        return {
          ...result,
          originalRank: null,
          rankChange: 0
        };
      }
    });
  }, []);
  
  // Function to handle the initial search
  const handleSearch = async () => {
    if (!searchQuery.trim()) {
      setError('Please enter a search query');
      return;
    }

    setSearchLoading(true);
    setError(null);
    try {
      console.log('Making search request with query:', searchQuery);
      const response = await fetch(`${API_URL}/api/search/compare`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          query: searchQuery,
          sources: ['ads', 'scholar'],
          metrics: ['ndcg@10', 'precision@10', 'recall@10'],
          fields: ['title', 'abstract', 'author', 'year', 'citation_count', 'doctype'],
          max_results: 20,
          quepid_case_id: quepidCaseId || undefined
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to perform search');
      }

      const data = await response.json();
      console.log('Search response:', data);
      
      if (!data.results || !data.results.ads || data.results.ads.length === 0) {
        throw new Error('No results found for the given query');
      }

      setSearchResults(data);
      // Reset boosted results when performing a new search
      setBoostedResults(null);
      
      // If we have a Quepid case ID, fetch the Quepid results
      if (quepidCaseId) {
        try {
          const quepidResponse = await fetch(`${API_URL}/api/quepid/judgments/${quepidCaseId}?query=${encodeURIComponent(searchQuery)}`);
          if (quepidResponse.ok) {
            const quepidData = await quepidResponse.json();
            setQuepidResults(quepidData);
          }
        } catch (err) {
          console.error('Error fetching Quepid results:', err);
        }
      } else {
        setQuepidResults(null);
      }
    } catch (err) {
      console.error('Error performing search:', err);
      setError(err instanceof Error ? err.message : 'An error occurred');
      setSearchResults(null);
    } finally {
      setSearchLoading(false);
    }
  };
  
  // Function to handle running the boost experiment
  const handleRunBoostExperiment = async () => {
    if (!searchResults?.results?.ads) {
      setError('Please perform a search first');
      return;
    }

    setLoading(true);
    setError(null);
    try {
      // Transform the query
      const transformedQuery = transformQuery(searchQuery);
      
      // Debug logging for boost config
      console.log('Current boost config:', boostConfig);
      console.log('Field boosts:', boostConfig.fieldBoosts);
      console.log('Citation boost:', boostConfig.citationBoost);
      console.log('Recency boost:', boostConfig.recencyBoost);
      console.log('Doctype boosts:', boostConfig.doctypeBoosts);
      
      // Make the API request
      const requestBody = {
        query: transformedQuery,
        originalQuery: searchQuery,
        sources: ['ads'],
        metrics: ['ndcg@10', 'precision@10', 'recall@10'],
        fields: ['title', 'abstract', 'author', 'year', 'citation_count', 'doctype'],
        max_results: 20,
        useTransformedQuery: true,
        boost_config: {
          name: "Boosted Results",
          citation_boost: parseFloat(boostConfig.citationBoost) || 0.0,
          min_citations: 1,
          recency_boost: parseFloat(boostConfig.recencyBoost) || 0.0,
          reference_year: parseInt(boostConfig.referenceYear) || new Date().getFullYear(),
          doctype_boosts: Object.fromEntries(
            Object.entries(boostConfig.doctypeBoosts)
              .map(([key, value]) => [key, parseFloat(value) || 0.0])
          ),
          field_boosts: Object.fromEntries(
            Object.entries(boostConfig.fieldBoosts)
              .map(([key, value]) => [key, parseFloat(value) || 0.0])
          )
        }
      };
      
      console.log('Request body:', JSON.stringify(requestBody, null, 2));
      
      const response = await fetch(`${API_URL}/api/search/compare`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestBody),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to run boost experiment');
      }

      const data = await response.json();
      console.log('Boost experiment response:', data);
      
      // Process the results to add rank change information
      if (data.results && data.results.ads) {
        const processedResults = calculateRankChanges(searchResults.results.ads, data.results.ads);
        data.results.ads = processedResults;
      }
      
      setBoostedResults(data);
      setTransformedQuery(transformedQuery);
    } catch (err) {
      console.error('Error running boost experiment:', err);
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setLoading(false);
    }
  };
  
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
    return typeof value === 'number' ? value.toFixed(2) : String(value);
  };
  
  // Function to render boost controls
  const renderBoostControls = () => (
    <Box sx={{ mb: 3 }}>
      <Typography variant="h6" gutterBottom>
        Boost Controls
      </Typography>
      
      {/* Field Boosts */}
      <Box sx={{ mb: 3 }}>
        <Typography variant="subtitle1" gutterBottom>
          Field Boosts
        </Typography>
        <Grid container spacing={2}>
          {Object.entries(boostConfig.fieldBoosts).map(([field, value]) => (
            <Grid item xs={12} sm={6} md={3} key={field}>
              <TextField
                fullWidth
                label={`${field.charAt(0).toUpperCase() + field.slice(1)} Boost`}
                type="number"
                value={value}
                onChange={(e) => handleBoostChange('fieldBoosts', field, e.target.value)}
                inputProps={{ min: 0, step: 0.1 }}
              />
            </Grid>
          ))}
        </Grid>
      </Box>

      {/* Citation Boost */}
      <Box sx={{ mb: 3 }}>
        <Typography variant="subtitle1" gutterBottom>
          Citation Boost
        </Typography>
        <Grid container spacing={2}>
          <Grid item xs={12}>
            <TextField
              fullWidth
              label="Citation Boost Factor"
              type="number"
              value={boostConfig.citationBoost}
              onChange={(e) => handleBoostChange('citationBoost', null, e.target.value)}
              inputProps={{ min: 0, step: 0.1 }}
            />
          </Grid>
        </Grid>
      </Box>

      {/* Recency Boost */}
      <Box sx={{ mb: 3 }}>
        <Typography variant="subtitle1" gutterBottom>
          Recency Boost
        </Typography>
        <Grid container spacing={2}>
          <Grid item xs={12} sm={6}>
            <TextField
              fullWidth
              label="Recency Boost Factor"
              type="number"
              value={boostConfig.recencyBoost}
              onChange={(e) => handleBoostChange('recencyBoost', null, e.target.value)}
              inputProps={{ min: 0, step: 0.1 }}
            />
          </Grid>
          <Grid item xs={12} sm={6}>
            <TextField
              fullWidth
              label="Reference Year"
              type="number"
              value={boostConfig.referenceYear}
              onChange={(e) => handleBoostChange('referenceYear', null, e.target.value)}
              inputProps={{ min: 1900, max: new Date().getFullYear() }}
            />
          </Grid>
        </Grid>
      </Box>

      {/* Document Type Boosts */}
      <Box sx={{ mb: 3 }}>
        <Typography variant="subtitle1" gutterBottom>
          Document Type Boosts
        </Typography>
        <Grid container spacing={2}>
          {Object.entries(boostConfig.doctypeBoosts).map(([type, value]) => (
            <Grid item xs={12} sm={6} md={3} key={type}>
              <TextField
                fullWidth
                label={`${type.charAt(0).toUpperCase() + type.slice(1)} Boost`}
                type="number"
                value={value}
                onChange={(e) => handleBoostChange('doctypeBoosts', type, e.target.value)}
                inputProps={{ min: 0, step: 0.1 }}
              />
            </Grid>
          ))}
        </Grid>
      </Box>

      {/* Transformed Query Display */}
      <TransformedQuery query={searchQuery} fieldBoosts={boostConfig.fieldBoosts} />

      {/* Run Experiment Button */}
      <Button
        variant="contained"
        onClick={handleRunBoostExperiment}
        disabled={loading || !searchResults?.results?.ads}
        sx={{ mt: 2 }}
      >
        {loading ? <CircularProgress size={24} /> : 'Run Boost Experiment'}
      </Button>
    </Box>
  );
  
  // Add the search form section at the top of the component
  const renderSearchForm = () => (
    <Paper sx={{ p: 2, mb: 3 }}>
      <Typography variant="h6" gutterBottom>
        Search Configuration
      </Typography>
      <Grid container spacing={2} alignItems="center">
        <Grid item xs={12} md={4}>
          <TextField
            fullWidth
            label="Search Query"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Enter your search query"
            disabled={searchLoading}
          />
        </Grid>
        <Grid item xs={12} md={4}>
          <TextField
            fullWidth
            label="Information Need"
            value={informationNeed}
            onChange={(e) => setInformationNeed(e.target.value)}
            placeholder="Describe the information need"
            disabled={searchLoading}
            multiline
            rows={2}
          />
        </Grid>
        <Grid item xs={12} md={2}>
          <TextField
            fullWidth
            label="Quepid Case ID (Optional)"
            value={quepidCaseId}
            onChange={(e) => setQuepidCaseId(e.target.value)}
            placeholder="Enter Quepid case ID"
            disabled={searchLoading}
          />
        </Grid>
        <Grid item xs={12} md={2}>
          <Button
            fullWidth
            variant="contained"
            onClick={handleSearch}
            disabled={searchLoading || !searchQuery.trim()}
            startIcon={searchLoading ? <CircularProgress size={20} /> : <SearchIcon />}
          >
            {searchLoading ? 'Searching...' : 'Search'}
          </Button>
        </Grid>
      </Grid>
    </Paper>
  );
  
  // Add this helper function to get judgment for a title
  const getJudgmentForTitle = useCallback((title) => {
    if (!title) return null;
    const normalizedTitle = normalizeTitle(title);
    const judgment = judgmentMap[normalizedTitle];
    console.log(`Looking up judgment for title: "${title}" -> "${normalizedTitle}" -> ${judgment}`);
    return judgment === undefined ? null : judgment;
  }, [judgmentMap]);

  // Function to calculate NDCG
  const calculateNDCG = useCallback((results, k = 10, source = 'original') => {
    if (!results || results.length === 0) {
      console.log('No results available for NDCG calculation');
      return null;
    }

    // Get judgments for the first k results
    const judgments = results.slice(0, k).map(result => {
      const recordId = result.bibcode || normalizeTitle(result.title);
      // First check local judgments with the correct source ID
      const localJudgment = localJudgments[`${source}_${recordId}`];
      // Then check Quepid judgments
      const quepidJudgment = getJudgmentForTitle(result.title);
      
      // Use local judgment if available, otherwise use Quepid judgment
      const judgment = localJudgment?.judgment ?? quepidJudgment;
      
      console.log(`NDCG calculation for ${source} - Record: ${result.title}`, {
        recordId,
        localJudgment,
        quepidJudgment,
        finalJudgment: judgment
      });
      
      return judgment;
    }).filter(j => j !== null && j !== undefined);

    console.log(`${source} NDCG calculation - Found ${judgments.length} judgments:`, judgments);

    if (judgments.length === 0) {
      console.log(`No judgments available for ${source} NDCG calculation`);
      return null;
    }

    // Calculate DCG
    const dcg = judgments.reduce((sum, judgment, i) => {
      const dcgValue = judgment / Math.log2(i + 2);
      console.log(`DCG calculation for ${source} - position ${i + 1}, judgment: ${judgment}, DCG value: ${dcgValue}`);
      return sum + dcgValue;
    }, 0);

    // Calculate IDCG (ideal case where all judgments are perfect)
    const idcg = judgments.reduce((sum, _, i) => {
      const idcgValue = 3 / Math.log2(i + 2); // Assuming 3 is the maximum judgment value
      console.log(`IDCG calculation for ${source} - position ${i + 1}, IDCG value: ${idcgValue}`);
      return sum + idcgValue;
    }, 0);

    const ndcg = idcg === 0 ? 0 : dcg / idcg;
    console.log(`${source} Final NDCG calculation:`, { dcg, idcg, ndcg });
    return ndcg;
  }, [localJudgments, getJudgmentForTitle]);

  // Add effect to update judgment counts when judgments change
  useEffect(() => {
    const updateJudgmentCounts = () => {
      const newCounts = {
        original: { quepid: 0, manual: 0, total: 0 },
        boosted: { quepid: 0, manual: 0, total: 0 },
        scholar: { quepid: 0, manual: 0, total: 0 },
        quepid: { quepid: 0, manual: 0, total: 0 }
      };

      // Count judgments for each source
      ['original', 'boosted', 'scholar', 'quepid'].forEach(source => {
        const results = source === 'original' ? searchResults?.results?.ads :
                       source === 'boosted' ? boostedResults?.results?.ads :
                       source === 'scholar' ? searchResults?.results?.scholar :
                       quepidResults;

        if (results) {
          results.slice(0, 10).forEach(result => {
            const recordId = result.bibcode || normalizeTitle(result.title);
            const hasQuepidJudgment = getJudgmentForTitle(result.title) !== null;
            const hasManualJudgment = localJudgments[`${source}_${recordId}`] !== undefined;
            
            if (hasQuepidJudgment) newCounts[source].quepid++;
            if (hasManualJudgment) newCounts[source].manual++;
            if (hasQuepidJudgment || hasManualJudgment) newCounts[source].total++;
          });
        }
      });

      console.log('Updating judgment counts:', newCounts);
      setJudgmentCounts(newCounts);
    };

    updateJudgmentCounts();
  }, [localJudgments, searchResults, boostedResults, quepidResults, getJudgmentForTitle]);

  // Function to render column header with NDCG score
  const renderColumnHeader = (title, subtitle, results, source) => {
    // Calculate NDCG@10 for the given results
    const ndcg = calculateNDCG(results, 10, source);
    console.log(`NDCG calculation for ${source}:`, { ndcg, results: results?.length });
    
    // Calculate judgment counts directly
    const counts = results ? results.slice(0, 10).reduce((acc, result) => {
      const recordId = result.bibcode || normalizeTitle(result.title);
      const hasQuepidJudgment = getJudgmentForTitle(result.title) !== null;
      const hasManualJudgment = localJudgments[`${source}_${recordId}`] !== undefined;
      
      console.log(`Checking judgments for ${source} - ${result.title}:`, {
        recordId,
        hasQuepidJudgment,
        hasManualJudgment,
        manualJudgment: localJudgments[`${source}_${recordId}`]
      });
      
      if (hasQuepidJudgment) acc.quepid++;
      if (hasManualJudgment) acc.manual++;
      if (hasQuepidJudgment || hasManualJudgment) acc.total++;
      
      return acc;
    }, { quepid: 0, manual: 0, total: 0 }) : { quepid: 0, manual: 0, total: 0 };

    console.log(`Final counts for ${source}:`, counts);

    // Get all NDCG values for ranking
    const allNdcgValues = [
      { source: 'original', value: calculateNDCG(searchResults?.results?.ads, 10, 'original') },
      { source: 'boosted', value: calculateNDCG(boostedResults?.results?.ads, 10, 'boosted') },
      { source: 'scholar', value: calculateNDCG(searchResults?.results?.scholar, 10, 'scholar') },
      { source: 'quepid', value: calculateNDCG(quepidResults, 10, 'quepid') }
    ].filter(item => item.value !== null);

    // Sort by NDCG value in descending order
    allNdcgValues.sort((a, b) => b.value - a.value);

    // Find the rank of current source
    const currentRank = allNdcgValues.findIndex(item => item.source === source);

    // Define border colors based on rank
    const getBorderColor = (rank) => {
      if (rank === 0) return '#4caf50'; // Bright green for highest
      if (rank === 1) return '#2196f3'; // Blue for second
      if (rank === 2) return '#ff9800'; // Orange for third
      return '#f44336'; // Red for lowest
    };

    const borderColor = currentRank !== -1 ? getBorderColor(currentRank) : 'transparent';

    return (
      <Paper sx={{ 
        p: 1, 
        bgcolor: source === 'original' ? 'grey.100' : 
          source === 'boosted' ? 'primary.light' : 
          source === 'scholar' ? 'error.light' : 'success.light',
        color: source === 'original' ? 'inherit' : 'primary.contrastText',
        borderRadius: 1,
        border: '3px solid',
        borderColor: borderColor,
        transition: 'border-color 0.3s ease'
      }}>
        <Typography variant="subtitle1" align="center" fontWeight="bold">
          {title}
        </Typography>
        <Typography variant="caption" align="center" display="block" sx={{ 
          color: source === 'original' ? 'text.secondary' : 'rgba(255,255,255,0.8)' 
        }}>
          {subtitle}
        </Typography>
        <Box sx={{ mt: 0.5 }}>
          <Typography variant="caption" align="center" display="block" sx={{ 
            color: source === 'original' ? 'text.secondary' : 'rgba(255,255,255,0.8)',
            fontWeight: 'bold'
          }}>
            NDCG@10: {ndcg !== null ? ndcg.toFixed(3) : 'N/A'}
          </Typography>
          <Typography variant="caption" align="center" display="block" sx={{ 
            color: source === 'original' ? 'text.secondary' : 'rgba(255,255,255,0.8)',
            fontSize: '0.7rem',
            fontWeight: counts.total > 0 ? 'bold' : 'normal'
          }}>
            {counts.total > 0 ? (
              <>
                Total Judgments: {counts.total}
                {counts.quepid > 0 && ` (Quepid: ${counts.quepid}`}
                {counts.quepid > 0 && counts.manual > 0 && ' | '}
                {counts.manual > 0 && `Manual: ${counts.manual}`}
                {counts.quepid > 0 && ')'}
              </>
            ) : (
              'No judgments'
            )}
          </Typography>
        </Box>
      </Paper>
    );
  };

  // Function to handle loading more results
  const handleLoadMore = (source) => {
    setVisibleResults(prev => ({
      ...prev,
      [source]: prev[source] + 10
    }));
  };

  // Update the results rendering section
  const renderResultsList = (results, source) => {
    if (!results || results.length === 0) {
      return (
        <ListItem>
          <ListItemText
            primary={`No ${source} results available`}
            secondary={source === 'boosted' ? 
              "Configure and apply boost factors to see how they affect the ranking" :
              source === 'quepid' ? 
              "Enter a Quepid case ID to see relevance judgments" :
              "No matching results found"}
          />
        </ListItem>
      );
    }

    const visibleItems = results.slice(0, visibleResults[source]);

    return (
      <>
        {visibleItems.map((result, index) => 
          renderResultItem(result, index, source)
        )}
        {results.length > visibleResults[source] && (
          <ListItem>
            <Button
              fullWidth
              onClick={() => handleLoadMore(source)}
              sx={{ mt: 1 }}
            >
              Load More
            </Button>
          </ListItem>
        )}
      </>
    );
  };

  // Modify the createJudgmentMap function
  const createJudgmentMap = useCallback((quepidResults) => {
    if (!quepidResults) return {};
    
    const map = {};
    console.log('Creating judgment map from Quepid results:', quepidResults);
    
    quepidResults.forEach(result => {
      // Log the raw result structure
      console.log('Processing Quepid result:', result);
      
      // Check for judgment score in different possible locations
      const judgmentScore = result.judgment_score ?? result.score ?? result.rating ?? result.judgment;
      const title = result.title;
      
      if (title && judgmentScore !== undefined) {
        const normalizedTitle = normalizeTitle(title);
        map[normalizedTitle] = judgmentScore;
        console.log(`Added judgment for title: "${title}" -> "${normalizedTitle}" with score: ${judgmentScore}`);
      } else {
        console.log('Skipping result due to missing title or score:', result);
      }
    });
    
    console.log('Final judgment map:', map);
    return map;
  }, []);

  // Add this effect to update the judgment map when Quepid results change
  useEffect(() => {
    if (quepidResults) {
      console.log('Quepid results updated:', quepidResults);
      const newMap = createJudgmentMap(quepidResults);
      setJudgmentMap(newMap);
    }
  }, [quepidResults, createJudgmentMap]);

  // Function to handle judgment selection
  const handleJudgmentSelect = (recordId, judgment, sourceId) => {
    console.log('Handling judgment select:', { recordId, judgment, sourceId });
    
    // Convert judgment to number and check if it's a valid judgment value
    const judgmentValue = judgment === '' ? null : Number(judgment);
    
    if (judgmentValue === null) {
      // If clearing the judgment, just remove it
      setLocalJudgments(prev => {
        const newJudgments = { ...prev };
        delete newJudgments[`${sourceId}_${recordId}`];
        console.log('Cleared judgment, new state:', newJudgments);
        return newJudgments;
      });
      return;
    }

    // For new judgments, store with default values
    setLocalJudgments(prev => {
      const existingJudgment = prev[`${sourceId}_${recordId}`];
      const judgmentType = existingJudgment === undefined ? 'new' : 
                          existingJudgment.judgment !== judgmentValue ? 'changed' : 'existing';

      const newJudgments = {
        ...prev,
        [`${sourceId}_${recordId}`]: {
          judgment: judgmentValue,
          note: existingJudgment?.note || '',
          type: judgmentType,
          timestamp: new Date().toISOString()
        }
      };
      
      console.log('Updated judgments, new state:', newJudgments);
      return newJudgments;
    });
  };

  // Function to handle adding/editing a note
  const handleAddNote = (recordId, sourceId) => {
    const currentJudgment = localJudgments[`${sourceId}_${recordId}`];
    setCurrentJudgmentData({
      recordId,
      judgment: currentJudgment?.judgment,
      sourceId,
      note: currentJudgment?.note || ''
    });
    setJudgmentNoteDialogOpen(true);
  };

  // Function to confirm judgment note
  const handleConfirmNote = (note) => {
    if (!currentJudgmentData) return;

    const { recordId, judgment, sourceId } = currentJudgmentData;
    
    setLocalJudgments(prev => {
      const existingJudgment = prev[`${sourceId}_${recordId}`];
      return {
        ...prev,
        [`${sourceId}_${recordId}`]: {
          ...existingJudgment,
          note,
          timestamp: new Date().toISOString()
        }
      };
    });

    setJudgmentNoteDialogOpen(false);
    setCurrentJudgmentData(null);
  };

  // Function to render judgment selector
  const renderJudgmentSelector = (record) => {
    const recordId = record.bibcode || normalizeTitle(record.title);
    const sourceId = record.source_id || 'original';
    const quepidJudgment = getJudgmentForTitle(record.title);
    const userJudgment = localJudgments[`${sourceId}_${recordId}`];
    const currentJudgment = userJudgment?.judgment !== undefined ? userJudgment.judgment : quepidJudgment;
    const hasQuepidJudgment = quepidJudgment !== null;

    return (
      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          {hasQuepidJudgment && (
            <Tooltip title={`Quepid Judgment: ${quepidJudgment}`}>
              <Chip 
                label="Quepid" 
                size="small"
                variant="outlined"
                color="info"
                sx={{ height: 20, '& .MuiChip-label': { px: 1, fontSize: '0.7rem' } }}
              />
            </Tooltip>
          )}
          <FormControl size="small" sx={{ minWidth: 120 }}>
            <Select
              value={currentJudgment !== null && currentJudgment !== undefined ? currentJudgment : ''}
              onChange={(e) => handleJudgmentSelect(recordId, e.target.value, sourceId)}
              displayEmpty
              sx={{ height: 20, fontSize: '0.7rem' }}
            >
              <MenuItem value="" disabled>
                <em>Add Judgment</em>
              </MenuItem>
              <MenuItem value={0}>Poor (0)</MenuItem>
              <MenuItem value={1}>Fair (1)</MenuItem>
              <MenuItem value={2}>Good (2)</MenuItem>
              <MenuItem value={3}>Perfect (3)</MenuItem>
            </Select>
          </FormControl>
        </Box>
        {currentJudgment !== null && currentJudgment !== undefined && (
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Button
              size="small"
              variant="text"
              onClick={() => handleAddNote(recordId, sourceId)}
              sx={{ 
                height: 24,
                minWidth: 'auto',
                px: 1,
                fontSize: '0.7rem',
                textTransform: 'none'
              }}
            >
              {userJudgment?.note ? "Edit Note" : "Add Note"}
            </Button>
            {userJudgment?.note && (
              <Tooltip title={userJudgment.note}>
                <Chip 
                  label="View Note" 
                  size="small"
                  variant="outlined"
                  color="secondary"
                  onClick={() => handleAddNote(recordId, sourceId)}
                  sx={{ 
                    height: 20, 
                    '& .MuiChip-label': { px: 1, fontSize: '0.7rem' },
                    cursor: 'pointer'
                  }}
                />
              </Tooltip>
            )}
          </Box>
        )}
      </Box>
    );
  };

  // Function to handle record expansion
  const handleRecordExpand = (record) => {
    setSelectedRecord(record);
    setDetailsDialogOpen(true);
  };

  // Function to export judgments to TXT
  const handleExportJudgments = () => {
    // Get all records that have judgments (both Quepid and manual)
    const recordsWithJudgments = [];

    // Helper function to add a record with judgment
    const addRecordWithJudgment = (record, judgment, source, judgmentType = 'existing') => {
      // Format the source name
      const formattedSource = source === 'ads' ? 'ADS' : 
                            source === 'quepid' ? 'Quepid' :
                            source === 'boosted' ? 'Boosted' :
                            source === 'scholar' ? 'Google Scholar' : source;

      // Get the judgment value - explicitly check for null/undefined
      let judgmentValue;
      if (typeof judgment === 'object') {
        judgmentValue = judgment.judgment;
      } else {
        judgmentValue = judgment;
      }

      // Only add if we have a valid judgment (including 0)
      if (judgmentValue !== null && judgmentValue !== undefined && judgmentValue >= 0) {
        recordsWithJudgments.push({
          query: searchQuery,
          information_need: informationNeed,
          title: record.title,
          judgment: judgmentValue,
          note: judgment?.note || '',
          type: judgmentType,
          source: formattedSource,
          timestamp: judgment?.timestamp || new Date().toISOString(),
          // Add boost information if available
          boosts: source === 'boosted' ? {
            field_boosts: boostConfig.fieldBoosts,
            citation_boost: boostConfig.citationBoost,
            recency_boost: boostConfig.recencyBoost,
            doctype_boosts: boostConfig.doctypeBoosts,
            reference_year: boostConfig.referenceYear
          } : null
        });
      }
    };

    // Check ADS results
    searchResults?.results?.ads?.forEach(record => {
      const recordId = record.bibcode || normalizeTitle(record.title);
      const userJudgment = localJudgments[`original_${recordId}`];
      const quepidJudgment = getJudgmentForTitle(record.title);

      if (userJudgment !== undefined) {
        addRecordWithJudgment(record, userJudgment, 'ads', userJudgment.type);
      } else if (quepidJudgment !== null && quepidJudgment !== undefined) {
        addRecordWithJudgment(record, { judgment: quepidJudgment }, 'ads', 'quepid');
      }
    });

    // Check Google Scholar results
    searchResults?.results?.scholar?.forEach(record => {
      const recordId = normalizeTitle(record.title);
      const userJudgment = localJudgments[`scholar_${recordId}`];
      if (userJudgment !== undefined) {
        addRecordWithJudgment(record, userJudgment, 'scholar', userJudgment.type);
      }
    });

    // Check boosted results
    boostedResults?.results?.ads?.forEach(record => {
      const recordId = record.bibcode || normalizeTitle(record.title);
      const userJudgment = localJudgments[`boosted_${recordId}`];
      if (userJudgment !== undefined) {
        addRecordWithJudgment(record, userJudgment, 'boosted', userJudgment.type);
      }
    });

    if (recordsWithJudgments.length === 0) {
      setError('No judgments to export. Please add some judgments first.');
      return;
    }

    // Calculate NDCG@10 scores for each source
    const ndcgScores = {
      original: calculateNDCG(searchResults?.results?.ads, 10, 'original'),
      boosted: calculateNDCG(boostedResults?.results?.ads, 10, 'boosted'),
      scholar: calculateNDCG(searchResults?.results?.scholar, 10, 'scholar'),
      quepid: calculateNDCG(quepidResults, 10, 'quepid')
    };

    // Helper function to pad string to fixed width
    const padString = (str, width) => {
      const strValue = String(str || '');
      return strValue.padEnd(width);
    };

    // Helper function to wrap text to multiple lines
    const wrapText = (text, width) => {
      // Convert to string and handle null/undefined
      const textStr = text?.toString() || '';
      if (!textStr) return [''];
      
      const words = textStr.split(' ');
      const lines = [];
      let currentLine = '';
      
      words.forEach(word => {
        if (currentLine.length + word.length + 1 <= width) {
          currentLine += (currentLine ? ' ' : '') + word;
        } else {
          lines.push(currentLine);
          currentLine = word;
        }
      });
      if (currentLine) {
        lines.push(currentLine);
      }
      return lines;
    };

    // Helper function to format a row with proper spacing
    const formatRow = (values, widths) => {
      const wrappedTitle = wrapText(values[0], widths[0]);
      const otherValues = values.slice(1);
      
      // Format the first line
      const firstLine = [
        padString(wrappedTitle[0], widths[0]),
        ...otherValues.map((value, index) => padString(value, widths[index + 1]))
      ].join('  ');

      // Format any additional lines for the title
      const additionalLines = wrappedTitle.slice(1).map(line => 
        padString(line, widths[0]) + '  ' + 
        otherValues.map((_, index) => padString('', widths[index + 1])).join('  ')
      );

      return [firstLine, ...additionalLines].join('\n');
    };

    // Column widths
    const columnWidths = {
      title: 80,  // Increased width for title
      judgment: 8,
      note: 25,
      type: 8,
      source: 15,
      timestamp: 24
    };

    // Group records by query and information need
    const groupedRecords = recordsWithJudgments.reduce((acc, record) => {
      const key = `${record.query}|${record.information_need}`;
      if (!acc[key]) {
        acc[key] = {
          query: record.query,
          information_need: record.information_need,
          records: []
        };
      }
      acc[key].records.push(record);
      return acc;
    }, {});

    // Format as fixed-width text for the detailed report
    const detailedReport = [
      // Header section with metadata
      '=== Search Configuration ===',
      `Timestamp: ${new Date().toISOString()}`,
      '',
      '=== NDCG@10 Scores ===',
      `Original Results: ${ndcgScores.original?.toFixed(3) || 'N/A'}`,
      `Boosted Results: ${ndcgScores.boosted?.toFixed(3) || 'N/A'}`,
      `Google Scholar Results: ${ndcgScores.scholar?.toFixed(3) || 'N/A'}`,
      `Quepid Results: ${ndcgScores.quepid?.toFixed(3) || 'N/A'}`,
      '',
      '=== Boost Configuration ===',
      'Field Boosts:',
      ...Object.entries(boostConfig.fieldBoosts).map(([field, value]) => `  ${field}: ${value}`),
      '',
      `Citation Boost: ${boostConfig.citationBoost}`,
      `Recency Boost: ${boostConfig.recencyBoost}`,
      `Reference Year: ${boostConfig.referenceYear}`,
      '',
      'Document Type Boosts:',
      ...Object.entries(boostConfig.doctypeBoosts).map(([type, value]) => `  ${type}: ${value}`),
      '',
      '=== Judgments ===',
      // Column headers
      formatRow([
        'Title',
        'Judgment',
        'Note',
        'Type',
        'Source',
        'Timestamp'
      ], Object.values(columnWidths)),
      // Separator line
      '-'.repeat(Object.values(columnWidths).reduce((a, b) => a + b + 2, 0)),
      // Grouped records
      ...Object.values(groupedRecords).flatMap(group => [
        // Group header with extra newline
        '',
        `Query: ${group.query}`,
        group.information_need ? `Information Need: ${group.information_need}` : '',
        // Group records
        ...group.records.map(record => formatRow([
          record.title,
          record.judgment,
          record.note,
          record.type,
          record.source,
          record.timestamp
        ], Object.values(columnWidths)))
      ])
    ].join('\n');

    // Create a simple version with just query, title, judgment, and source
    const simpleReport = [
      'Query\tTitle\tJudgment\tSource',
      ...recordsWithJudgments.map(record => [
        record.query,
        record.title,
        record.judgment,
        record.source
      ].join('\t'))
    ].join('\n');

    // Get timestamp for filenames
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');

    // Export detailed report
    const detailedBlob = new Blob([detailedReport], { type: 'text/plain;charset=utf-8' });
    const detailedLink = document.createElement('a');
    const detailedUrl = URL.createObjectURL(detailedBlob);
    detailedLink.setAttribute('href', detailedUrl);
    detailedLink.setAttribute('download', `relevance_report_${timestamp}.txt`);
    document.body.appendChild(detailedLink);
    detailedLink.click();
    document.body.removeChild(detailedLink);

    // Export simple report
    const simpleBlob = new Blob([simpleReport], { type: 'text/plain;charset=utf-8' });
    const simpleLink = document.createElement('a');
    const simpleUrl = URL.createObjectURL(simpleBlob);
    simpleLink.setAttribute('href', simpleUrl);
    simpleLink.setAttribute('download', `relevance_judgments_${timestamp}.txt`);
    document.body.appendChild(simpleLink);
    simpleLink.click();
    document.body.removeChild(simpleLink);
  };

  // Function to render expanded record details in a dialog
  const renderDetailsDialog = () => (
    <Dialog 
      open={detailsDialogOpen} 
      onClose={() => setDetailsDialogOpen(false)}
      maxWidth="md"
      fullWidth
    >
      {selectedRecord && (
        <>
          <DialogTitle>
            <Typography variant="h6" component="div">
              {selectedRecord.title}
            </Typography>
          </DialogTitle>
          <DialogContent>
            <Box sx={{ mt: 2 }}>
              <Typography variant="subtitle1" gutterBottom>
                <strong>Authors:</strong> {formatAuthors(selectedRecord.author)}
              </Typography>
              {selectedRecord.abstract && (
                <Typography variant="body1" paragraph>
                  <strong>Abstract:</strong> {selectedRecord.abstract}
                </Typography>
              )}
              <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, mt: 2 }}>
                {selectedRecord.year && (
                  <Chip 
                    label={`Year: ${selectedRecord.year}`} 
                    variant="outlined"
                  />
                )}
                {selectedRecord.citation_count !== undefined && (
                  <Chip 
                    label={`Citations: ${selectedRecord.citation_count}`} 
                    variant="outlined"
                  />
                )}
                {selectedRecord.doctype && (
                  <Chip 
                    label={`Type: ${selectedRecord.doctype}`} 
                    variant="outlined"
                  />
                )}
              </Box>
              <Box sx={{ mt: 3 }}>
                {renderJudgmentSelector(selectedRecord)}
              </Box>
            </Box>
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setDetailsDialogOpen(false)}>Close</Button>
          </DialogActions>
        </>
      )}
    </Dialog>
  );

  // Function to render judgment note dialog
  const renderJudgmentNoteDialog = () => (
    <Dialog open={judgmentNoteDialogOpen} onClose={() => setJudgmentNoteDialogOpen(false)}>
      <DialogTitle>Add/Edit Judgment Note</DialogTitle>
      <DialogContent>
        <Typography variant="body2" gutterBottom>
          Add a note explaining your judgment (optional):
        </Typography>
        <TextField
          fullWidth
          multiline
          rows={4}
          value={currentJudgmentData?.note || ''}
          onChange={(e) => setCurrentJudgmentData(prev => ({ ...prev, note: e.target.value }))}
          placeholder="Enter your judgment note here..."
          sx={{ mt: 2 }}
        />
      </DialogContent>
      <DialogActions>
        <Button onClick={() => setJudgmentNoteDialogOpen(false)}>Cancel</Button>
        <Button onClick={() => handleConfirmNote(currentJudgmentData?.note || '')} variant="contained">
          Save Note
        </Button>
      </DialogActions>
    </Dialog>
  );

  // Modify the renderResultItem function to remove inline expansion
  const renderResultItem = (result, index, containerId) => {
    const recordId = result.bibcode || normalizeTitle(result.title);
    // Set the correct source ID based on the container
    const sourceId = containerId === 'scholar' ? 'scholar' : containerId;

    return (
      <ListItem 
        id={`${containerId}-item-${index}`}
        divider
        sx={{ 
          px: 2, 
          py: 1,
          position: 'relative',
          transition: 'background-color 0.3s ease',
          whiteSpace: 'normal'
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
              <Box sx={{ width: '100%', wordBreak: 'break-word' }}>
                <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 1 }}>
                  <Typography 
                    variant="body2" 
                    sx={{ 
                      fontWeight: 'medium',
                      flexGrow: 1,
                      cursor: 'pointer',
                      '&:hover': {
                        color: 'primary.main'
                      }
                    }}
                    onClick={() => handleRecordExpand(result)}
                  >
                    {truncateText(result.title, 60)}
                  </Typography>
                  <IconButton 
                    size="small" 
                    onClick={() => handleRecordExpand(result)}
                    sx={{ 
                      ml: 'auto',
                      flexShrink: 0,
                      p: 0.5
                    }}
                  >
                    <ExpandMoreIcon />
                  </IconButton>
                </Box>
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5, mt: 0.5 }}>
                  <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
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
                    {containerId === 'boosted' && result.boosted_score !== undefined && result.boosted_score !== null && (
                      <Chip 
                        label={`Boost: ${result.boosted_score.toFixed(1)}`} 
                        size="small"
                        color="primary"
                        sx={{ 
                          height: 20, 
                          '& .MuiChip-label': { px: 1, fontSize: '0.7rem' },
                          fontWeight: 'bold', 
                          bgcolor: `rgba(25, 118, 210, ${Math.min(result.boosted_score / 20, 1)})`
                        }}
                      />
                    )}
                  </Box>
                  {renderJudgmentSelector({...result, source_id: sourceId})}
                </Box>
              </Box>
            </Box>
          }
        />
      </ListItem>
    );
  };

  // Add export button to the top of the results panel
  const renderExportButton = () => (
    <Button
      startIcon={<FileDownloadIcon />}
      variant="outlined"
      size="small"
      onClick={() => setExportDialogOpen(true)}
      sx={{ ml: 2 }}
    >
      Export Judgments
    </Button>
  );

  // Update the export dialog to show more information
  const renderExportDialog = () => (
    <Dialog open={exportDialogOpen} onClose={() => setExportDialogOpen(false)}>
      <DialogTitle>Export Judgments</DialogTitle>
      <DialogContent>
        <Typography variant="body2" gutterBottom>
          This will export a comprehensive report including:
        </Typography>
        <List dense>
          <ListItem>
            <ListItemText 
              primary="Search Configuration" 
              secondary="Query, information need, and timestamp"
            />
          </ListItem>
          <ListItem>
            <ListItemText 
              primary="NDCG@10 Scores" 
              secondary="Performance metrics for all result sets"
            />
          </ListItem>
          <ListItem>
            <ListItemText 
              primary="Boost Configuration" 
              secondary="All boost factors used for the experiment"
            />
          </ListItem>
          <ListItem>
            <ListItemText 
              primary="Judgments" 
              secondary="All judgments with notes, types, and associated boost configurations"
            />
          </ListItem>
        </List>
      </DialogContent>
      <DialogActions>
        <Button onClick={() => setExportDialogOpen(false)}>Cancel</Button>
        <Button onClick={handleExportJudgments} variant="contained">
          Export
        </Button>
      </DialogActions>
    </Dialog>
  );
  
  // Add toggle button for boost controls
  const renderBoostControlsToggle = () => (
    <Button
      startIcon={showBoostControls ? <ExpandLessIcon /> : <ExpandMoreIcon />}
      variant="outlined"
      size="small"
      onClick={() => setShowBoostControls(!showBoostControls)}
      sx={{ ml: 2 }}
    >
      {showBoostControls ? 'Hide Boost Controls' : 'Show Boost Controls'}
    </Button>
  );

  return (
    <Box sx={{ width: '100%', p: 2 }}>
      {renderSearchForm()}
      
      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      {searchLoading && (
        <Box sx={{ display: 'flex', justifyContent: 'center', my: 4 }}>
          <CircularProgress />
        </Box>
      )}

      {!searchLoading && (!searchResults || !searchResults.results || !searchResults.results.ads || searchResults.results.ads.length === 0) ? (
        <Alert severity="info">
          {searchResults === null ? 
            'Enter a search query and click Search to begin experimenting with boost factors.' :
            'No results found for the given query. Please try a different search term.'}
        </Alert>
      ) : (
        <Grid container spacing={2}>
          {/* Boost Controls */}
          {showBoostControls && (
            <Grid item xs={12} md={4}>
              {renderBoostControls()}
            </Grid>
          )}

          {/* Results Panel */}
          <Grid item xs={12} md={showBoostControls ? 8 : 12}>
            <Paper sx={{ p: 2 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                <Typography variant="h6" sx={{ flexGrow: 1 }}>
                  Ranking Results
                </Typography>
                {loading && <CircularProgress size={24} sx={{ ml: 2 }} />}
                {renderExportButton()}
                {renderBoostControlsToggle()}
              </Box>

              <Box sx={{ display: 'flex', mb: 2 }}>
                {/* Title Headers */}
                <Box sx={{ width: showBoostControls ? '25%' : '30%', pr: 1 }}>
                  {renderColumnHeader(
                    'Original Results',
                    'Default ranking without boosts',
                    searchResults?.results?.ads,
                    'original'
                  )}
                </Box>
                <Box sx={{ width: showBoostControls ? '25%' : '30%', px: 1 }}>
                  {renderColumnHeader(
                    'Boosted Results',
                    'Re-ranked based on current boost settings',
                    boostedResults?.results?.ads,
                    'boosted'
                  )}
                </Box>
                <Box sx={{ width: showBoostControls ? '25%' : '30%', px: 1 }}>
                  {renderColumnHeader(
                    'Google Scholar Results',
                    'For comparison',
                    searchResults?.results?.scholar,
                    'scholar'
                  )}
                </Box>
                <Box sx={{ width: showBoostControls ? '25%' : '30%', pl: 1 }}>
                  {renderColumnHeader(
                    'Quepid Results',
                    'Relevance judgments',
                    quepidResults,
                    'quepid'
                  )}
                </Box>
              </Box>
              
              <Box sx={{ display: 'flex', position: 'relative' }}>
                {/* Original Results */}
                <Box sx={{ 
                  width: showBoostControls ? '25%' : '30%', 
                  pr: 1, 
                  height: '65vh', 
                  overflow: 'hidden',
                  display: 'flex',
                  flexDirection: 'column'
                }} id="original-results-container">
                  <List sx={{ 
                    bgcolor: 'background.paper', 
                    border: '1px solid', 
                    borderColor: 'divider', 
                    borderRadius: 1,
                    overflow: 'auto',
                    overflowX: 'hidden',
                    flexGrow: 1
                  }}>
                    {renderResultsList(searchResults?.results?.ads, 'original')}
                  </List>
                </Box>
                
                {/* Boosted Results */}
                <Box sx={{ 
                  width: showBoostControls ? '25%' : '30%', 
                  px: 1, 
                  height: '65vh', 
                  overflow: 'hidden',
                  display: 'flex',
                  flexDirection: 'column'
                }} id="boosted-results-container">
                  <List sx={{ 
                    bgcolor: 'background.paper', 
                    border: '1px solid', 
                    borderColor: 'divider', 
                    borderRadius: 1,
                    overflow: 'auto',
                    overflowX: 'hidden',
                    flexGrow: 1
                  }}>
                    {renderResultsList(boostedResults?.results?.ads, 'boosted')}
                  </List>
                </Box>

                {/* Google Scholar Results */}
                <Box sx={{ 
                  width: showBoostControls ? '25%' : '30%', 
                  px: 1, 
                  height: '65vh', 
                  overflow: 'hidden',
                  display: 'flex',
                  flexDirection: 'column'
                }} id="google-scholar-container">
                  <List sx={{ 
                    bgcolor: 'background.paper', 
                    border: '1px solid', 
                    borderColor: 'divider', 
                    borderRadius: 1,
                    overflow: 'auto',
                    overflowX: 'hidden',
                    flexGrow: 1
                  }}>
                    {renderResultsList(searchResults?.results?.scholar, 'scholar')}
                  </List>
                </Box>

                {/* Quepid Results */}
                <Box sx={{ 
                  width: showBoostControls ? '25%' : '30%', 
                  pl: 1, 
                  height: '65vh', 
                  overflow: 'hidden',
                  display: 'flex',
                  flexDirection: 'column'
                }} id="quepid-results-container">
                  <List sx={{ 
                    bgcolor: 'background.paper', 
                    border: '1px solid', 
                    borderColor: 'divider', 
                    borderRadius: 1,
                    overflow: 'auto',
                    overflowX: 'hidden',
                    flexGrow: 1
                  }}>
                    {renderResultsList(quepidResults, 'quepid')}
                  </List>
                </Box>
              </Box>
            </Paper>
          </Grid>
        </Grid>
      )}
      
      {renderExportDialog()}
      {renderDetailsDialog()}
      {renderJudgmentNoteDialog()}
    </Box>
  );
};

export default BoostExperiment; 
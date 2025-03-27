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
import { experimentService, API_URL as DEFAULT_API_URL } from '../services/api';
import { List as ListIcon } from '@mui/icons-material';
import LaunchIcon from '@mui/icons-material/Launch';

/**
 * Component for experimenting with different boost factors and their impact on ranking
 * 
 * @param {Object} props - Component props
 * @param {Array} props.originalResults - The original search results to re-rank
 * @param {string} props.query - The search query used to retrieve results
 * @param {function} props.onRunNewSearch - Callback function when user wants to run a new search
 * @param {Object} props.results - Full search results including Google Scholar for comparison
 */
const BoostExperiment = ({ originalResults, query, API_URL = DEFAULT_API_URL, onRunNewSearch, results }) => {
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
    citeBoostWeight: 0.0,
    
    // Recency boost
    enableRecencyBoost: true,
    recencyBoostWeight: 0.0,
    recencyFunction: "exponential", // Changed to match backend default
    recencyMultiplier: 0.01, // Changed to match backend default
    recencyMidpoint: 36,
    
    // Document type boost
    enableDoctypeBoost: true,
    doctypeBoostWeight: 0.0,
    
    // Refereed boost
    enableRefereedBoost: true,
    refereedBoostWeight: 0.0,
    
    // Combination method
    combinationMethod: "sum",
    
    // Field-specific query boosts (new addition)
    enableFieldBoosts: true,
    fieldBoosts: {
      title: 0.0,
      abstract: 0.0,
      author: 0.0,
      year: 0.0,
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
        // This should be the very basic query that was first used
        cleanQuery = query;
        console.log("Using original prop query:", cleanQuery);
      }
    }
    
    if (!cleanQuery) return "";
    
    console.log("Transforming query:", cleanQuery, "with config:", boostConfig.queryTransformation);
    
    // Create a simpler query format with field boosts - greatly simplified!
    const parts = [];
    
    // For each field, add a boosted term
    Object.entries(boostConfig.fieldBoosts).forEach(([field, boost]) => {
      if (boost > 0) {
        // Format the boost with one decimal place
        const formattedBoost = parseFloat(boost).toFixed(1);
        
        // Handle phrase queries (if the original query contains spaces)
        if (cleanQuery.includes(' ')) {
          parts.push(`${field}:"${cleanQuery}"^${formattedBoost}`);
        } else {
          parts.push(`${field}:${cleanQuery}^${formattedBoost}`);
        }
      }
    });
    
    // If no field boosts are applied, use the original query
    if (parts.length === 0) {
      return cleanQuery;
    }
    
    // Join all parts with OR operators
    const result = parts.join(" OR ");
    console.log("Final transformed query:", result);
    return result;
  }, [boostConfig, query]);
  
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
  
  // Helper functions for title comparison
  const normalizeTitle = (title) => {
    if (!title) return '';
    // Remove special characters, extra spaces, lowercase everything
    return title.toLowerCase()
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
  
  // Apply the boost experiment
  const applyBoosts = useCallback(async () => {
    console.log("🚀 applyBoosts called with originalResults length:", originalResults?.length);
    
    if (!originalResults || originalResults.length === 0) {
      console.log("❌ No original results to modify");
      setError('No original results to modify');
      return;
    }
    
    console.log("✅ Starting boost process with config:", boostConfig);
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
      
      // Generate the transformed query - but don't use it for the boost experiment
      // We'll just log it for reference
      const transformedQuery = transformQuery(query);
      console.log("Transformed query (for reference only):", transformedQuery);
      
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
            console.log(`Extracted year ${extractedYear} from bibcode ${result.bibcode} for "${truncateText(result.title, 30)}"`);
          }
        }
        
        // Extract year from the URL if we still don't have a year
        if (extractedYear === null && result.url) {
          const urlYearMatch = result.url.match(/\/abs\/(\d{4})/);
          if (urlYearMatch && urlYearMatch[1]) {
            extractedYear = parseInt(urlYearMatch[1], 10);
            console.log(`Extracted year ${extractedYear} from URL ${result.url} for "${truncateText(result.title, 30)}"`);
          }
        }
        
        // Check if year is embedded in the title (sometimes in parentheses at the end)
        if (extractedYear === null && result.title) {
          const titleYearMatch = result.title.match(/\((\d{4})\)/);
          if (titleYearMatch && titleYearMatch[1]) {
            extractedYear = parseInt(titleYearMatch[1], 10);
            console.log(`Extracted year ${extractedYear} from title for "${truncateText(result.title, 30)}"`);
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
      
      // Make a direct API call to match the endpoint in the running backend
      console.log(`📡 Sending request to: ${API_URL}/api/boost-experiment`);
      const response = await fetch(`${API_URL}/api/boost-experiment`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          query, // Use the original query, not the transformed one
          // Only include transformedQuery if needed for debugging
          // transformedQuery,
          results: processedResults,
          boostConfig: normalizedBoostConfig
        })
      });
      
      console.log('📡 Boost experiment response status:', response.status);
      
      if (!response.ok) {
        const errorText = await response.text();
        console.error('❌ Boost experiment error:', errorText);
        throw new Error(`Failed to apply boosts: ${errorText}`);
      }
      
      const data = await response.json();
      console.log('📡 Received boosted results data:', data);
      
      // Calculate rank changes directly with our helper function
      if (data.results && data.results.length > 0) {
        data.results = calculateRankChanges(originalResults, data.results);
      }
      
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
      setError(err.message || "Failed to apply boosts. Please check the console for details.");
    } finally {
      setLoading(false);
    }
  }, [API_URL, boostConfig, originalResults, query, transformQuery, calculateRankChanges]);
  
  // Function to run a completely new search with current field weights
  const runNewSearch = useCallback(() => {
    console.log("🚀 Apply Changes button clicked!");
    
    if (!query) {
      console.log("❌ No query to search with");
      setError('No query to search with');
      return;
    }
    
    // Store the current Google Scholar results and original results for preservation
    const currentScholarResults = results?.results?.scholar;
    const cachedOriginalResults = originalResults;
    
    // Check if any field boosts are active - if so, we need to rerun the search
    const anyFieldBoostsActive = Object.values(boostConfig.fieldBoosts).some(val => val > 0);
    const anyOtherBoostsActive = boostConfig.citeBoostWeight > 0 || 
                                boostConfig.recencyBoostWeight > 0 || 
                                boostConfig.doctypeBoostWeight > 0 ||
                                boostConfig.refereedBoostWeight > 0;
    
    // Only for citation and recency boosts, we can apply them locally
    if (!anyFieldBoostsActive && anyOtherBoostsActive) {
      console.log("✅ Only applying local boosts (citation/recency/doctype/refereed)");
      applyBoosts();
      return;
    }
    
    // For field boosts, we need to run a new search
    if (anyFieldBoostsActive && typeof onRunNewSearch === 'function') {
      console.log("🔄 Field boosts active, rerunning search with new weights");
      
      // Show loading indicator
      setSearchLoading(true);
      
      try {
        const transformedQuery = transformQuery(query);
        console.log("Running search with transformed query:", transformedQuery);
        
        // Pass the transformed query and boost configuration to the parent
        onRunNewSearch(transformedQuery, boostConfig)
          .then((newResults) => {
            setSearchLoading(false);
            console.log("New search completed successfully", newResults);
            
            // If the search response includes both original and boosted results,
            // we need to calculate the rank changes
            if (newResults.originalResults && newResults.results && newResults.results.origin) {
              console.log("Calculating rank changes between original and boosted results");
              
              // Create a local copy of the boosted results to add rank changes
              const boostedWithRankChanges = {
                results: calculateRankChanges(
                  newResults.originalResults, 
                  newResults.results.origin
                )
              };
              
              setBoostedResults(boostedWithRankChanges);
            }
            
            // If we had Google Scholar results before and they're not in the new results,
            // manually add them back to preserve them
            if (currentScholarResults && !newResults.results.scholar) {
              console.log("Manually restoring Google Scholar results in component state");
              if (!newResults.results) newResults.results = {};
              newResults.results.scholar = currentScholarResults;
            }
          })
          .catch(err => {
            console.error("Error running new search:", err);
            setError("Failed to run new search: " + (err.message || 'Unknown error'));
            setSearchLoading(false);
          });
      } catch (error) {
        console.error("Error in runNewSearch:", error);
        setError("Failed to transform query: " + (error.message || 'Unknown error'));
        setSearchLoading(false);
      }
    } else {
      // If no boosts are active, still show something
      console.log("✅ No active boosts, still applying empty boost configuration");
      applyBoosts();
    }
    
  }, [query, transformQuery, boostConfig, onRunNewSearch, applyBoosts, results, originalResults, calculateRankChanges]);
  
  // Apply boosts whenever configuration changes
  useEffect(() => {
    console.log("🔄 Initial useEffect to apply boosts on component mount");
    
    // Apply boosts on initial component mount to ensure results are shown
    if (originalResults && originalResults.length > 0 && !boostedResults) {
      console.log("✅ Applying initial boosts on mount");
      applyBoosts();
    }
    
  }, [originalResults, applyBoosts, boostedResults]);
  
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
            onClick={() => {
              console.log("🔘 Apply Changes button clicked directly");
              runNewSearch();
            }}
            disabled={searchLoading || loading}
            sx={{ ml: 1 }}
          >
            {(searchLoading || loading) ? <CircularProgress size={20} sx={{ mr: 1 }} color="inherit" /> : null}
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
              onChange={(e, value) => handleConfigChange('citeBoostWeight', value)}
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
              onChange={(e, value) => handleConfigChange('recencyBoostWeight', value)}
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
                    <Box sx={{ width: '33%', pr: 1 }}>
                      <Paper sx={{ p: 1, bgcolor: 'grey.100', borderRadius: 1 }}>
                        <Typography variant="subtitle1" align="center" fontWeight="bold">
                          Original Results
                        </Typography>
                        <Typography variant="caption" align="center" display="block" color="text.secondary">
                          Default ranking without boosts
                        </Typography>
                      </Paper>
                    </Box>
                    <Box sx={{ width: '33%', px: 1 }}>
                      <Paper sx={{ p: 1, bgcolor: 'primary.light', color: 'primary.contrastText', borderRadius: 1 }}>
                        <Typography variant="subtitle1" align="center" fontWeight="bold">
                          Boosted Results
                        </Typography>
                        <Typography variant="caption" align="center" display="block" sx={{ color: 'rgba(255,255,255,0.8)' }}>
                          Re-ranked based on current boost settings
                        </Typography>
                      </Paper>
                    </Box>
                    <Box sx={{ width: '33%', pl: 1 }}>
                      <Paper sx={{ p: 1, bgcolor: 'error.light', color: 'error.contrastText', borderRadius: 1 }}>
                        <Typography variant="subtitle1" align="center" fontWeight="bold">
                          Google Scholar Results
                        </Typography>
                        <Typography variant="caption" align="center" display="block" sx={{ color: 'rgba(255,255,255,0.8)' }}>
                          For comparison
                        </Typography>
                      </Paper>
                    </Box>
                  </Box>
                  
                  <Box sx={{ display: 'flex', position: 'relative' }}>
                    {/* Original Results */}
                    <Box sx={{ 
                      width: '33%', 
                      pr: 1, 
                      height: '65vh', 
                      overflow: 'hidden',  // Change from 'auto' to 'hidden'
                      display: 'flex',
                      flexDirection: 'column'
                    }} id="original-results-container">
                      <List sx={{ 
                        bgcolor: 'background.paper', 
                        border: '1px solid', 
                        borderColor: 'divider', 
                        borderRadius: 1,
                        overflow: 'auto',  // Allow only vertical scrolling inside the list
                        overflowX: 'hidden',  // Hide horizontal scrolling
                        flexGrow: 1
                      }}>
                        {originalResults.map((result, index) => {
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
                                id={`original-item-${index}`}
                                key={result.bibcode || result.title} 
                                divider
                                sx={{ 
                                  px: 2, 
                                  py: 1,
                                  position: 'relative',
                                  transition: 'background-color 0.3s ease',
                                  whiteSpace: 'normal'  // Allow text to wrap
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
                                {boostedResults && boostedResults.results && (
                                  <Box 
                                    className="connector-point"
                                    data-target={`boosted-item-${boostedResults.results.findIndex(
                                      r => r.bibcode === result.bibcode || r.title === result.title
                                    )}`}
                                    sx={{ 
                                      position: 'absolute', 
                                      right: 0, 
                                      height: '100%', 
                                      width: 4
                                    }} 
                                  />
                                )}
                              </ListItem>
                            </Tooltip>
                          );
                        })}
                      </List>
                    </Box>
                    
                    {/* Boosted Results */}
                    <Box sx={{ 
                      width: '33%', 
                      px: 1, 
                      height: '65vh', 
                      overflow: 'hidden',  // Change from 'auto' to 'hidden'
                      display: 'flex',
                      flexDirection: 'column'
                    }} id="boosted-results-container">
                      <List sx={{ 
                        bgcolor: 'background.paper', 
                        border: '1px solid', 
                        borderColor: 'primary.light', 
                        borderRadius: 1,
                        overflow: 'auto',  // Allow only vertical scrolling inside the list
                        overflowX: 'hidden',  // Hide horizontal scrolling
                        flexGrow: 1
                      }}>
                        {boostedResults.results.map((result, index) => {
                          // Get the rankChange directly from the result
                          const rankChange = result.rankChange || 0;
                          
                          // Determine border style based on magnitude of change
                          let borderStyle = {};
                          if (Math.abs(rankChange) >= 5) {
                            // Major change - thicker border
                            borderStyle = {
                              borderLeft: rankChange !== 0 ? '6px solid' : 'none',
                              borderLeftColor: rankChange > 0 ? 'success.main' : rankChange < 0 ? 'error.main' : 'transparent',
                              bgcolor: rankChange !== 0 ? (rankChange > 0 ? 'success.50' : 'error.50') : 'transparent'
                            };
                          } else if (rankChange !== 0) {
                            // Minor change - standard border
                            borderStyle = {
                              borderLeft: '4px solid',
                              borderLeftColor: rankChange > 0 ? 'success.main' : 'error.main',
                            };
                          }
                          
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
                                    <strong>Original Rank:</strong> {result.originalRank || 'N/A'}
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
                                id={`boosted-item-${index}`}
                                key={result.bibcode || result.title} 
                                divider
                                sx={{ 
                                  px: 2, 
                                  py: 1,
                                  position: 'relative',
                                  ...borderStyle,
                                  transition: 'background-color 0.3s ease',
                                  whiteSpace: 'normal'  // Allow text to wrap
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
                                              sx={{ 
                                                height: 20, 
                                                '& .MuiChip-label': { px: 1, fontSize: '0.7rem' },
                                                fontWeight: Math.abs(rankChange) >= 5 ? 'bold' : 'normal'
                                              }}
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
                                {result.originalRank && (
                                  <Box 
                                    className="connector-point"
                                    data-target={`original-item-${result.originalRank - 1}`}
                                    data-change={rankChange}
                                    sx={{ 
                                      position: 'absolute', 
                                      left: 0, 
                                      height: '100%', 
                                      width: 4
                                    }} 
                                  />
                                )}
                              </ListItem>
                            </Tooltip>
                          );
                        })}
                      </List>
                    </Box>

                    {/* Google Scholar Results */}
                    <Box sx={{ 
                      width: '33%', 
                      pl: 1, 
                      height: '65vh', 
                      overflow: 'hidden',  // Change from 'auto' to 'hidden'
                      display: 'flex',
                      flexDirection: 'column'
                    }} id="google-scholar-container">
                      <List sx={{ 
                        bgcolor: 'background.paper', 
                        border: '1px solid', 
                        borderColor: 'error.light', 
                        borderRadius: 1,
                        overflow: 'auto',  // Allow vertical scrolling inside the list
                        overflowX: 'hidden',  // Hide horizontal scrolling
                        flexGrow: 1
                      }}>
                        {results && results.results && results.results.scholar ? (
                          results.results.scholar.map((result, index) => (
                            <Tooltip
                              key={`scholar-${index}`}
                              title={
                                <Box>
                                  <Typography variant="subtitle2">{result.title}</Typography>
                                  <Typography variant="body2">
                                    <strong>Authors:</strong> {formatAuthors(result.authors)}
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
                                divider
                                sx={{ 
                                  px: 2, 
                                  py: 1,
                                  position: 'relative',
                                  transition: 'background-color 0.3s ease',
                                  whiteSpace: 'normal'  // Allow text to wrap
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
                                {result.url && (
                                  <IconButton 
                                    size="small" 
                                    href={result.url} 
                                    target="_blank"
                                    aria-label="Open in Google Scholar"
                                  >
                                    <LaunchIcon fontSize="small" />
                                  </IconButton>
                                )}
                              </ListItem>
                            </Tooltip>
                          ))
                        ) : (
                          <ListItem>
                            <ListItemText
                              primary="No Google Scholar results available"
                              secondary="Please run a search with Google Scholar enabled to see comparison results"
                            />
                          </ListItem>
                        )}
                      </List>
                    </Box>
                  </Box>
                  
                  {/* Add useEffect to draw connecting lines between matching items */}
                  <Box component="script" dangerouslySetInnerHTML={{ __html: `
                    // Draw connecting lines between matching items when the component mounts
                    setTimeout(function() {
                      // Remove any existing connectors
                      document.querySelectorAll('.result-connector').forEach(el => el.remove());
                      
                      // For each boosted result, find its original position and draw a line
                      document.querySelectorAll('#boosted-results-container .connector-point').forEach(point => {
                        const targetId = point.getAttribute('data-target');
                        const rankChange = parseInt(point.getAttribute('data-change') || '0');
                        
                        if (!targetId) return;
                        
                        const targetEl = document.getElementById(targetId);
                        if (!targetEl) return;
                        
                        // Get positions
                        const boostedRect = point.getBoundingClientRect();
                        const originalRect = targetEl.getBoundingClientRect();
                        
                        // Create connector
                        const connector = document.createElement('div');
                        connector.className = 'result-connector';
                        
                        // Set style
                        connector.style.position = 'absolute';
                        connector.style.zIndex = '10';
                        connector.style.height = '2px';
                        connector.style.opacity = '0.7';
                        connector.style.pointerEvents = 'none';
                        
                        // Set color based on rank change
                        if (rankChange > 0) {
                          connector.style.backgroundColor = '#4caf50'; // success.main
                        } else if (rankChange < 0) {
                          connector.style.backgroundColor = '#f44336'; // error.main
                        } else {
                          connector.style.backgroundColor = '#9e9e9e'; // grey.500
                        }
                        
                        // Get parent container
                        const container = document.querySelector('.MuiGrid-container');
                        
                        // Calculate positions relative to the container
                        const rect = container.getBoundingClientRect();
                        
                        const fromX = boostedRect.left - rect.left;
                        const fromY = boostedRect.top - rect.top + boostedRect.height / 2;
                        const toX = originalRect.right - rect.left;
                        const toY = originalRect.top - rect.top + originalRect.height / 2;
                        
                        const length = Math.sqrt(Math.pow(toX - fromX, 2) + Math.pow(toY - fromY, 2));
                        const angle = Math.atan2(toY - fromY, toX - fromX) * 180 / Math.PI;
                        
                        // Apply styles
                        connector.style.width = length + 'px';
                        connector.style.left = fromX + 'px';
                        connector.style.top = fromY + 'px';
                        connector.style.transform = 'rotate(' + angle + 'deg)';
                        connector.style.transformOrigin = '0 0';
                        
                        // Add to document
                        container.appendChild(connector);
                      });
                    }, 500);
                  `}} />
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
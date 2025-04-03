import React, { useState, useEffect, useMemo } from 'react';
import { 
  Box, Typography, TextField, Button, 
  Grid, Paper, CircularProgress, Chip,
  Card, CardContent, CardActions, 
  Divider, Alert, Tooltip, IconButton
} from '@mui/material';
import StarIcon from '@mui/icons-material/Star';
import LinkIcon from '@mui/icons-material/Link';
import SearchIcon from '@mui/icons-material/Search';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import InfoIcon from '@mui/icons-material/Info';
import CompareArrowsIcon from '@mui/icons-material/CompareArrows';

// Default similarity data
import similarityData from '../data/similarityData.json';

// Import specific JSON files for operator and embeddings
import operatorData from '../data/2022ApJ...931...44P_operator.json';
import embeddingsData from '../data/2022ApJ...931...44P_embeddings.json';

import { searchService } from '../services/api';

/**
 * SimilarityTests component for comparing "similar" operator search results with LLM judgments
 * 
 * @returns {React.ReactElement} The SimilarityTests component
 */
const SimilarityTests = () => {
  // State for search query and options
  const [query, setQuery] = useState('similar(2022ApJ...931...44P)');
  const [referenceBibcode, setReferenceBibcode] = useState('2022ApJ...931...44P');
  const [loading, setLoading] = useState(false);
  const [operatorResults, setOperatorResults] = useState(null);
  const [embeddingsResults, setEmbeddingsResults] = useState(null);
  const [error, setError] = useState(null);
  const [originalPaper, setOriginalPaper] = useState(null);
  const [matchingBibcodes, setMatchingBibcodes] = useState([]);
  
  // Parse bibcode from query
  const extractBibcode = (query) => {
    const match = query.match(/similar\(([^)]+)\)/);
    return match ? match[1] : null;
  };
  
  // Load the appropriate data files based on the bibcode
  const loadDataForBibcode = (bibcode) => {
    if (!bibcode) return;
    
    try {
      console.log(`Loading data for bibcode: ${bibcode}`);
      
      // In a real implementation, this would be dynamic imports
      // For now, we're using the static imports above and filtering
      let operatorJson = null;
      let embeddingsJson = null;
      
      if (bibcode === '2022ApJ...931...44P') {
        operatorJson = operatorData;
        embeddingsJson = embeddingsData;
        
        console.log('Loaded operator data:', operatorJson);
        console.log('Loaded embeddings data:', embeddingsJson);
      } else {
        // Fallback to our default data
        operatorJson = similarityData;
        embeddingsJson = similarityData;
      }
      
      // Set the original paper data from the embeddings file
      setOriginalPaper(embeddingsJson);
      
      // Set the operator results (left column)
      if (operatorJson && operatorJson.search_results) {
        console.log(`Setting operator results with ${operatorJson.search_results.length} items`);
        // Limit to top 10
        setOperatorResults(operatorJson.search_results.slice(0, 10));
      } else {
        console.warn('No search_results found in operator JSON');
        setOperatorResults([]);
      }
      
      // Set the embeddings results (right column)
      if (embeddingsJson && embeddingsJson.search_results) {
        console.log(`Setting embeddings results with ${embeddingsJson.search_results.length} items`);
        // Limit to top 10
        setEmbeddingsResults(embeddingsJson.search_results.slice(0, 10));
      } else {
        console.warn('No search_results found in embeddings JSON');
        setEmbeddingsResults([]);
      }
      
      // Compare bibcodes between the two result sets to find matches
      const operatorBibcodes = operatorJson?.search_results?.map(paper => paper.bibcode) || [];
      const embeddingsBibcodes = embeddingsJson?.search_results?.map(paper => paper.bibcode) || [];
      
      const matches = operatorBibcodes.filter(bibcode => embeddingsBibcodes.includes(bibcode));
      setMatchingBibcodes(matches);
      console.log('Matching bibcodes between operator and embeddings:', matches);
      
    } catch (err) {
      console.error(`Error loading data for bibcode ${bibcode}:`, err);
      setError(`Error loading data for bibcode ${bibcode}: ${err.message}`);
      // Fallback to default data
      setOriginalPaper(similarityData);
      setOperatorResults(similarityData.search_results || []);
      setEmbeddingsResults(similarityData.search_results || []);
    }
  };
  
  // Initial load on component mount
  useEffect(() => {
    console.log('SimilarityTests component mounted');
    loadDataForBibcode(referenceBibcode);
  }, []);
  
  // Load data when reference bibcode changes
  const handleReferenceBibcodeChange = () => {
    setLoading(true);
    loadDataForBibcode(referenceBibcode);
    
    // Update the query to match the new bibcode
    setQuery(`similar(${referenceBibcode})`);
    setLoading(false);
  };

  // Generate score chip with appropriate color based on score
  const renderScoreChip = (score, model) => {
    if (score === null || score === undefined) return null;
    
    let color = 'default';
    if (score >= 4) color = 'success';
    else if (score >= 3) color = 'primary';
    else if (score >= 2) color = 'warning';
    else color = 'error';

    return (
      <Chip 
        size="small" 
        color={color} 
        label={`${model}: ${score}`} 
        icon={<StarIcon />} 
        sx={{ mr: 1, my: 0.5 }}
      />
    );
  };

  // Render a paper card with title, abstract, and actions
  const renderPaperCard = (paper, idx, showScores = false, isLLMColumn = false) => {
    const isMatch = matchingBibcodes.includes(paper.bibcode);
    
    return (
      <Card key={idx} variant="outlined" sx={{ 
        mb: 2, 
        height: '100%', 
        display: 'flex', 
        flexDirection: 'column',
        position: 'relative',
        pl: 1,
        borderColor: isMatch ? 'success.main' : 'inherit',
        boxShadow: isMatch ? '0 0 0 1px #4caf50' : 'inherit'
      }}>
        {/* Rank indicator */}
        <Box 
          sx={{ 
            position: 'absolute', 
            left: 0, 
            top: 0, 
            bottom: 0, 
            width: '8px', 
            bgcolor: isLLMColumn ? 'secondary.main' : 'primary.main',
            borderTopLeftRadius: '4px',
            borderBottomLeftRadius: '4px'
          }} 
        />
        
        <CardContent sx={{ 
          flexGrow: 1, 
          pb: 1, // Reduce bottom padding to make cards more compact
          display: 'flex',
          flexDirection: 'column'
        }}>
          <Box display="flex" alignItems="flex-start">
            <Chip 
              label={idx + 1} 
              size="small" 
              color={isLLMColumn ? "secondary" : "primary"}
              sx={{ 
                mr: 1, 
                mt: 0.3,
                minWidth: 40, 
                fontWeight: 'bold',
                fontSize: '1rem',
                px: 1,
                '& .MuiChip-label': {
                  whiteSpace: 'nowrap',
                  overflow: 'visible',
                  textOverflow: 'clip'
                }
              }}
            />
            <Typography variant="h6" component="div" noWrap sx={{ flexGrow: 1 }}>
              {paper.title}
            </Typography>
            
            {isMatch && (
              <Tooltip title="This paper appears in both results">
                <CheckCircleIcon 
                  color="success" 
                  sx={{ ml: 1, mt: 0.3, flexShrink: 0 }} 
                />
              </Tooltip>
            )}
          </Box>
          <Typography variant="body2" color="text.secondary" gutterBottom>
            {paper.bibcode}
          </Typography>
          
          {/* Authors and year */}
          {paper.authors && (
            <Typography variant="body2" color="text.secondary" gutterBottom noWrap>
              {Array.isArray(paper.authors) 
                ? paper.authors.slice(0, 3).join(', ') + (paper.authors.length > 3 ? ', et al.' : '')
                : paper.authors}
              {paper.year ? ` (${paper.year})` : ''}
            </Typography>
          )}
          
          {/* Citation count if available */}
          {paper.citation_count !== undefined && (
            <Typography variant="body2" color="text.secondary" gutterBottom>
              Citations: {paper.citation_count}
            </Typography>
          )}
          
          <Divider sx={{ my: 1 }} />
          
          {/* Fixed height abstract container */}
          <Box sx={{ height: 100, overflow: 'hidden', mb: 1, flexShrink: 0 }}>
            <Typography variant="body2">
              {paper.abstract?.length > 250 
                ? `${paper.abstract.substring(0, 250)}...` 
                : paper.abstract}
            </Typography>
          </Box>
          
          {/* Fixed height scores container */}
          <Box mt="auto" sx={{ minHeight: showScores ? 60 : 0 }}>
            {showScores && (
              <>
                <Typography variant="body2" fontWeight="bold" gutterBottom>
                  LLM Relevance Scores:
                </Typography>
                <Box>
                  {renderScoreChip(paper.claude_score, 'Claude')}
                  {renderScoreChip(paper.deepseek_score, 'DeepSeek')}
                  {renderScoreChip(paper.gemini_score, 'Gemini')}
                </Box>
              </>
            )}
          </Box>
        </CardContent>
        <CardActions>
          <Button 
            size="small" 
            startIcon={<LinkIcon />}
            href={`https://ui.adsabs.harvard.edu/abs/${paper.bibcode}`}
            target="_blank"
            rel="noopener noreferrer"
          >
            View on ADS
          </Button>
        </CardActions>
      </Card>
    );
  };

  // Calculate NDCG@10 for a result set based on LLM relevance scores
  const calculateNDCG = (results, k = 10) => {
    if (!results || results.length === 0) return 0;
    
    // Limit to top k results
    const topK = results.slice(0, k);
    
    // Calculate DCG
    let dcg = 0;
    topK.forEach((paper, idx) => {
      // Average the available LLM scores (claude_score, deepseek_score, gemini_score)
      const scores = [
        paper.claude_score,
        paper.deepseek_score,
        paper.gemini_score
      ].filter(score => score !== undefined && score !== null);
      
      // If no scores available, use 0
      const avgScore = scores.length > 0 ? scores.reduce((a, b) => a + b, 0) / scores.length : 0;
      
      // Calculate relevance gain (2^rel - 1)
      const relevanceGain = Math.pow(2, avgScore) - 1;
      
      // Position discount (log2(pos+1))
      const positionDiscount = Math.log2(idx + 2); // +2 because idx is 0-based and log2(1) = 0
      
      // Add to DCG
      dcg += relevanceGain / positionDiscount;
    });
    
    // Create sorted array of all papers by average score for IDCG calculation
    const allPapersByScore = [...results].sort((a, b) => {
      const aScores = [a.claude_score, a.deepseek_score, a.gemini_score]
        .filter(score => score !== undefined && score !== null);
      const bScores = [b.claude_score, b.deepseek_score, b.gemini_score]
        .filter(score => score !== undefined && score !== null);
      
      const aAvg = aScores.length > 0 ? aScores.reduce((acc, score) => acc + score, 0) / aScores.length : 0;
      const bAvg = bScores.length > 0 ? bScores.reduce((acc, score) => acc + score, 0) / bScores.length : 0;
      
      return bAvg - aAvg; // Sort descending
    });
    
    // Calculate IDCG (ideal DCG)
    let idcg = 0;
    allPapersByScore.slice(0, k).forEach((paper, idx) => {
      const scores = [
        paper.claude_score,
        paper.deepseek_score,
        paper.gemini_score
      ].filter(score => score !== undefined && score !== null);
      
      const avgScore = scores.length > 0 ? scores.reduce((a, b) => a + b, 0) / scores.length : 0;
      const relevanceGain = Math.pow(2, avgScore) - 1;
      const positionDiscount = Math.log2(idx + 2);
      
      idcg += relevanceGain / positionDiscount;
    });
    
    // Avoid division by zero
    if (idcg === 0) return 0;
    
    // Calculate NDCG
    return dcg / idcg;
  };

  // Calculate NDCG scores for both result sets
  const operatorNDCG = useMemo(() => {
    return calculateNDCG(operatorResults);
  }, [operatorResults]);
  
  const embeddingsNDCG = useMemo(() => {
    return calculateNDCG(embeddingsResults);
  }, [embeddingsResults]);

  return (
    <Box>
      <Typography variant="h5" gutterBottom>
        Similarity Tests
      </Typography>
      <Typography paragraph>
        Compare similarity results from ADS operator with LLM-judged similar papers. 
        Enter a bibcode to see the comparison data.
      </Typography>
      
      <Paper elevation={3} sx={{ p: 3, mb: 4 }}>
        <Grid container spacing={2} alignItems="center">
          <Grid item xs={12} sm={7}>
            <TextField
              fullWidth
              label="Reference Paper Bibcode"
              variant="outlined"
              value={referenceBibcode}
              onChange={(e) => setReferenceBibcode(e.target.value)}
              placeholder="Enter a bibcode (e.g., 2022ApJ...931...44P)"
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  handleReferenceBibcodeChange();
                }
              }}
              disabled={loading}
            />
          </Grid>
          <Grid item xs={6} sm={2.5}>
            <Button
              variant="contained"
              color="primary"
              onClick={handleReferenceBibcodeChange}
              disabled={loading}
              startIcon={loading ? <CircularProgress size={18} /> : <CompareArrowsIcon />}
              fullWidth
            >
              {loading ? "Loading..." : "Load Data"}
            </Button>
          </Grid>
          <Grid item xs={6} sm={2.5}>
            <Button
              variant="outlined"
              color="secondary"
              onClick={() => {
                setReferenceBibcode('2022ApJ...931...44P');
                setQuery('similar(2022ApJ...931...44P)');
                loadDataForBibcode('2022ApJ...931...44P');
              }}
              disabled={loading}
              fullWidth
            >
              Reset
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

      {/* Original Paper */}
      {originalPaper && (
        <Paper elevation={3} sx={{ p: 3, mb: 4, bgcolor: 'white' }}>
          <Box display="flex" justifyContent="space-between" alignItems="flex-start">
            <Typography variant="h6" gutterBottom color="primary.main">
              Reference Paper
            </Typography>
            
            <Tooltip 
              title={
                <Typography variant="body2">
                  {originalPaper.abstract || "No abstract available"}
                </Typography>
              }
              enterDelay={300}
              leaveDelay={200}
              arrow
              placement="top-start"
              componentsProps={{
                tooltip: {
                  sx: { 
                    maxWidth: 600, 
                    p: 2, 
                    backgroundColor: "white", 
                    color: "text.primary", 
                    boxShadow: 3,
                    '& .MuiTooltip-arrow': {
                      color: 'white',
                    }
                  }
                }
              }}
            >
              <IconButton size="small" color="primary">
                <InfoIcon />
              </IconButton>
            </Tooltip>
          </Box>
          
          <Typography variant="h6" component="div" gutterBottom color="text.primary">
            {originalPaper.title}
          </Typography>
          <Typography variant="body2" gutterBottom color="text.secondary">
            {originalPaper.bibcode}
          </Typography>
          <Divider sx={{ my: 1 }} />
          <Typography variant="body2" paragraph color="text.secondary">
            {originalPaper.abstract?.length > 300 
              ? `${originalPaper.abstract.substring(0, 300)}...` 
              : originalPaper.abstract}
          </Typography>
          <Button 
            size="small" 
            variant="outlined"
            startIcon={<LinkIcon />}
            href={`https://ui.adsabs.harvard.edu/abs/${originalPaper.bibcode}`}
            target="_blank"
            rel="noopener noreferrer"
            color="primary"
          >
            View on ADS
          </Button>
        </Paper>
      )}

      {/* Debug information */}
      {process.env.NODE_ENV === 'development' && (
        <Alert severity="info" sx={{ mt: 2, mb: 2 }}>
          <Typography variant="subtitle2">Debug Info:</Typography>
          <Typography variant="body2">
            Operator Results: {operatorResults ? operatorResults.length : 'none'} items
          </Typography>
          <Typography variant="body2">
            Embeddings Results: {embeddingsResults ? embeddingsResults.length : 'none'} items
          </Typography>
          <Typography variant="body2">
            Matching Bibcodes: {matchingBibcodes.length} items
          </Typography>
        </Alert>
      )}

      {/* Results Comparison */}
      <Box display="flex" alignItems="center" mb={2}>
        <Typography variant="h6">
          Similarity Comparison
        </Typography>
        {matchingBibcodes.length > 0 && (
          <Chip 
            label={`${matchingBibcodes.length} matching papers`} 
            color="success" 
            size="small" 
            icon={<CheckCircleIcon />} 
            sx={{ ml: 2 }} 
          />
        )}
      </Box>
      
      <Grid container spacing={2}>
        {/* Operator Results (left column) */}
        <Grid item xs={12} md={6}>
          <Paper elevation={2} sx={{ p: 2, height: '100%' }}>
            <Box display="flex" justifyContent="space-between" alignItems="center" mb={1}>
              <Typography variant="subtitle1" gutterBottom sx={{ fontWeight: 'bold', color: 'primary.main' }}>
                ADS Similar Operator Results
              </Typography>
              
              {!loading && operatorResults && (
                <Chip 
                  label={`NDCG@10: ${operatorNDCG.toFixed(3)}`}
                  color="primary"
                  size="medium"
                  sx={{ fontWeight: 'bold' }}
                />
              )}
            </Box>
            
            <Typography variant="body2" color="text.secondary" paragraph>
              Results from {referenceBibcode}_operator.json
            </Typography>
            <Divider sx={{ mb: 2 }} />
            
            {loading && (
              <Box display="flex" justifyContent="center" alignItems="center" flexDirection="column" my={4}>
                <CircularProgress size={40} />
                <Typography variant="body2" sx={{ mt: 2 }}>
                  Loading operator data...
                </Typography>
              </Box>
            )}
            
            {operatorResults && !loading && (
              <Box>
                {operatorResults.length > 0 ? (
                  operatorResults.map((paper, idx) => (
                    <Box key={idx} mb={2}>
                      {renderPaperCard(paper, idx, true, false)}
                    </Box>
                  ))
                ) : (
                  <Alert severity="info">No operator results found</Alert>
                )}
              </Box>
            )}
            
            {!operatorResults && !loading && (
              <Alert severity="info">
                Enter a reference bibcode to see operator results
              </Alert>
            )}
          </Paper>
        </Grid>
        
        {/* Embeddings Results (right column) */}
        <Grid item xs={12} md={6}>
          <Paper elevation={2} sx={{ p: 2, height: '100%' }}>
            <Box display="flex" justifyContent="space-between" alignItems="center" mb={1}>
              <Typography variant="subtitle1" gutterBottom sx={{ fontWeight: 'bold', color: 'secondary.main' }}>
                Embeddings Results (title and abstract)
              </Typography>
              
              {!loading && embeddingsResults && (
                <Chip 
                  label={`NDCG@10: ${embeddingsNDCG.toFixed(3)}`}
                  color="secondary"
                  size="medium"
                  sx={{ fontWeight: 'bold' }}
                />
              )}
            </Box>
            
            <Typography variant="body2" color="text.secondary" paragraph>
              Results from {referenceBibcode}_embeddings.json
            </Typography>
            <Divider sx={{ mb: 2 }} />
            
            {loading && (
              <Box display="flex" justifyContent="center" alignItems="center" flexDirection="column" my={4}>
                <CircularProgress size={40} />
                <Typography variant="body2" sx={{ mt: 2 }}>
                  Loading embeddings data...
                </Typography>
              </Box>
            )}
            
            {embeddingsResults && !loading && (
              <Box>
                {embeddingsResults.length > 0 ? (
                  embeddingsResults.map((paper, idx) => (
                    <Box key={idx} mb={2}>
                      {renderPaperCard(paper, idx, true, true)}
                    </Box>
                  ))
                ) : (
                  <Alert severity="info">No embeddings results found</Alert>
                )}
              </Box>
            )}
            
            {!embeddingsResults && !loading && (
              <Alert severity="info">
                Enter a reference bibcode to see embeddings results
              </Alert>
            )}
          </Paper>
        </Grid>
      </Grid>
    </Box>
  );
};

export default SimilarityTests; 
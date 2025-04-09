import React, { useState } from 'react';
import {
  Box,
  TextField,
  Button,
  Typography,
  CircularProgress,
  Alert,
} from '@mui/material';
import QueryIntentResults from '../components/QueryIntentResults';
import { transformQuery } from '../services/queryIntentService';

const QueryIntentPage: React.FC = () => {
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [results, setResults] = useState<any>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setResults(null);

    try {
      const response = await transformQuery(query);
      setResults(response);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box sx={{ maxWidth: 800, mx: 'auto', p: 3 }}>
      <Typography variant="h4" gutterBottom>
        Query Intent Analysis
      </Typography>
      
      <Typography variant="body1" paragraph>
        Enter a search query to analyze its intent and get transformed results.
        The system will use LLM-based intent detection to understand your query
        and transform it into a more effective search query.
      </Typography>
      
      <Box component="form" onSubmit={handleSubmit} sx={{ mb: 4 }}>
        <TextField
          fullWidth
          label="Search Query"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          margin="normal"
          required
        />
        <Button
          type="submit"
          variant="contained"
          color="primary"
          disabled={loading || !query.trim()}
          sx={{ mt: 2 }}
        >
          {loading ? <CircularProgress size={24} /> : 'Analyze Query'}
        </Button>
      </Box>
      
      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}
      
      {results && (
        <QueryIntentResults
          originalQuery={results.original_query}
          transformedQuery={results.transformed_query}
          intent={results.intent}
          intentConfidence={results.intent_confidence}
          explanation={results.explanation}
          searchResults={results.search_results}
        />
      )}
    </Box>
  );
};

export default QueryIntentPage; 
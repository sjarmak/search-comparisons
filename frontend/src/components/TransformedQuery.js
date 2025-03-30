import React, { useState } from 'react';
import { Box, Button, Paper, Typography, CircularProgress } from '@mui/material';
import { API_URL } from '../services/api';

/**
 * Component to display and transform queries with field boosts.
 * 
 * @param {Object} props - Component props
 * @param {string} props.query - The input query to transform
 * @param {Object} props.fieldBoosts - Dictionary of field boosts to apply
 * @returns {React.ReactElement} The TransformedQuery component
 */
export const TransformedQuery = ({ query, fieldBoosts }) => {
  const [transformedQuery, setTransformedQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleTransform = async () => {
    setLoading(true);
    setError('');
    try {
      // Clean up field boosts to ensure they are numbers
      const cleanedFieldBoosts = Object.fromEntries(
        Object.entries(fieldBoosts)
          .filter(([_, value]) => value !== '' && value !== null && value !== undefined)
          .map(([key, value]) => [key, parseFloat(value)])
      );

      const response = await fetch(`${API_URL}/api/transform-query`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          query,
          field_boosts: cleanedFieldBoosts,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to transform query');
      }

      const data = await response.json();
      setTransformedQuery(data.transformed_query);
    } catch (err) {
      console.error('Error transforming query:', err);
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box sx={{ mt: 2 }}>
      <Button
        variant="outlined"
        onClick={handleTransform}
        disabled={loading || !query}
        sx={{ mb: 2 }}
      >
        {loading ? <CircularProgress size={24} /> : 'Show Transformed Query'}
      </Button>

      {error && (
        <Typography color="error" sx={{ mb: 2 }}>
          {error}
        </Typography>
      )}

      {transformedQuery && (
        <Paper
          elevation={1}
          sx={{
            p: 2,
            backgroundColor: 'grey.50',
            maxHeight: '300px',
            overflow: 'auto',
            '& pre': {
              whiteSpace: 'pre-wrap',
              wordBreak: 'break-word',
              fontFamily: 'monospace',
              fontSize: '0.875rem',
              lineHeight: 1.5,
              margin: 0,
            },
          }}
        >
          <Typography variant="subtitle2" color="text.secondary" gutterBottom>
            Transformed Query:
          </Typography>
          <Typography component="pre" sx={{ m: 0 }}>
            {transformedQuery}
          </Typography>
        </Paper>
      )}
    </Box>
  );
}; 
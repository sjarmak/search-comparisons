import React, { useState } from 'react';
import { Box, Button, Paper, Typography, CircularProgress } from '@mui/material';

interface TransformedQueryProps {
  query: string;
  fieldBoosts: Record<string, number>;
}

export const TransformedQuery: React.FC<TransformedQueryProps> = ({ query, fieldBoosts }) => {
  const [transformedQuery, setTransformedQuery] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string>('');

  const handleTransform = async () => {
    setLoading(true);
    setError('');
    try {
      const response = await fetch('/api/transform-query', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          query,
          field_boosts: fieldBoosts,
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to transform query');
      }

      const data = await response.json();
      setTransformedQuery(data.transformed_query);
    } catch (err) {
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
            wordBreak: 'break-word',
          }}
        >
          <Typography variant="subtitle2" color="text.secondary" gutterBottom>
            Transformed Query:
          </Typography>
          <Typography variant="body2" component="pre" sx={{ m: 0 }}>
            {transformedQuery}
          </Typography>
        </Paper>
      )}
    </Box>
  );
}; 
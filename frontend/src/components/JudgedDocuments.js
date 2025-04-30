import React, { useState, useEffect } from 'react';
import { experimentService } from '../services/api';
import { Card, CardContent, Typography, Box, CircularProgress, Alert } from '@mui/material';
import { styled } from '@mui/material/styles';

const StyledCard = styled(Card)(({ theme }) => ({
  marginBottom: theme.spacing(2),
  '&:hover': {
    boxShadow: theme.shadows[4],
  },
}));

const ScoreBadge = styled(Box)(({ theme, score }) => ({
  display: 'inline-block',
  padding: theme.spacing(0.5, 1),
  borderRadius: theme.shape.borderRadius,
  backgroundColor: score >= 3 ? theme.palette.success.light :
                  score >= 2 ? theme.palette.info.light :
                  score >= 1 ? theme.palette.warning.light :
                  theme.palette.error.light,
  color: theme.palette.getContrastText(
    score >= 3 ? theme.palette.success.light :
    score >= 2 ? theme.palette.info.light :
    score >= 1 ? theme.palette.warning.light :
    theme.palette.error.light
  ),
  fontWeight: 'bold',
}));

const JudgedDocuments = ({ caseId = 8914, queryText = "triton" }) => {
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchDocuments = async () => {
      try {
        setLoading(true);
        setError(null);
        const data = await experimentService.getJudgedDocuments(caseId, queryText);
        setDocuments(data);
      } catch (err) {
        setError(err.message || 'Failed to fetch judged documents');
      } finally {
        setLoading(false);
      }
    };

    fetchDocuments();
  }, [caseId, queryText]);

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" p={3}>
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return (
      <Alert severity="error" sx={{ mb: 2 }}>
        {error}
      </Alert>
    );
  }

  if (documents.length === 0) {
    return (
      <Alert severity="info" sx={{ mb: 2 }}>
        No judged documents found for this query.
      </Alert>
    );
  }

  return (
    <Box>
      {documents.map((doc) => (
        <StyledCard key={doc.id}>
          <CardContent>
            <Box display="flex" justifyContent="space-between" alignItems="flex-start" mb={1}>
              <Typography variant="h6" component="h2" gutterBottom>
                {doc.title}
              </Typography>
              <ScoreBadge score={doc.score}>
                Score: {doc.score}
              </ScoreBadge>
            </Box>
            {doc.metadata && (
              <Box mt={1}>
                {Object.entries(doc.metadata).map(([key, value]) => (
                  <Typography key={key} variant="body2" color="text.secondary">
                    <strong>{key}:</strong> {value}
                  </Typography>
                ))}
              </Box>
            )}
          </CardContent>
        </StyledCard>
      ))}
    </Box>
  );
};

export default JudgedDocuments; 
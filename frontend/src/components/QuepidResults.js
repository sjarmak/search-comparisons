import React, { useState, useEffect } from 'react';
import { Paper, Typography, Grid, Card, CardContent, Box, CircularProgress, Alert } from '@mui/material';
import { styled } from '@mui/material/styles';

const StyledCard = styled(Card)(({ theme }) => ({
  height: '100%',
  display: 'flex',
  flexDirection: 'column',
  transition: 'transform 0.2s',
  '&:hover': {
    transform: 'translateY(-4px)',
    boxShadow: theme.shadows[4],
  },
}));

const JudgmentBadge = styled(Box)(({ theme, judgment }) => ({
  display: 'inline-block',
  padding: theme.spacing(0.5, 1),
  borderRadius: theme.shape.borderRadius,
  backgroundColor: judgment === 3 ? theme.palette.success.light :
                  judgment === 2 ? theme.palette.info.light :
                  judgment === 1 ? theme.palette.warning.light :
                  theme.palette.error.light,
  color: theme.palette.getContrastText(
    judgment === 3 ? theme.palette.success.light :
    judgment === 2 ? theme.palette.info.light :
    judgment === 1 ? theme.palette.warning.light :
    theme.palette.error.light
  ),
  fontWeight: 'bold',
  marginBottom: theme.spacing(1),
}));

const QuepidResults = () => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [judgedDocuments, setJudgedDocuments] = useState([]);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        // Fetch judged documents from Quepid
        const response = await fetch('/api/quepid/documents');
        if (!response.ok) {
          throw new Error('Failed to fetch Quepid documents');
        }
        const data = await response.json();
        setJudgedDocuments(data);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="200px">
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return (
      <Alert severity="error" sx={{ mt: 2 }}>
        Error: {error}
      </Alert>
    );
  }

  return (
    <Paper sx={{ p: 3 }}>
      <Typography variant="h5" gutterBottom>
        Quepid Results
      </Typography>
      
      <Grid container spacing={3}>
        <Grid item xs={12}>
          <Typography variant="h6" gutterBottom>
            Judged Documents ({judgedDocuments.length})
          </Typography>
          {judgedDocuments.length > 0 ? (
            judgedDocuments.map((doc) => (
              <StyledCard key={doc.id} sx={{ mb: 2 }}>
                <CardContent>
                  <JudgmentBadge judgment={doc.judgment}>
                    Judgment: {doc.judgment}
                  </JudgmentBadge>
                  <Typography variant="h6" component="div">
                    {doc.title}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    ID: {doc.id}
                  </Typography>
                  {doc.score && (
                    <Typography variant="body2" color="text.secondary">
                      Score: {doc.score}
                    </Typography>
                  )}
                </CardContent>
              </StyledCard>
            ))
          ) : (
            <Typography>No judged documents available</Typography>
          )}
        </Grid>
      </Grid>
    </Paper>
  );
};

export default QuepidResults; 
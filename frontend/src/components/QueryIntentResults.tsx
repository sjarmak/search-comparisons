import React from 'react';
import { Paper, Typography, Box, Chip, Link } from '@mui/material';
import { styled } from '@mui/material/styles';

interface Author {
  name: string;
  affiliation?: string;
}

interface SearchResult {
  id: string;
  title: string;
  author: string[];
  abstract: string;
  year: string;
  citation_count: number;
  doi: string;
  url: string;
}

interface QueryIntentResultsProps {
  originalQuery: string;
  transformedQuery: string;
  intent: string;
  intentConfidence: number;
  explanation: string;
  searchResults: {
    num_found: number;
    results: SearchResult[];
  };
}

const ResultPaper = styled(Paper)(({ theme }) => ({
  padding: theme.spacing(2),
  marginBottom: theme.spacing(2),
  backgroundColor: theme.palette.background.paper,
}));

const AuthorChip = styled(Chip)(({ theme }) => ({
  marginRight: theme.spacing(0.5),
  marginBottom: theme.spacing(0.5),
}));

const QueryIntentResults: React.FC<QueryIntentResultsProps> = ({
  originalQuery,
  transformedQuery,
  intent,
  intentConfidence,
  explanation,
  searchResults,
}) => {
  return (
    <Box sx={{ mt: 4 }}>
      <Typography variant="h5" gutterBottom>
        Query Transformation Results
      </Typography>
      
      <ResultPaper elevation={1}>
        <Typography variant="subtitle1" color="text.secondary">
          Original Query
        </Typography>
        <Typography variant="body1" gutterBottom>
          {originalQuery}
        </Typography>
        
        <Typography variant="subtitle1" color="text.secondary" sx={{ mt: 2 }}>
          Transformed Query
        </Typography>
        <Typography variant="body1" gutterBottom>
          {transformedQuery}
        </Typography>
        
        <Box sx={{ display: 'flex', alignItems: 'center', mt: 2 }}>
          <Typography variant="subtitle1" color="text.secondary">
            Detected Intent:
          </Typography>
          <Chip
            label={intent}
            color="primary"
            size="small"
            sx={{ ml: 1 }}
          />
          <Typography variant="body2" color="text.secondary" sx={{ ml: 1 }}>
            (Confidence: {(intentConfidence * 100).toFixed(1)}%)
          </Typography>
        </Box>
        
        <Typography variant="subtitle1" color="text.secondary" sx={{ mt: 2 }}>
          Explanation
        </Typography>
        <Typography variant="body1">
          {explanation}
        </Typography>
      </ResultPaper>
      
      <Typography variant="h6" sx={{ mt: 3, mb: 2 }}>
        Search Results ({searchResults.num_found} found)
      </Typography>
      
      {searchResults.results.map((result) => (
        <ResultPaper key={result.id} elevation={1}>
          <Typography variant="h6" component="div">
            <Link href={result.url} target="_blank" rel="noopener noreferrer">
              {result.title}
            </Link>
          </Typography>
          
          <Box sx={{ my: 1 }}>
            {result.author.map((author, index) => (
              <AuthorChip
                key={index}
                label={author}
                size="small"
                variant="outlined"
              />
            ))}
          </Box>
          
          <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
            <Typography variant="body2" color="text.secondary">
              {result.year}
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mx: 1 }}>
              •
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Citations: {result.citation_count}
            </Typography>
            {result.doi && (
              <>
                <Typography variant="body2" color="text.secondary" sx={{ mx: 1 }}>
                  •
                </Typography>
                <Link
                  href={`https://doi.org/${result.doi}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  variant="body2"
                >
                  DOI
                </Link>
              </>
            )}
          </Box>
          
          <Typography variant="body1" sx={{ mt: 1 }}>
            {result.abstract}
          </Typography>
        </ResultPaper>
      ))}
    </Box>
  );
};

export default QueryIntentResults; 
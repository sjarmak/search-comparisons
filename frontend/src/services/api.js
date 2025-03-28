/**
 * API service for search-comparisons application.
 * 
 * Provides methods for interacting with the backend API.
 */
import axios from 'axios';

// Base API URL from environment or fallback to localhost
const API_URL = process.env.REACT_APP_API_URL || process.env.VITE_API_URL || "http://localhost:8000";
const DEBUG = process.env.REACT_APP_DEBUG === 'true';

// Create axios instance with consistent configuration
const apiClient = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
    'Accept': 'application/json'
  },
  timeout: 60000 // 1 minute timeout
});

// Log requests and responses in debug mode
if (DEBUG) {
  apiClient.interceptors.request.use(request => {
    console.log('API Request:', request);
    return request;
  });
  
  apiClient.interceptors.response.use(
    response => {
      console.log('API Response:', response);
      return response;
    },
    error => {
      console.error('API Error:', error);
      return Promise.reject(error);
    }
  );
}

/**
 * Standard error handler for API calls
 */
const handleApiError = (error) => {
  let errorMessage = 'An unknown error occurred';
  
  if (error.response) {
    // The request was made and the server responded with an error status
    const status = error.response.status;
    const data = error.response.data;
    
    if (data && data.detail) {
      errorMessage = data.detail;
    } else if (data && data.message) {
      errorMessage = data.message;
    } else {
      errorMessage = `Server error: ${status}`;
    }
  } else if (error.request) {
    // The request was made but no response was received
    errorMessage = 'No response received from server. Please check your connection.';
  } else {
    // Something happened in setting up the request
    errorMessage = error.message || errorMessage;
  }
  
  return {
    error: true,
    message: errorMessage
  };
};

/**
 * Search API services
 */
const searchService = {
  /**
   * Compare search results across multiple sources
   */
  compareSearchResults: async (searchParams) => {
    try {
      const response = await apiClient.post('/api/search/compare', searchParams);
      return response.data;
    } catch (error) {
      return handleApiError(error);
    }
  },
  
  /**
   * Get search results from a specific source
   */
  searchBySource: async (source, query, options = {}) => {
    try {
      const response = await apiClient.post(`/api/search/${source}`, { 
        query,
        ...options
      });
      return response.data;
    } catch (error) {
      return handleApiError(error);
    }
  },
  
  /**
   * Get paper details by DOI
   */
  getPaperDetails: async (doi, sources = []) => {
    try {
      const params = sources.length > 0 ? { sources: sources.join(',') } : {};
      const response = await apiClient.get(`/api/paper/${doi}`, { params });
      return response.data;
    } catch (error) {
      return handleApiError(error);
    }
  }
};

/**
 * Experiment API services
 */
const experimentService = {
  /**
   * Run result boosting experiment
   */
  runBoostExperiment: async (boostConfig) => {
    try {
      const response = await apiClient.post('/api/experiments/boost', boostConfig);
      return response.data;
    } catch (error) {
      return handleApiError(error);
    }
  },
  
  /**
   * Apply boosts to search results - uses the legacy endpoint for compatibility
   */
  applyBoosts: async (query, results, boostConfig) => {
    try {
      console.log("Using legacy /api/boost-experiment endpoint with boostConfig:", boostConfig);
      const response = await apiClient.post('/api/boost-experiment', {
        query,
        results,
        boostConfig
      });
      
      return {
        results: {
          origin: response.data.results
        }
      };
    } catch (error) {
      return handleApiError(error);
    }
  },
  
  /**
   * Run A/B testing experiment
   */
  runAbTest: async (searchRequest, variation = 'B') => {
    try {
      const response = await apiClient.post(`/api/experiments/ab-test?variation=${variation}`, searchRequest);
      return response.data;
    } catch (error) {
      return handleApiError(error);
    }
  },
  
  /**
   * Get log analysis metrics
   */
  getLogAnalysis: async () => {
    try {
      const response = await apiClient.get('/api/experiments/log-analysis');
      return response.data;
    } catch (error) {
      return handleApiError(error);
    }
  },
  
  /**
   * Evaluate search results against Quepid judgments
   */
  evaluateWithQuepid: async (evaluationRequest) => {
    try {
      const response = await apiClient.post('/api/experiments/quepid-evaluation', evaluationRequest);
      return response.data;
    } catch (error) {
      return handleApiError(error);
    }
  },
  
  /**
   * Get available Quepid cases
   */
  getQuepidCases: async () => {
    try {
      const response = await apiClient.get('/api/experiments/quepid-cases');
      return response.data;
    } catch (error) {
      return handleApiError(error);
    }
  }
};

/**
 * Debug API services
 */
const debugService = {
  /**
   * List available sources and their configuration
   */
  listSources: async () => {
    try {
      const response = await apiClient.get('/api/debug/sources');
      return response.data;
    } catch (error) {
      return handleApiError(error);
    }
  },
  
  /**
   * Get environment information
   */
  getEnvironmentInfo: async () => {
    try {
      const response = await apiClient.get('/api/debug/env');
      return response.data;
    } catch (error) {
      return handleApiError(error);
    }
  },
  
  /**
   * Ping a specific source
   */
  pingSource: async (source) => {
    try {
      const response = await apiClient.get(`/api/debug/ping/${source}`);
      return response.data;
    } catch (error) {
      return handleApiError(error);
    }
  },
  
  /**
   * Test search on a specific source
   */
  testSearch: async (source, query, limit = 5) => {
    try {
      const response = await apiClient.get(`/api/debug/search/${source}?query=${encodeURIComponent(query)}&limit=${limit}`);
      return response.data;
    } catch (error) {
      return handleApiError(error);
    }
  }
};

// Export all services
export {
  searchService,
  experimentService,
  debugService,
  API_URL
}; 
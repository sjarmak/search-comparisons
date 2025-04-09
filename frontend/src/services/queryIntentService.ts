import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

/**
 * Transform a search query using the query intent service.
 * 
 * @param query - The original search query
 * @returns Promise containing the transformation results
 */
export const transformQuery = async (query: string): Promise<any> => {
  try {
    const response = await axios.post(`${API_BASE_URL}/api/intent-transform-query`, {
      query
    });
    return response.data;
  } catch (error) {
    if (axios.isAxiosError(error)) {
      throw new Error(error.response?.data?.detail || 'Failed to transform query');
    }
    throw error;
  }
}; 
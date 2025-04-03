# Academic Search Engine Comparisons

A web application for comparing search results across multiple academic search engines, including ADS/SciX, Google Scholar, Semantic Scholar, and Web of Science.

## Features

- Compare search results from multiple academic search engines
- Analyze similarity and differences between result sets
- Experiment with boosting factors to improve search rankings
- Perform A/B testing of different search algorithms
- Debug tools for API testing and diagnostics
- Direct Solr proxy for ADS/SciX queries (no API key required)

## New Features

### Quepid Integration

The application now includes integration with [Quepid](https://quepid.com/), a search relevance testing platform. This integration allows you to:

1. Connect to your Quepid cases containing relevance judgments
2. Evaluate search results using industry-standard metrics like nDCG@10
3. Compare performance across different search engines
4. Test how changes to search algorithms affect relevance scores

#### Configuration

To use the Quepid integration, you'll need to set the following environment variables:

```
QUEPID_API_URL=https://app.quepid.com/api/
QUEPID_API_KEY=your_api_key_here
```

#### API Endpoints

The following endpoint has been added:

- `POST /experiments/quepid-evaluation`: Evaluate search results against Quepid judgments

Example request:

```json
{
  "query": "katabatic wind",
  "sources": ["ads", "scholar", "semantic_scholar"],
  "case_id": 123,
  "max_results": 20
}
```

Example response:

```json
{
  "query": "katabatic wind",
  "case_id": 123,
  "case_name": "Atmospheric Sciences",
  "source_results": [
    {
      "source": "ads",
      "metrics": [
        {
          "name": "ndcg@10",
          "value": 0.85,
          "description": "Normalized Discounted Cumulative Gain at 10"
        },
        {
          "name": "p@10",
          "value": 0.7,
          "description": "Precision at 10"
        }
      ],
      "judged_retrieved": 15,
      "relevant_retrieved": 12,
      "results_count": 20
    }
  ],
  "total_judged": 25,
  "total_relevant": 18
}
```

## New: LLM-Based Query Intent Service

The repository now includes a new feature that uses lightweight open-source LLMs to interpret user search queries, detect intent, and transform queries to be more effective. This feature is accessible through the "Query Intent" tab in the UI.

### Key Features

- Query analysis using local LLM models via Ollama
- Automatic query transformation based on detected intent
- Support for multiple lightweight models (Llama 2, Mistral, Gemma)
- Rule-based fallbacks when intent is clear
- Docker Compose setup for easy deployment

To use this feature:

1. Set up the backend service following instructions in `backend/README.md`
2. Use the "Query Intent" tab in the UI for semantic query transformation

For details, see the [backend documentation](./backend/README.md).

## Project Structure

The project is structured as follows:

- `backend/`: FastAPI backend with search services
  - `app/`: Application code
    - `api/`: API routes and models
    - `core/`: Core configuration and utilities
    - `services/`: Search engine integration services
    - `utils/`: Utility functions
  - `tests/`: Backend tests

- `frontend/`: React frontend application
  - `public/`: Static files
  - `src/`: React source code
    - `components/`: React components
    - `services/`: API service functions

## Prerequisites

- Python 3.9+
- Node.js 14+
- API keys for academic search engines (optional)

## Setup

### Backend Setup

1. Navigate to the backend directory:
   ```
   cd backend
   ```

2. Create and activate a virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Create a `.env.local` file in the project root with your API keys:
   ```
   ADS_API_TOKEN=your_ads_token
   SEMANTIC_SCHOLAR_API_KEY=your_ss_key
   WEB_OF_SCIENCE_API_KEY=your_wos_key
   ```

### ADS/SciX Solr Proxy Configuration

The application supports querying ADS/SciX directly through a Solr proxy, which offers faster results and doesn't require an API key. Configure this in your environment file:

```
# Solr proxy URL (default: https://scix-solr-proxy.onrender.com/solr/select)
ADS_SOLR_PROXY_URL=https://scix-solr-proxy.onrender.com/solr/select

# Query method (options: solr_only, api_only, solr_first)
# - solr_only: Only use Solr proxy
# - api_only: Only use ADS API
# - solr_first: Try Solr first, fall back to API if needed (default)
ADS_QUERY_METHOD=solr_first
```

### Frontend Setup

1. Navigate to the frontend directory:
   ```
   cd frontend
   ```

2. Install dependencies:
   ```
   npm install
   ```

## Development

### Running Locally

1. Start both frontend and backend servers:
   ```
   ./start_local.sh
   ```

   Or run them separately:

   - Backend:
     ```
     cd backend
     python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
     ```

   - Frontend:
     ```
     cd frontend
     npm start
     ```

2. Open your browser and navigate to http://localhost:3000

### Testing

- Run backend tests:
  ```
  cd backend
  pytest
  ```

## Deployment

This application is configured for deployment on Render.com using the `render.yaml` configuration file.

### Environment Configuration

The application supports different environments:

- `local`: For local development
- `development`: For development deployment
- `staging`: For staging deployment
- `production`: For production deployment

Environment-specific configuration is loaded from:

- `.env.local`
- `.env.dev`
- `.env.staging`
- `.env.prod`

## API Documentation

When running locally, the API documentation is available at:

- Swagger UI: http://localhost:8000/api/docs
- ReDoc: http://localhost:8000/api/redoc

## License

[MIT License](LICENSE)
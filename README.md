# Academic Search Engine Comparisons

A web application for comparing search results across multiple academic search engines, including ADS/SciX, Google Scholar, Semantic Scholar, and Web of Science.

## Features

- Compare search results from multiple academic search engines
- Analyze similarity and differences between result sets
- Experiment with boosting factors to improve search rankings
- Perform A/B testing of different search algorithms
- Debug tools for API testing and diagnostics

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
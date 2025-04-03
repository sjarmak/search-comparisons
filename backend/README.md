# ADS Query Intent Service

A lightweight service for interpreting astronomy search queries, detecting user intent, and transforming queries to be more effective with the NASA Astrophysics Data System (ADS).

## Features

- **Query Intent Detection**: Uses a lightweight open-source LLM to identify the user's search intent
- **Query Transformation**: Enhances queries with appropriate ADS search syntax based on intent
- **Multiple LLM Options**: Supports multiple lightweight LLMs via Ollama, including:
  - Llama 2 (7B)
  - Mistral 7B Instruct
  - Gemma 2B Instruct
- **Rule-based Fallback**: Includes rule-based transformations when intent is clear
- **Query Analysis**: Provides complexity analysis and improvement suggestions for queries
- **API Documentation**: Automatic OpenAPI documentation via FastAPI

## Requirements

- Python 3.9+
- Docker and Docker Compose (for containerized deployment)
- Ollama (for running local LLMs)
- ~8GB RAM for smaller models (Gemma 2B)
- ~16GB RAM for larger models (Llama 2 7B or Mistral 7B)
- GPU recommended but not required

## Setup

### Local Development

1. Clone the repository:
   ```bash
   git clone https://github.com/adsabs/query-intent-service.git
   cd query-intent-service
   ```

2. Create a virtual environment and install dependencies:
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. Install Ollama following instructions at [https://ollama.ai/download](https://ollama.ai/download)

4. Pull the LLM model:
   ```bash
   ollama pull mistral:7b-instruct-v0.2  # or llama2:7b-chat or gemma:2b-instruct
   ```

5. Start Ollama:
   ```bash
   ollama serve
   ```

6. Run the FastAPI service:
   ```bash
   cd backend
   uvicorn app.main:app --reload
   ```

7. Access the API at http://localhost:8000 and documentation at http://localhost:8000/docs

### Docker Deployment

1. Start all services using Docker Compose:
   ```bash
   docker-compose up -d
   ```

2. Access the API at http://localhost:8000 and documentation at http://localhost:8000/docs

3. Pull the required model in the Ollama container:
   ```bash
   docker exec -it query-intent-service-ollama-1 ollama pull mistral:7b-instruct-v0.2
   ```

## API Usage

### Transform a Query

```bash
curl -X GET "http://localhost:8000/api/query-intent/transform?query=recent%20papers%20on%20exoplanets" | jq
```

Example response:
```json
{
  "original_query": "recent papers on exoplanets",
  "intent": "recent",
  "intent_confidence": 0.9,
  "transformed_query": "exoplanets year:2023-2024",
  "explanation": "Added year:2023-2024 to find recent papers on this topic."
}
```

### Analyze Query Complexity

```bash
curl -X GET "http://localhost:8000/api/query-intent/analyze?query=author%3A%22Kurtz%2C%20M%22%20AND%20year%3A2020-2022" | jq
```

### Get Query Improvement Suggestions

```bash
curl -X GET "http://localhost:8000/api/query-intent/suggest?query=black%20holes" | jq
```

## Integration with Frontend

To integrate with the Query Intent tab in the search-comparisons frontend:

1. Update the frontend's `env.local` or environment variables to point to the API:
   ```
   REACT_APP_QUERY_INTENT_API=http://localhost:8000
   ```

2. The frontend will automatically use the `/api/query-intent/transform` endpoint when searching.

## Configuration

The service can be configured using environment variables:

- `LLM_MODEL`: Model name (default: "llama2-chat")
- `LLM_TEMPERATURE`: Sampling temperature 0.0-1.0 (default: 0.1)
- `LLM_MAX_TOKENS`: Maximum tokens to generate (default: 1024)
- `LLM_PROVIDER`: Provider type (default: "ollama")
- `LLM_API_ENDPOINT`: API endpoint URL (default: "http://localhost:11434/api/generate")

## Running Tests

```bash
cd backend
pytest
```

## License

This project is licensed under the MIT License - see the LICENSE file for details. 
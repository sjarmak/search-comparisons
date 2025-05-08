# Search Comparisons Tool

A powerful search comparison tool that aggregates and analyzes results from multiple academic search engines, with advanced query understanding and result comparison capabilities.

## Project Overview

This tool provides a unified interface for searching across multiple academic search engines, including:
- NASA Astrophysics Data System (ADS)
- Google Scholar
- Semantic Scholar
- Web of Science

It features intelligent query understanding, result comparison, and caching mechanisms to provide efficient and relevant search results.

## Architecture

### Core Components

#### 1. Search Service (`backend/app/services/search_service.py`)
- Coordinates search operations across different search engines
- Handles fallback mechanisms when primary search methods fail
- Computes similarity metrics between results from different sources
- Provides paper detail retrieval across multiple sources

#### 2. Query Intent Service (`backend/app/services/query_intent/`)
- Interprets and transforms user queries using LLM-based intent detection
- Components:
  - `service.py`: Main query intent service implementation
  - `llm_service.py`: Handles LLM interactions for query understanding
  - `cache_service.py`: Caches query transformations and results
  - `documentation_service.py`: Provides documentation for query transformations

#### 3. LLM Service (`backend/app/services/llm/`)
- Manages interactions with lightweight open-source LLMs
- Supports multiple providers (Ollama, HuggingFace, OpenAI)
- Handles prompt formatting and response processing
- Implements query transformation logic

#### 4. Individual Search Engine Services

##### ADS Service (`backend/app/services/ads_service.py`)
- Handles interactions with NASA's Astrophysics Data System
- Manages API authentication and request formatting
- Processes ADS-specific search results

##### Scholar Service (`backend/app/services/scholar_service.py`)
- Interfaces with Google Scholar
- Implements fallback mechanisms using Scholarly or direct HTML scraping
- Handles proxy management for rate limiting

##### Semantic Scholar Service (`backend/app/services/semantic_scholar_service.py`)
- Manages interactions with Semantic Scholar API
- Processes academic paper metadata and citations

##### Web of Science Service (`backend/app/services/web_of_science_service.py`)
- Interfaces with Web of Science API
- Handles authentication and result processing

#### 5. Cache Service (`backend/app/services/cache_service.py`)
- Implements LRU (Least Recently Used) caching with TTL support
- Caches query transformations and search results
- Improves performance and reduces redundant processing

#### 6. Boost Service (`backend/app/services/boost_service.py`)
- Applies various boost factors to search results
- Considers citation count, publication recency, and document type
- Enhances result relevance and ranking

#### 7. Quepid Service (`backend/app/services/quepid_service.py`)
- Integrates with Quepid API for search evaluation
- Manages cases, judgments, and result evaluation
- Provides search quality metrics

### Project Structure

```
backend/
├── app/
│   ├── api/            # API models and endpoints
│   ├── core/           # Core configuration and settings
│   ├── routes/         # API route definitions
│   ├── services/       # Service implementations
│   │   ├── llm/        # LLM-related services
│   │   └── query_intent/ # Query intent services
│   └── utils/          # Utility functions
├── tests/              # Test suite
└── scripts/            # Utility scripts
```

## Features

1. **Unified Search Interface**
   - Single interface for multiple academic search engines
   - Consistent result formatting across sources
   - Fallback mechanisms for reliability

2. **Intelligent Query Understanding**
   - LLM-based query intent detection
   - Query transformation for improved results
   - Support for astronomy-specific terminology

3. **Result Comparison**
   - Similarity metrics between results
   - Citation count analysis
   - Publication date comparison
   - Document type analysis

4. **Performance Optimization**
   - LRU caching with TTL
   - Query transformation caching
   - Result caching
   - Proxy management for rate limiting

5. **Search Quality Evaluation**
   - Integration with Quepid for search evaluation
   - Result ranking analysis
   - Quality metrics computation

## Configuration

The application uses environment variables for configuration. Key settings include:

- `ADS_API_KEY`: NASA ADS API key
- `LLM_PROVIDER`: LLM service provider (ollama, huggingface, openai)
- `LLM_MODEL_NAME`: Model name for the LLM service
- `LLM_TEMPERATURE`: Temperature setting for LLM generation
- `LLM_MAX_TOKENS`: Maximum tokens for LLM generation
- `CACHE_TTL`: Cache time-to-live in seconds
- `CACHE_MAX_SIZE`: Maximum cache size

## Development

### Prerequisites

- Python 3.8+
- Docker and Docker Compose
- API keys for required services

### Setup

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Set up environment variables
4. Run the application:
   ```bash
   ./start_local.sh
   ```

### Testing

Run tests using pytest:
```bash
pytest backend/tests/
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.
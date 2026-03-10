# Multi-Tool Research Agent

An intelligent research agent capable of accessing multiple tools including web search, APIs, databases, and knowledge bases. Orchestrates complex multi-step research workflows with self-reasoning and iterative refinement capabilities.

## Features

- **Multi-Tool Integration**: Access web search, academic databases, code repositories
- **Caching System**: Cache research results for performance optimization
- **Search History**: Track all research queries and results
- **Async Processing**: High-performance async/await architecture
- **Real-time Updates**: WebSocket support for live updates
- **Error Handling**: Robust retry mechanisms with exponential backoff
- **Structured Logging**: Comprehensive JSON logging for debugging
- **RESTful API**: FastAPI-based REST endpoints
- **Docker Support**: Production-ready containerization

## Installation

### Local Setup

```bash
git clone https://github.com/Neuro-kiran/multi-tool-research-agent.git
cd multi-tool-research-agent
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Docker

```bash
docker build -t multi-tool-research-agent:latest .
docker run -p 8000:8000 -e GOOGLE_API_KEY=your_key -e SERPER_API_KEY=your_key multi-tool-research-agent:latest
```

## Configuration

Environment variables:

```env
GOOGLE_API_KEY=your_google_api_key
SERPER_API_KEY=your_serper_api_key
ARXIV_API_KEY=your_arxiv_api_key
HOST=0.0.0.0
PORT=8000
LOG_LEVEL=INFO
```

## API Endpoints

### Health Check
```http
GET /health
```

### Perform Research
```http
POST /research
Content-Type: application/json

{
  "query": "machine learning frameworks",
  "tools": ["web_search", "code_search", "academic"],
  "depth": 2,
  "max_results": 20
}
```

### Get Search History
```http
GET /history
```

### WebSocket
```
WS /ws
```

## Research Tools

- **web_search**: Search the web using Serper API
- **academic**: Search academic papers using arXiv API
- **code_search**: Search code repositories using GitHub API
- **database**: Query structured databases
- **api_aggregation**: Aggregate results from multiple APIs

## Usage Example

```python
import asyncio
import aiohttp

async def main():
    async with aiohttp.ClientSession() as session:
        payload = {
            "query": "generative AI trends",
            "tools": ["web_search", "academic"],
            "depth": 2,
            "max_results": 15
        }
        async with session.post('http://localhost:8000/research', json=payload) as resp:
            results = await resp.json()
            print(results)

asyncio.run(main())
```

## Architecture

- **FastAPI**: Web framework for building APIs
- **Uvicorn**: ASGI server for async HTTP
- **aiohttp**: Async HTTP client for external APIs
- **Tenacity**: Retry logic with exponential backoff
- **Structlog**: Structured logging
- **Pydantic**: Data validation and settings management

## Performance Optimization

- Result caching to avoid duplicate requests
- Async/await for non-blocking I/O
- Connection pooling for API clients
- Batch processing capabilities
- Multi-worker Uvicorn setup

## Error Handling

- Automatic retry with exponential backoff
- Graceful error responses
- Comprehensive logging
- Connection timeout handling
- API rate limit management

## Development

```bash
# Run with reload
uvicorn main:app --reload

# Run tests
pytest tests/

# Format code
black .
flake8 .
```

## License

MIT License

## Author

Kiran Marne (Neuro-kiran)

## Support

For issues and support:
- GitHub Issues: https://github.com/Neuro-kiran/multi-tool-research-agent/issues
- Email: marne.kiran44@gmail.com

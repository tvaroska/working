# Technical Context

## Core Technologies

### Programming Language
- **Python 3.12**: The project is built using Python 3.12, leveraging modern language features and optimizations.

### Key Libraries & Frameworks
- **Flet**: A Flutter-based framework for building interactive web UIs with Python
- **asyncio**: For asynchronous I/O operations and concurrent processing
- **feedparser**: To parse and extract content from RSS feeds
- **httpx**: Modern asynchronous HTTP client for Python
- **Google Vertex AI**: Cloud-based AI platform for generative text processing (using Gemini models)
- **Pydantic**: For data validation and settings management
- **structlog**: Structured logging for better observability
- **tenacity**: Retry library for handling transient failures
- **argparse**: Command-line argument parsing for flexible configuration

### Storage & Data Format
- **JSON**: Used for both configuration (`settings.json`) and data storage (`articles.json` and `latest.json`)
- **Markdown**: Used for formatting long-form article summaries in the UI

### Deployment & Containerization
- **Docker**: For containerized deployment and consistent runtime environments using multi-stage builds
- **UV**: Modern Python package manager for dependency management (used in the Docker build process)

## Development Setup

### Requirements
- Python 3.12+
- Docker for containerization
- Google Cloud project with Vertex AI API enabled
- API credentials for Google Vertex AI

### Local Development
The project can be run locally with:
```bash
# Install dependencies
uv sync --frozen

# Run the content processor
python process.py

# Run the web application
python app.py
```

### Command-line Options
The process.py script supports several command-line options:
- `--model`: Specify the Gemini model to use (default: gemini-2.0-flash-001)
- `--input`: Specify the input settings file (default: settings.json)
- `--output`: Specify the output file for processed articles (default: articles.json)

### Environment Variables
- `DATAFILE`: Optional override for the data file path (default: `articles.json`)
- `VERTEX_AI_LOCATION`: Location for the Vertex AI API (default: us-central1)

### Configuration Files
- `settings.json`: Contains RSS feed URLs and other configuration parameters
- `pyproject.toml`: Project metadata and dependencies
- `uv.lock`: Dependency lock file for reproducible builds

## Technical Constraints

### API Limitations
- **Google Vertex AI Quotas**: Limited by API rate limits and quotas
- **Cost Considerations**: Pay-per-use model for AI API calls
- **Rate Limiting**: Implemented via semaphores (currently set to 10 concurrent requests)

### Performance Considerations
- **Memory Usage**: Flet applications may have higher memory usage than traditional web servers
- **Network Dependency**: Relies on stable network connections for feed fetching and API calls
- **Rate Limiting**: Must implement rate limiting to avoid API throttling
- **Processing Time**: Initial content collection and processing can be time-intensive

### Security Aspects
- **API Credentials**: Requires secure handling of API keys
- **Content Security**: No user-generated content, reducing security risks
- **Data Privacy**: No user data collection or storage

## Dependencies

### Core Dependencies
```
flet>=0.17.0
feedparser>=6.0.0
httpx>=0.25.0
google-generativeai>=0.3.0
pydantic>=2.5.0
structlog>=24.1.0
tenacity>=8.2.0
```

### Development Dependencies
```
black
pytest
pytest-asyncio
pytest-cov
mypy
```

## Build & Deployment Process

### Docker Build Process
1. Uses multi-stage build for smaller final image
2. First stage installs dependencies and syncs with UV
3. Second stage copies application code and dependencies
4. Final image exposes port 8000 and runs the application

### Deployment Options
- **Container Orchestration**: Kubernetes or Docker Swarm
- **Cloud Platforms**: Google Cloud Run, AWS Fargate, or Azure Container Instances
- **Static Hosting**: Since Flet can export to static assets, can be deployed to static hosting platforms

## Testing Strategy
- **Unit Tests**: For individual components and functions
- **Integration Tests**: For testing the entire pipeline
- **End-to-End Tests**: For validating the web interface

## Monitoring & Logging
- Uses `structlog` for structured logging with contextual information
- Configurable log levels and processors
- Contextual binding for better traceability across components
- Exception handling with proper logging

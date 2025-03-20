# System Patterns

## System Architecture

The system follows a data pipeline architecture with three main components:

```mermaid
flowchart TD
    A[Article Collection] --> B[Processing & Summarization]
    B --> C[Web Presentation]
    
    subgraph A[Article Collection]
        A1[RSS Feed Fetching]
        A2[Article Extraction]
        A3[Deduplication]
    end
    
    subgraph B[Processing & Summarization]
        B1[Content Preparation]
        B2[Google Vertex AI API]
        B3[Summary Storage]
    end
    
    subgraph C[Web Presentation]
        C1[Flet Web App]
        C2[List View]
        C3[Detail View]
    end
```

## Key Technical Decisions

### 1. Data Collection & Processing
- **RSS Feed Integration**: Uses `feedparser` to collect articles from specified RSS feeds
- **Asynchronous Processing**: Leverages `asyncio` for efficient concurrent processing of multiple feeds
- **HTTP Client**: Uses `httpx` for asynchronous HTTP requests to fetch article content
- **Error Handling**: Implements robust error handling with `tenacity` for retries on failures
- **Caching**: Avoids duplicate processing by tracking previously processed articles

### 2. AI Processing
- **Google Vertex AI**: Leverages Google's Generative AI models for content summarization
- **Batched Processing**: Processes articles in batches with rate limiting to manage API costs
- **Schema Validation**: Uses `pydantic` models to enforce structured summary formats
- **Retry Logic**: Implements exponential backoff for API calls to handle service limitations

### 3. Web Interface
- **Flet Framework**: Uses Flet (Flutter-based Python framework) for the web UI
- **Responsive Design**: Implements adaptive layouts for different screen sizes
- **Client-Side Routing**: Enables navigation between list and detail views without page reload
- **Material Design**: Follows Material Design principles for consistent user experience

## Component Relationships

### Article Processing Pipeline
1. **Collection Stage**:
   - Reads feed URLs from `settings.json`
   - Parses each feed to extract articles
   - Filters articles based on publication date

2. **Processing Stage**:
   - Prepares content for AI processing
   - Sends to Google Vertex AI for summarization
   - Generates both short and long-form summaries

3. **Storage Stage**:
   - Stores processed articles in `articles.json`
   - Includes metadata, summaries, and URLs

### Web Application Flow
1. **Initialization**:
   - Loads article data from JSON file
   - Sets up UI components and routes

2. **List View**:
   - Displays article cards with title and short summary
   - Implements click handlers for navigation

3. **Detail View**:
   - Shows article title, long summary, and source link
   - Provides back navigation to list view

## Design Patterns

- **Async/Await Pattern**: For concurrent network operations
- **Retry Pattern**: For handling transient failures in API calls
- **Repository Pattern**: For data access abstraction
- **MVC Pattern**: Separation of data, presentation, and control logic
- **Factory Pattern**: For creating different types of views and components

## Error Handling Strategy

- **Network Failures**: Retry with exponential backoff
- **API Limits**: Rate limiting and graceful degradation
- **Parsing Errors**: Robust error handling with fallbacks
- **UI Exceptions**: Graceful error state displays

## Deployment Strategy

- **Containerization**: Docker-based deployment for consistency
- **Configuration Management**: External configuration files
- **Environment Variables**: For sensitive API credentials
- **Lightweight Runtime**: Minimalist Python container for production

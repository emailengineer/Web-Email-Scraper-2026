# Website Scraper - Production-Grade Email Extraction

A high-performance, production-ready website scraper that extracts email addresses from websites by intelligently visiting common contact pages and validating emails through DNS MX record checks.

## 🚀 Features

- **Intelligent Scraping**: Automatically visits root domain and common contact pages
- **Multiple Email Extraction Methods**: Uses regex, HTML parsing, JavaScript rendering, and obfuscation detection
- **DNS Validation**: Validates all found emails by checking MX records
- **Smart Caching**: Caches MX records to avoid redundant DNS queries
- **Early Termination**: Stops as soon as a valid email is found
- **High Performance**: Async/await architecture with concurrent scraping
- **Production Ready**: Dockerized with health checks, logging, and monitoring
- **RESTful API**: Clean FastAPI-based API with automatic documentation

## 📋 Requirements

- Docker & Docker Compose
- Python 3.11+ (for local development)
- 2GB+ RAM recommended
- Internet connection for DNS queries

## 🛠️ Quick Start

### One-Click Deployment

```bash
./scripts/deploy.sh
```

This script will:
1. Check for Docker and Docker Compose
2. Create `.env` file if needed
3. Build Docker images
4. Start all services (scraper + Redis)
5. Verify health checks

### Manual Deployment

```bash
# Clone the repository
git clone <repository-url>
cd "New Scraper"

# Copy environment file
cp .env.example .env

# Build and start services
docker-compose up -d

# Check logs
docker-compose logs -f scraper
```

## 📖 API Usage

### Health Check

```bash
curl http://localhost:8000/health
```

### Scrape Website

```bash
curl -X POST "http://localhost:8000/api/v1/scrape" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com",
    "max_pages": 50,
    "timeout": 30
  }'
```

### Response Format

```json
{
  "success": true,
  "domain": "example.com",
  "emails": [
    {
      "email": "contact@example.com",
      "domain": "example.com",
      "mx_valid": true,
      "found_on": "/contact",
      "mx_records": [
        {
          "preference": 10,
          "exchange": "mail.example.com"
        }
      ]
    }
  ],
  "pages_visited": ["/", "/contact"],
  "total_pages": 2,
  "execution_time": 2.34
}
```

### Interactive API Documentation

Visit `http://localhost:8000/docs` for interactive Swagger UI documentation.

## 🏗️ Architecture

### Project Structure

```
new-scraper/
├── src/
│   ├── main.py                 # FastAPI application
│   ├── api/                     # API routes and models
│   ├── core/                    # Configuration and logging
│   ├── services/                # Business logic services
│   │   ├── url_processor.py    # URL normalization
│   │   ├── scraper.py          # Web scraping
│   │   ├── email_extractor.py  # Email extraction
│   │   ├── mx_validator.py     # DNS validation
│   │   ├── cache_manager.py    # Redis caching
│   │   └── orchestrator.py     # Workflow orchestration
│   └── utils/                   # Utilities and patterns
├── scripts/
│   └── deploy.sh               # Deployment script
├── docker-compose.yml          # Docker Compose configuration
├── Dockerfile                  # Docker image definition
└── requirements.txt            # Python dependencies
```

### Workflow

1. **URL Processing**: Extract and normalize root domain
2. **Root Page Scraping**: Scrape the homepage first
3. **Email Extraction**: Use multiple methods to find emails
4. **DNS Validation**: Check MX records for found emails
5. **Contact Pages**: If no valid email, visit common contact pages
6. **Early Termination**: Stop when valid email is found
7. **Caching**: Cache MX records for future requests

### Contact Pages Visited

The scraper automatically visits these common contact pages:

- `/contact`, `/contact-us`, `/contactus`, `/get-in-touch`
- `/about`, `/about-us`, `/who-we-are`, `/company`
- `/support`, `/help`, `/customer-service`, `/faq`
- `/sales`, `/pricing`, `/quote`, `/business`, `/enterprise`

## ⚙️ Configuration

Configuration is managed through environment variables. See `.env.example` for all available options:

### Key Settings

- `MAX_PAGES_TO_VISIT`: Maximum pages to scrape (default: 50)
- `PAGE_LOAD_TIMEOUT`: Timeout for page loads (default: 15s)
- `DNS_TIMEOUT`: DNS query timeout (default: 5s)
- `CACHE_TTL`: Cache time-to-live (default: 86400s)
- `ENABLE_JS_RENDERING`: Enable JavaScript rendering (default: true)
- `CONCURRENT_SCRAPING`: Enable concurrent page scraping (default: true)

## 🔧 Development

### Local Development Setup

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium

# Run Redis (using Docker)
docker run -d -p 6379:6379 redis:7-alpine

# Run application
uvicorn src.main:app --reload
```

### Running Tests

```bash
# Install test dependencies
pip install pytest pytest-asyncio

# Run tests
pytest
```

## 📊 Performance

- **Concurrent Scraping**: Multiple pages scraped simultaneously
- **Smart Caching**: MX records cached to reduce DNS queries
- **Early Termination**: Stops immediately when valid email found
- **Connection Pooling**: Reuses HTTP connections
- **Async Architecture**: Non-blocking I/O for maximum throughput

## 🔒 Security

- Input validation and sanitization
- Timeout enforcement
- Error handling without data leakage
- Non-root Docker user
- Health check endpoints

## 📝 Logging

Structured JSON logging for easy parsing and monitoring:

```json
{
  "event": "Scraping completed",
  "domain": "example.com",
  "pages": 2,
  "emails_found": 1,
  "execution_time": 2.34,
  "timestamp": "2024-01-01T12:00:00Z"
}
```

## 🐳 Docker

### Build Image

```bash
docker build -t website-scraper .
```

### Run Container

```bash
docker run -p 8000:8000 website-scraper
```

### Docker Compose

```bash
# Start services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down

# Rebuild and restart
docker-compose up -d --build
```

## 🚀 Deployment

### Single Server Deployment

```bash
./scripts/deploy.sh
```

### Multi-Server Deployment

1. Push code to GitHub
2. On each server:
   ```bash
   git clone <repository-url>
   cd "New Scraper"
   ./scripts/deploy.sh
   ```

### Environment Variables

Set production environment variables in `.env`:

```bash
LOG_LEVEL=INFO
WORKERS=4
CACHE_ENABLED=true
REDIS_HOST=redis
```

## 📈 Monitoring

### Health Endpoint

```bash
curl http://localhost:8000/health
```

### Statistics

```bash
curl http://localhost:8000/api/v1/stats
```

### Logs

```bash
# Docker Compose
docker-compose logs -f scraper

# Docker
docker logs -f website-scraper
```

## 🐛 Troubleshooting

### Services Not Starting

```bash
# Check Docker status
docker-compose ps

# View logs
docker-compose logs scraper

# Check Redis connection
docker-compose logs redis
```

### Playwright Issues

```bash
# Reinstall Playwright browsers
docker-compose exec scraper playwright install chromium
```

### DNS Timeout Issues

Increase `DNS_TIMEOUT` in `.env` file.

### Cache Issues

```bash
# Clear Redis cache
docker-compose exec redis redis-cli FLUSHDB
```

## 📄 License

[Add your license here]

## 🤝 Contributing

[Add contribution guidelines]

## 📧 Support

[Add support information]

---

**Built with ❤️ for production-grade web scraping**


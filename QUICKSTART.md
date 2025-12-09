# Quick Start Guide

## 🚀 Get Started in 3 Steps

### Step 1: Deploy
```bash
./scripts/deploy.sh
```

### Step 2: Test Health
```bash
curl http://localhost:8000/health
```

### Step 3: Scrape a Website
```bash
curl -X POST "http://localhost:8000/api/v1/scrape" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}'
```

## 📝 Using the Example Script

```bash
python example_usage.py https://example.com
```

## 🐳 Docker Commands

```bash
# Start services
docker-compose up -d

# View logs
docker-compose logs -f scraper

# Stop services
docker-compose down

# Restart
docker-compose restart
```

## 📚 API Documentation

Visit `http://localhost:8000/docs` for interactive API documentation.

## ✅ Verification Checklist

- [ ] Docker and Docker Compose installed
- [ ] Services running: `docker-compose ps`
- [ ] Health check passes: `curl http://localhost:8000/health`
- [ ] API docs accessible: `http://localhost:8000/docs`

## 🆘 Troubleshooting

**Services not starting?**
```bash
docker-compose logs
```

**Port already in use?**
Change port in `docker-compose.yml`:
```yaml
ports:
  - "8001:8000"  # Change 8000 to 8001
```

**Need to rebuild?**
```bash
docker-compose up -d --build
```

